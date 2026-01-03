"""Migrate command implementation."""

from __future__ import annotations

import argparse
import logging
from typing import Any

logger = logging.getLogger(__name__)


class MigrationError(Exception):
    """Raised when migration fails."""


class PostgresMigrator:
    """PostgreSQL-specific migration operations."""

    def __init__(self, config: Any) -> None:
        """Initialize PostgreSQL migrator.

        Args:
            config: Configuration object with PostgreSQL settings
        """
        self.dsn = config.postgres.dsn
        self.queue_table = config.postgres.queue_table
        self.dead_letter_table = config.postgres.dead_letter_table

    async def check_table_exists(self, conn: Any, table_name: str) -> bool:
        """Check if a table exists in the database.

        Args:
            conn: Database connection
            table_name: Name of the table to check

        Returns:
            True if table exists, False otherwise
        """
        result = await conn.fetchval(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = $1
            )
            """,
            table_name,
        )
        return bool(result)

    async def verify_schema(self, conn: Any) -> dict[str, bool]:
        """Verify that all required tables and indices exist.

        Args:
            conn: Database connection

        Returns:
            Dictionary with verification results
        """
        results = {}

        # Check queue table
        results["queue_table"] = await self.check_table_exists(conn, self.queue_table)

        # Check queue index
        index_exists = await conn.fetchval(
            """
            SELECT EXISTS (
                SELECT FROM pg_indexes
                WHERE tablename = $1 AND indexname = $2
            )
            """,
            self.queue_table,
            f"idx_{self.queue_table}_lookup",
        )
        results["queue_index"] = bool(index_exists)

        # Check dead letter table
        results["dead_letter_table"] = await self.check_table_exists(conn, self.dead_letter_table)

        return results

    async def get_migration_sql(self) -> list[tuple[str, str]]:
        """Get SQL statements for migration.

        Returns:
            List of tuples (description, sql_statement)
        """
        statements = []

        # Queue table
        statements.append(
            (
                f"Create queue table '{self.queue_table}'",
                f"""
                CREATE TABLE IF NOT EXISTS {self.queue_table} (
                    id SERIAL PRIMARY KEY,
                    queue_name TEXT NOT NULL,
                    payload BYTEA NOT NULL,
                    available_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    locked_until TIMESTAMPTZ,
                    status TEXT NOT NULL DEFAULT 'pending',
                    current_attempt INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    visibility_timeout_seconds INTEGER NOT NULL DEFAULT 3600,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """,
            )
        )

        # Visibility timeout column migration
        statements.append(
            (
                f"Add visibility_timeout_seconds column to '{self.queue_table}' (if missing)",
                f"""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = '{self.queue_table}'
                        AND column_name = 'visibility_timeout_seconds'
                    ) THEN
                        ALTER TABLE {self.queue_table}
                        ADD COLUMN visibility_timeout_seconds INTEGER NOT NULL DEFAULT 3600;
                    END IF;
                END $$;
                """,
            )
        )

        # Queue table index
        statements.append(
            (
                f"Create index 'idx_{self.queue_table}_lookup'",
                f"""
                CREATE INDEX IF NOT EXISTS idx_{self.queue_table}_lookup
                ON {self.queue_table} (queue_name, status, available_at, locked_until)
                """,
            )
        )

        # Dead letter table
        statements.append(
            (
                f"Create dead letter table '{self.dead_letter_table}'",
                f"""
                CREATE TABLE IF NOT EXISTS {self.dead_letter_table} (
                    id SERIAL PRIMARY KEY,
                    queue_name TEXT NOT NULL,
                    payload BYTEA NOT NULL,
                    current_attempt INTEGER NOT NULL,
                    error_message TEXT,
                    failed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """,
            )
        )

        return statements

    async def run_migration(self, conn: Any, dry_run: bool = False) -> None:
        """Execute migration statements.

        Args:
            conn: Database connection
            dry_run: If True, only show what would be executed

        Raises:
            Exception: If migration fails
        """
        statements = await self.get_migration_sql()

        if dry_run:
            logger.info("🔍 Dry-run mode: Showing SQL statements that would be executed")
            logger.info("")
            for description, sql in statements:
                logger.info(f"  ▸ {description}")
                logger.info(f"    {sql.strip()}")
                logger.info("")
            return

        # Execute all statements in a transaction
        async with conn.transaction():
            for description, sql in statements:
                logger.info(f"  ▸ {description}")
                await conn.execute(sql)


class MySQLMigrator:
    """MySQL-specific migration operations."""

    def __init__(self, config: Any) -> None:
        """Initialize MySQL migrator.

        Args:
            config: Configuration object with MySQL settings
        """
        self.dsn = config.mysql.dsn
        self.queue_table = config.mysql.queue_table
        self.dead_letter_table = config.mysql.dead_letter_table

    async def check_table_exists(self, cursor: Any, table_name: str) -> bool:
        """Check if a table exists in the database.

        Args:
            cursor: Database cursor
            table_name: Name of the table to check

        Returns:
            True if table exists, False otherwise
        """
        await cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = DATABASE() AND table_name = %s
            """,
            (table_name,),
        )
        result = await cursor.fetchone()
        return bool(result and result[0] > 0)

    async def verify_schema(self, cursor: Any) -> dict[str, bool]:
        """Verify that all required tables and indices exist.

        Args:
            cursor: Database cursor

        Returns:
            Dictionary with verification results
        """
        results = {}

        # Check queue table
        results["queue_table"] = await self.check_table_exists(cursor, self.queue_table)

        # Check queue index
        await cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.statistics
            WHERE table_schema = DATABASE()
            AND table_name = %s
            AND index_name = %s
            """,
            (self.queue_table, f"idx_{self.queue_table}_lookup"),
        )
        index_result = await cursor.fetchone()
        results["queue_index"] = bool(index_result and index_result[0] > 0)

        # Check dead letter table
        results["dead_letter_table"] = await self.check_table_exists(cursor, self.dead_letter_table)

        return results

    async def get_migration_sql(self) -> list[tuple[str, str]]:
        """Get SQL statements for migration.

        Returns:
            List of tuples (description, sql_statement)
        """
        statements = []

        # Queue table
        statements.append(
            (
                f"Create queue table '{self.queue_table}'",
                f"""
                CREATE TABLE IF NOT EXISTS {self.queue_table} (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    queue_name VARCHAR(255) NOT NULL,
                    payload BLOB NOT NULL,
                    available_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                    locked_until DATETIME(6) NULL,
                    status VARCHAR(50) NOT NULL DEFAULT 'pending',
                    current_attempt INT NOT NULL DEFAULT 0,
                    max_attempts INT NOT NULL DEFAULT 3,
                    visibility_timeout_seconds INT NOT NULL DEFAULT 3600,
                    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
                    INDEX idx_{self.queue_table}_lookup (queue_name, status, available_at, locked_until)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """,
            )
        )

        # Dead letter table
        statements.append(
            (
                f"Create dead letter table '{self.dead_letter_table}'",
                f"""
                CREATE TABLE IF NOT EXISTS {self.dead_letter_table} (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    queue_name VARCHAR(255) NOT NULL,
                    payload BLOB NOT NULL,
                    current_attempt INT NOT NULL,
                    error_message TEXT,
                    failed_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """,
            )
        )

        return statements

    async def run_migration(self, cursor: Any, dry_run: bool = False) -> None:
        """Execute migration statements.

        Args:
            cursor: Database cursor
            dry_run: If True, only show what would be executed

        Raises:
            Exception: If migration fails
        """
        statements = await self.get_migration_sql()

        if dry_run:
            logger.info("🔍 Dry-run mode: Showing SQL statements that would be executed")
            logger.info("")
            for description, sql in statements:
                logger.info(f"  ▸ {description}")
                logger.info(f"    {sql.strip()}")
                logger.info("")
            return

        # Execute all statements (MySQL doesn't support transactional DDL)
        for description, sql in statements:
            logger.info(f"  ▸ {description}")
            await cursor.execute(sql)


async def run_migrate(args: argparse.Namespace, config: Any) -> None:
    """Run the migrate command to initialize database schema.

    Supports both PostgreSQL and MySQL drivers with optimized migration logic:
    - Uses direct connections instead of connection pools
    - Checks if migration is needed before running (idempotent)
    - Wraps migrations in transactions (PostgreSQL only)
    - Verifies schema after migration
    - Supports dry-run mode to preview changes
    - Provides detailed error messages for common issues

    Args:
        args: Parsed command-line arguments with --dry-run and --force flags
        config: Configuration object

    Raises:
        MigrationError: If migration fails or driver is not supported.
    """
    dry_run = getattr(args, "dry_run", False)
    force = getattr(args, "force", False)

    if config.driver == "postgres":
        await _run_postgres_migration(config, dry_run, force)
    elif config.driver == "mysql":
        await _run_mysql_migration(config, dry_run, force)
    else:
        raise MigrationError(
            f"Migration is only supported for PostgreSQL and MySQL drivers. "
            f"Current driver: {config.driver}. Use --driver postgres or --driver mysql to migrate."
        )


async def _run_postgres_migration(config: Any, dry_run: bool, force: bool) -> None:
    """Run PostgreSQL migration.

    Args:
        config: Configuration object
        dry_run: If True, only show what would be executed
        force: If True, run migration even if tables exist
    """
    import asyncpg

    migrator = PostgresMigrator(config)

    logger.info("🚀 PostgreSQL Schema Migration")
    logger.info(f"  DSN: {config.postgres.dsn}")
    logger.info(f"  Queue table: {config.postgres.queue_table}")
    logger.info(f"  Dead letter table: {config.postgres.dead_letter_table}")
    logger.info("")

    conn = None
    try:
        # Use single connection instead of pool for one-time operation
        conn = await asyncpg.connect(dsn=config.postgres.dsn)

        if not force and not dry_run:
            # Check if migration is needed
            logger.info("🔍 Checking existing schema...")
            verification = await migrator.verify_schema(conn)

            if all(verification.values()):
                logger.info("✅ Schema already up to date. All tables and indices exist.")
                logger.info("   Use --force to run migration anyway.")
                return

            missing = [k for k, v in verification.items() if not v]
            logger.info(f"⚠️  Missing schema objects: {', '.join(missing)}")
            logger.info("")

        # Run migration
        logger.info("📝 Running migration...")
        await migrator.run_migration(conn, dry_run=dry_run)

        if dry_run:
            logger.info("✅ Dry-run complete. Use without --dry-run to apply changes.")
            return

        # Verify schema after migration
        logger.info("")
        logger.info("🔍 Verifying schema...")
        verification = await migrator.verify_schema(conn)

        if all(verification.values()):
            logger.info("✅ Migration successful! Schema verified.")
            logger.info(f"   ✓ Queue table: {config.postgres.queue_table}")
            logger.info(f"   ✓ Queue index: idx_{config.postgres.queue_table}_lookup")
            logger.info(f"   ✓ Dead letter table: {config.postgres.dead_letter_table}")
        else:
            missing = [k for k, v in verification.items() if not v]
            raise MigrationError(f"Schema verification failed. Missing: {', '.join(missing)}")

    except asyncpg.PostgresError as e:
        error_msg = str(e)
        if "does not exist" in error_msg:
            raise MigrationError(
                f"Database connection failed: {error_msg}\n"
                f"Please ensure PostgreSQL is running and the database exists.\n"
                f"You may need to create the database first: CREATE DATABASE <dbname>;"
            ) from e
        elif "authentication failed" in error_msg or "password" in error_msg:
            raise MigrationError(
                f"Authentication failed: {error_msg}\n"
                f"Please check your PostgreSQL credentials in the DSN."
            ) from e
        elif "could not connect" in error_msg or "Connection refused" in error_msg:
            raise MigrationError(
                f"Connection failed: {error_msg}\n"
                f"Please ensure PostgreSQL is running and accessible."
            ) from e
        else:
            raise MigrationError(f"PostgreSQL error during migration: {error_msg}") from e
    except Exception as e:
        raise MigrationError(f"Unexpected error during migration: {e}") from e
    finally:
        if conn:
            await conn.close()


async def _run_mysql_migration(config: Any, dry_run: bool, force: bool) -> None:
    """Run MySQL migration.

    Args:
        config: Configuration object
        dry_run: If True, only show what would be executed
        force: If True, run migration even if tables exist
    """
    import asyncmy
    from asyncmy.errors import Error as AsyncmyError

    migrator = MySQLMigrator(config)

    logger.info("🚀 MySQL Schema Migration")
    logger.info(f"  DSN: {config.mysql.dsn}")
    logger.info(f"  Queue table: {config.mysql.queue_table}")
    logger.info(f"  Dead letter table: {config.mysql.dead_letter_table}")
    logger.info("")

    conn = None
    try:
        # Parse connection parameters
        from urllib.parse import urlparse

        parsed = urlparse(config.mysql.dsn)
        conn_params = {
            "host": parsed.hostname or "localhost",
            "port": parsed.port or 3306,
            "user": parsed.username or "root",
            "password": parsed.password or "",
            "db": parsed.path.lstrip("/") if parsed.path else "test_db",
        }

        # Use single connection instead of pool for one-time operation
        conn = await asyncmy.connect(**conn_params)

        async with conn.cursor() as cursor:
            if not force and not dry_run:
                # Check if migration is needed
                logger.info("🔍 Checking existing schema...")
                verification = await migrator.verify_schema(cursor)

                if all(verification.values()):
                    logger.info("✅ Schema already up to date. All tables and indices exist.")
                    logger.info("   Use --force to run migration anyway.")
                    return

                missing = [k for k, v in verification.items() if not v]
                logger.info(f"⚠️  Missing schema objects: {', '.join(missing)}")
                logger.info("")

            # Run migration
            logger.info("📝 Running migration...")
            await migrator.run_migration(cursor, dry_run=dry_run)
            await conn.commit()

            if dry_run:
                logger.info("✅ Dry-run complete. Use without --dry-run to apply changes.")
                return

            # Verify schema after migration
            logger.info("")
            logger.info("🔍 Verifying schema...")
            verification = await migrator.verify_schema(cursor)

            if all(verification.values()):
                logger.info("✅ Migration successful! Schema verified.")
                logger.info(f"   ✓ Queue table: {config.mysql.queue_table}")
                logger.info(f"   ✓ Queue index: idx_{config.mysql.queue_table}_lookup")
                logger.info(f"   ✓ Dead letter table: {config.mysql.dead_letter_table}")
            else:
                missing = [k for k, v in verification.items() if not v]
                raise MigrationError(f"Schema verification failed. Missing: {', '.join(missing)}")

    except AsyncmyError as e:
        error_msg = str(e)
        if "Unknown database" in error_msg:
            raise MigrationError(
                f"Database connection failed: {error_msg}\n"
                f"Please ensure MySQL is running and the database exists.\n"
                f"You may need to create the database first: CREATE DATABASE <dbname>;"
            ) from e
        elif "Access denied" in error_msg:
            raise MigrationError(
                f"Authentication failed: {error_msg}\n"
                f"Please check your MySQL credentials in the DSN."
            ) from e
        elif "Can't connect" in error_msg or "Connection refused" in error_msg:
            raise MigrationError(
                f"Connection failed: {error_msg}\nPlease ensure MySQL is running and accessible."
            ) from e
        else:
            raise MigrationError(f"MySQL error during migration: {error_msg}") from e
    except Exception as e:
        raise MigrationError(f"Unexpected error during migration: {e}") from e
    finally:
        if conn:
            await conn.ensure_closed()
