"""Unit tests for migrate command.

Testing Strategy:
- pytest 9.0.1 with asyncio_mode="auto" (no decorators needed)
- AAA pattern (Arrange, Act, Assert)
- Mock the internal _run_postgres_migration and _run_mysql_migration functions
- Fast, isolated tests
"""

import argparse
from unittest.mock import AsyncMock, Mock, patch

from pytest import main, mark, raises

from asynctasq.cli.commands.migrate import (
    MigrationError,
    MySQLMigrator,
    PostgresMigrator,
    run_migrate,
)
from asynctasq.config import Config, MySQLConfig, PostgresConfig


@mark.unit
class TestMigrationError:
    """Test MigrationError exception."""

    def test_migration_error_is_exception(self) -> None:
        # Assert
        assert issubclass(MigrationError, Exception)

    def test_migration_error_can_be_raised(self) -> None:
        # Act & Assert
        with raises(MigrationError, match="test error"):
            raise MigrationError("test error")

    def test_migration_error_message(self) -> None:
        # Arrange
        error = MigrationError("Custom error message")

        # Assert
        assert str(error) == "Custom error message"


@mark.unit
class TestRunMigrate:
    """Test run_migrate() function."""

    @mark.asyncio
    async def test_run_migrate_with_non_postgres_driver_raises_error(self) -> None:
        # Arrange
        args = argparse.Namespace()
        config = Config(driver="redis")

        # Act & Assert
        with raises(
            MigrationError, match="Migration is only supported for PostgreSQL and MySQL drivers"
        ):
            await run_migrate(args, config)

    @mark.asyncio
    async def test_run_migrate_with_redis_driver_raises_error(self) -> None:
        # Arrange
        args = argparse.Namespace()
        config = Config(driver="redis")

        # Act & Assert
        with raises(
            MigrationError, match="Migration is only supported for PostgreSQL and MySQL drivers"
        ):
            await run_migrate(args, config)

    @mark.asyncio
    async def test_run_migrate_with_sqs_driver_raises_error(self) -> None:
        # Arrange
        args = argparse.Namespace()
        config = Config(driver="sqs")

        # Act & Assert
        with raises(
            MigrationError, match="Migration is only supported for PostgreSQL and MySQL drivers"
        ):
            await run_migrate(args, config)

    @patch("asynctasq.cli.commands.migrate._run_postgres_migration")
    @mark.asyncio
    async def test_run_migrate_with_postgres_driver_success(
        self, mock_run_postgres_migration
    ) -> None:
        # Arrange
        args = argparse.Namespace(dry_run=False, force=False)
        config = Config(
            driver="postgres",
            postgres=PostgresConfig(
                dsn="postgresql://user:pass@localhost/db",
                queue_table="task_queue",
                dead_letter_table="dead_letter_queue",
            ),
        )

        # Act
        await run_migrate(args, config)

        # Assert
        mock_run_postgres_migration.assert_awaited_once_with(config, False, False)

    @patch("asynctasq.cli.commands.migrate._run_postgres_migration")
    @mark.asyncio
    async def test_run_migrate_with_dry_run_flag(self, mock_run_postgres_migration) -> None:
        # Arrange
        args = argparse.Namespace(dry_run=True, force=False)
        config = Config(driver="postgres")

        # Act
        await run_migrate(args, config)

        # Assert
        mock_run_postgres_migration.assert_awaited_once_with(config, True, False)

    @patch("asynctasq.cli.commands.migrate._run_postgres_migration")
    @mark.asyncio
    async def test_run_migrate_with_force_flag(self, mock_run_postgres_migration) -> None:
        # Arrange
        args = argparse.Namespace(dry_run=False, force=True)
        config = Config(driver="postgres")

        # Act
        await run_migrate(args, config)

        # Assert
        mock_run_postgres_migration.assert_awaited_once_with(config, False, True)

    @patch("asynctasq.cli.commands.migrate._run_postgres_migration")
    @mark.asyncio
    async def test_run_migrate_propagates_migration_error(
        self, mock_run_postgres_migration
    ) -> None:
        # Arrange
        args = argparse.Namespace(dry_run=False, force=False)
        config = Config(driver="postgres")
        mock_run_postgres_migration.side_effect = MigrationError("Test error")

        # Act & Assert
        with raises(MigrationError, match="Test error"):
            await run_migrate(args, config)

    @patch("asynctasq.cli.commands.migrate._run_mysql_migration")
    @mark.asyncio
    async def test_run_migrate_with_mysql_driver_success(self, mock_run_mysql_migration) -> None:
        # Arrange
        args = argparse.Namespace(dry_run=False, force=False)
        config = Config(
            driver="mysql",
            mysql=MySQLConfig(
                dsn="mysql://user:pass@localhost/db",
                queue_table="task_queue",
                dead_letter_table="dead_letter_queue",
            ),
        )

        # Act
        await run_migrate(args, config)

        # Assert
        mock_run_mysql_migration.assert_awaited_once_with(config, False, False)

    @patch("asynctasq.cli.commands.migrate._run_mysql_migration")
    @mark.asyncio
    async def test_run_migrate_mysql_with_dry_run_flag(self, mock_run_mysql_migration) -> None:
        # Arrange
        args = argparse.Namespace(dry_run=True, force=False)
        config = Config(driver="mysql")

        # Act
        await run_migrate(args, config)

        # Assert
        mock_run_mysql_migration.assert_awaited_once_with(config, True, False)

    @patch("asynctasq.cli.commands.migrate._run_mysql_migration")
    @mark.asyncio
    async def test_run_migrate_mysql_with_force_flag(self, mock_run_mysql_migration) -> None:
        # Arrange
        args = argparse.Namespace(dry_run=False, force=True)
        config = Config(driver="mysql")

        # Act
        await run_migrate(args, config)

        # Assert
        mock_run_mysql_migration.assert_awaited_once_with(config, False, True)

    @patch("asynctasq.cli.commands.migrate._run_mysql_migration")
    @mark.asyncio
    async def test_run_migrate_mysql_propagates_migration_error(
        self, mock_run_mysql_migration
    ) -> None:
        # Arrange
        args = argparse.Namespace(dry_run=False, force=False)
        config = Config(driver="mysql")
        mock_run_mysql_migration.side_effect = MigrationError("Test error")

        # Act & Assert
        with raises(MigrationError, match="Test error"):
            await run_migrate(args, config)


@mark.unit
class TestPostgresMigrator:
    """Test PostgresMigrator class."""

    def test_init(self) -> None:
        # Arrange
        config = Config(
            driver="postgres",
            postgres=PostgresConfig(
                dsn="postgresql://user:pass@localhost/db",
                queue_table="tasks",
                dead_letter_table="dead_letters",
            ),
        )

        # Act
        migrator = PostgresMigrator(config)

        # Assert
        assert migrator.dsn == "postgresql://user:pass@localhost/db"
        assert migrator.queue_table == "tasks"
        assert migrator.dead_letter_table == "dead_letters"

    @mark.asyncio
    async def test_check_table_exists_returns_true(self) -> None:
        # Arrange
        config = Config(driver="postgres")
        migrator = PostgresMigrator(config)
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = True

        # Act
        result = await migrator.check_table_exists(mock_conn, "test_table")

        # Assert
        assert result is True
        mock_conn.fetchval.assert_awaited_once()
        call_args = mock_conn.fetchval.call_args
        assert "information_schema.tables" in call_args[0][0]
        assert call_args[0][1] == "test_table"

    @mark.asyncio
    async def test_check_table_exists_returns_false(self) -> None:
        # Arrange
        config = Config(driver="postgres")
        migrator = PostgresMigrator(config)
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = False

        # Act
        result = await migrator.check_table_exists(mock_conn, "test_table")

        # Assert
        assert result is False

    @mark.asyncio
    async def test_verify_schema_all_exists(self) -> None:
        # Arrange
        config = Config(
            driver="postgres",
            postgres=PostgresConfig(
                dsn="postgresql://user:pass@localhost/db",
                queue_table="tasks",
                dead_letter_table="dead_letters",
            ),
        )
        migrator = PostgresMigrator(config)
        mock_conn = AsyncMock()
        # First call for queue_table, second for index, third for dead_letter_table
        mock_conn.fetchval.side_effect = [True, True, True]

        # Act
        result = await migrator.verify_schema(mock_conn)

        # Assert
        assert result == {
            "queue_table": True,
            "queue_index": True,
            "dead_letter_table": True,
        }
        assert mock_conn.fetchval.call_count == 3

    @mark.asyncio
    async def test_verify_schema_missing_items(self) -> None:
        # Arrange
        config = Config(driver="postgres")
        migrator = PostgresMigrator(config)
        mock_conn = AsyncMock()
        # Missing queue index and dead letter table
        mock_conn.fetchval.side_effect = [True, False, False]

        # Act
        result = await migrator.verify_schema(mock_conn)

        # Assert
        assert result == {
            "queue_table": True,
            "queue_index": False,
            "dead_letter_table": False,
        }

    @mark.asyncio
    async def test_get_migration_sql_returns_statements(self) -> None:
        # Arrange
        config = Config(
            driver="postgres",
            postgres=PostgresConfig(
                dsn="postgresql://user:pass@localhost/db",
                queue_table="tasks",
                dead_letter_table="dead_letters",
            ),
        )
        migrator = PostgresMigrator(config)

        # Act
        statements = await migrator.get_migration_sql()

        # Assert
        assert len(statements) == 4
        descriptions = [s[0] for s in statements]
        assert "Create queue table 'tasks'" in descriptions
        assert "Add visibility_timeout_seconds column to 'tasks' (if missing)" in descriptions
        assert "Create index 'idx_tasks_lookup'" in descriptions
        assert "Create dead letter table 'dead_letters'" in descriptions

        # Check SQL contains expected keywords
        sqls = [s[1] for s in statements]
        assert any("CREATE TABLE" in sql and "tasks" in sql for sql in sqls)
        assert any("CREATE INDEX" in sql for sql in sqls)
        assert any("dead_letters" in sql for sql in sqls)

    @mark.asyncio
    async def test_run_migration_dry_run(self) -> None:
        # Arrange
        config = Config(driver="postgres")
        migrator = PostgresMigrator(config)
        mock_conn = AsyncMock()

        # Act
        await migrator.run_migration(mock_conn, dry_run=True)

        # Assert - Should not execute any SQL
        mock_conn.execute.assert_not_called()
        mock_conn.transaction.assert_not_called()

    @mark.asyncio
    async def test_run_migration_executes_statements(self) -> None:
        # Arrange
        config = Config(
            driver="postgres",
            postgres=PostgresConfig(
                dsn="postgresql://user:pass@localhost/db",
                queue_table="tasks",
                dead_letter_table="dead_letters",
            ),
        )
        migrator = PostgresMigrator(config)
        mock_conn = Mock()
        mock_conn.execute = AsyncMock()

        # Create a proper async context manager for transaction that is NOT a coroutine
        class AsyncContextManager:
            def __init__(self):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        # Make transaction callable that returns the context manager
        mock_conn.transaction = Mock(return_value=AsyncContextManager())

        # Act
        await migrator.run_migration(mock_conn, dry_run=False)

        # Assert
        mock_conn.transaction.assert_called_once()
        # Should execute 4 statements
        assert mock_conn.execute.call_count == 4


@mark.unit
class TestMySQLMigrator:
    """Test MySQLMigrator class."""

    def test_init(self) -> None:
        # Arrange
        config = Config(
            driver="mysql",
            mysql=MySQLConfig(
                dsn="mysql://user:pass@localhost/db",
                queue_table="tasks",
                dead_letter_table="dead_letters",
            ),
        )

        # Act
        migrator = MySQLMigrator(config)

        # Assert
        assert migrator.dsn == "mysql://user:pass@localhost/db"
        assert migrator.queue_table == "tasks"
        assert migrator.dead_letter_table == "dead_letters"

    @mark.asyncio
    async def test_check_table_exists_returns_true(self) -> None:
        # Arrange
        config = Config(driver="mysql")
        migrator = MySQLMigrator(config)
        mock_cursor = AsyncMock()
        mock_cursor.fetchone.return_value = (1,)

        # Act
        result = await migrator.check_table_exists(mock_cursor, "test_table")

        # Assert
        assert result is True
        mock_cursor.execute.assert_awaited_once()
        call_args = mock_cursor.execute.call_args
        assert "information_schema.tables" in call_args[0][0]
        assert call_args[0][1] == ("test_table",)

    @mark.asyncio
    async def test_check_table_exists_returns_false(self) -> None:
        # Arrange
        config = Config(driver="mysql")
        migrator = MySQLMigrator(config)
        mock_cursor = AsyncMock()
        mock_cursor.fetchone.return_value = (0,)

        # Act
        result = await migrator.check_table_exists(mock_cursor, "test_table")

        # Assert
        assert result is False

    @mark.asyncio
    async def test_check_table_exists_with_none_result(self) -> None:
        # Arrange
        config = Config(driver="mysql")
        migrator = MySQLMigrator(config)
        mock_cursor = AsyncMock()
        mock_cursor.fetchone.return_value = None

        # Act
        result = await migrator.check_table_exists(mock_cursor, "test_table")

        # Assert
        assert result is False

    @mark.asyncio
    async def test_verify_schema_all_exists(self) -> None:
        # Arrange
        config = Config(
            driver="mysql",
            mysql=MySQLConfig(
                dsn="mysql://user:pass@localhost/db",
                queue_table="tasks",
                dead_letter_table="dead_letters",
            ),
        )
        migrator = MySQLMigrator(config)
        mock_cursor = AsyncMock()
        # First call for queue_table, second for index, third for dead_letter_table
        mock_cursor.fetchone.side_effect = [(1,), (1,), (1,)]

        # Act
        result = await migrator.verify_schema(mock_cursor)

        # Assert
        assert result == {
            "queue_table": True,
            "queue_index": True,
            "dead_letter_table": True,
        }
        assert mock_cursor.execute.call_count == 3

    @mark.asyncio
    async def test_verify_schema_missing_items(self) -> None:
        # Arrange
        config = Config(driver="mysql")
        migrator = MySQLMigrator(config)
        mock_cursor = AsyncMock()
        # Missing queue index and dead letter table
        mock_cursor.fetchone.side_effect = [(1,), (0,), (0,)]

        # Act
        result = await migrator.verify_schema(mock_cursor)

        # Assert
        assert result == {
            "queue_table": True,
            "queue_index": False,
            "dead_letter_table": False,
        }

    @mark.asyncio
    async def test_get_migration_sql_returns_statements(self) -> None:
        # Arrange
        config = Config(
            driver="mysql",
            mysql=MySQLConfig(
                dsn="mysql://user:pass@localhost/db",
                queue_table="tasks",
                dead_letter_table="dead_letters",
            ),
        )
        migrator = MySQLMigrator(config)

        # Act
        statements = await migrator.get_migration_sql()

        # Assert
        assert len(statements) == 2
        descriptions = [s[0] for s in statements]
        assert "Create queue table 'tasks'" in descriptions
        assert "Create dead letter table 'dead_letters'" in descriptions

        # Check SQL contains expected keywords
        sqls = [s[1] for s in statements]
        assert any("CREATE TABLE" in sql and "tasks" in sql for sql in sqls)
        assert any("dead_letters" in sql for sql in sqls)

    @mark.asyncio
    async def test_run_migration_dry_run(self) -> None:
        # Arrange
        config = Config(driver="mysql")
        migrator = MySQLMigrator(config)
        mock_cursor = AsyncMock()

        # Act
        await migrator.run_migration(mock_cursor, dry_run=True)

        # Assert - Should not execute any SQL
        mock_cursor.execute.assert_not_called()

    @mark.asyncio
    async def test_run_migration_executes_statements(self) -> None:
        # Arrange
        config = Config(
            driver="mysql",
            mysql=MySQLConfig(
                dsn="mysql://user:pass@localhost/db",
                queue_table="tasks",
                dead_letter_table="dead_letters",
            ),
        )
        migrator = MySQLMigrator(config)
        mock_cursor = AsyncMock()

        # Act
        await migrator.run_migration(mock_cursor, dry_run=False)

        # Assert
        # Should execute 2 statements for MySQL
        assert mock_cursor.execute.call_count == 2


@mark.unit
class TestRunPostgresMigration:
    """Test _run_postgres_migration function with comprehensive mocking."""

    @mark.asyncio
    async def test_postgres_migration_success_with_fresh_install(self) -> None:
        # Arrange
        config = Config(driver="postgres")

        # Create proper mocks
        mock_conn = Mock()
        mock_conn.close = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.fetchval = AsyncMock(side_effect=[False, False, False, True, True, True])

        # Mock transaction as context manager
        class TransactionContext:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        mock_conn.transaction = Mock(return_value=TransactionContext())

        # Mock asyncpg module
        mock_asyncpg = Mock()
        mock_asyncpg.connect = AsyncMock(return_value=mock_conn)
        mock_asyncpg.PostgresError = type("PostgresError", (Exception,), {})

        # Act
        with (
            patch.dict("sys.modules", {"asyncpg": mock_asyncpg}),
            patch("asynctasq.cli.commands.migrate.logger"),
        ):
            from asynctasq.cli.commands.migrate import _run_postgres_migration

            await _run_postgres_migration(config, dry_run=False, force=False)

        # Assert
        mock_asyncpg.connect.assert_awaited_once()
        assert mock_conn.execute.call_count == 4  # 4 migration statements
        mock_conn.close.assert_awaited_once()

    @mark.asyncio
    async def test_postgres_migration_already_migrated(self) -> None:
        # Arrange
        config = Config(driver="postgres")

        mock_conn = Mock()
        mock_conn.close = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=True)  # All checks return True

        mock_asyncpg = Mock()
        mock_asyncpg.connect = AsyncMock(return_value=mock_conn)

        # Act
        with (
            patch.dict("sys.modules", {"asyncpg": mock_asyncpg}),
            patch("asynctasq.cli.commands.migrate.logger"),
        ):
            from asynctasq.cli.commands.migrate import _run_postgres_migration

            await _run_postgres_migration(config, dry_run=False, force=False)

        # Assert
        mock_conn.close.assert_awaited_once()

    @mark.asyncio
    async def test_postgres_migration_with_dry_run(self) -> None:
        # Arrange
        config = Config(driver="postgres")

        mock_conn = Mock()
        mock_conn.close = AsyncMock()

        mock_asyncpg = Mock()
        mock_asyncpg.connect = AsyncMock(return_value=mock_conn)

        # Act
        with (
            patch.dict("sys.modules", {"asyncpg": mock_asyncpg}),
            patch("asynctasq.cli.commands.migrate.logger"),
        ):
            from asynctasq.cli.commands.migrate import _run_postgres_migration

            await _run_postgres_migration(config, dry_run=True, force=False)

        # Assert
        mock_conn.close.assert_awaited_once()

    @mark.asyncio
    async def test_postgres_migration_with_force_flag(self) -> None:
        # Arrange
        config = Config(driver="postgres")

        mock_conn = Mock()
        mock_conn.close = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=True)  # Verification returns True

        # Mock transaction as context manager
        class TransactionContext:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        mock_conn.transaction = Mock(return_value=TransactionContext())

        mock_asyncpg = Mock()
        mock_asyncpg.connect = AsyncMock(return_value=mock_conn)

        # Act
        with (
            patch.dict("sys.modules", {"asyncpg": mock_asyncpg}),
            patch("asynctasq.cli.commands.migrate.logger"),
        ):
            from asynctasq.cli.commands.migrate import _run_postgres_migration

            await _run_postgres_migration(config, dry_run=False, force=True)

        # Assert
        assert mock_conn.execute.call_count == 4  # Migration runs even if already up to date
        mock_conn.close.assert_awaited_once()

    @mark.asyncio
    async def test_postgres_migration_verification_fails(self) -> None:
        # Arrange
        config = Config(driver="postgres")

        mock_conn = Mock()
        mock_conn.close = AsyncMock()
        mock_conn.execute = AsyncMock()
        # Initial check: all False, final verification: partial False
        mock_conn.fetchval = AsyncMock(side_effect=[False, False, False, True, False, False])

        # Mock transaction as context manager
        class TransactionContext:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        mock_conn.transaction = Mock(return_value=TransactionContext())

        # Create PostgresError that inherits from BaseException
        PostgresError = type("PostgresError", (BaseException,), {})

        mock_asyncpg = Mock()
        mock_asyncpg.connect = AsyncMock(return_value=mock_conn)
        mock_asyncpg.PostgresError = PostgresError

        # Act & Assert
        with (
            patch.dict("sys.modules", {"asyncpg": mock_asyncpg}),
            patch("asynctasq.cli.commands.migrate.logger"),
            raises(MigrationError, match="Schema verification failed"),
        ):
            from asynctasq.cli.commands.migrate import _run_postgres_migration

            await _run_postgres_migration(config, dry_run=False, force=False)

        mock_conn.close.assert_awaited_once()

    @mark.asyncio
    async def test_postgres_migration_database_not_exist_error(self) -> None:
        # Arrange
        config = Config(driver="postgres")

        PostgresError = type("PostgresError", (Exception,), {})

        mock_asyncpg = Mock()
        mock_asyncpg.PostgresError = PostgresError
        mock_asyncpg.connect = AsyncMock(side_effect=PostgresError("database does not exist"))

        # Act & Assert
        with (
            patch.dict("sys.modules", {"asyncpg": mock_asyncpg}),
            patch("asynctasq.cli.commands.migrate.logger"),
            raises(MigrationError, match="Database connection failed"),
        ):
            from asynctasq.cli.commands.migrate import _run_postgres_migration

            await _run_postgres_migration(config, dry_run=False, force=False)

    @mark.asyncio
    async def test_postgres_migration_authentication_error(self) -> None:
        # Arrange
        config = Config(driver="postgres")

        PostgresError = type("PostgresError", (Exception,), {})

        mock_asyncpg = Mock()
        mock_asyncpg.PostgresError = PostgresError
        mock_asyncpg.connect = AsyncMock(side_effect=PostgresError("authentication failed"))

        # Act & Assert
        with (
            patch.dict("sys.modules", {"asyncpg": mock_asyncpg}),
            patch("asynctasq.cli.commands.migrate.logger"),
            raises(MigrationError, match="Authentication failed"),
        ):
            from asynctasq.cli.commands.migrate import _run_postgres_migration

            await _run_postgres_migration(config, dry_run=False, force=False)

    @mark.asyncio
    async def test_postgres_migration_connection_refused_error(self) -> None:
        # Arrange
        config = Config(driver="postgres")

        PostgresError = type("PostgresError", (Exception,), {})

        mock_asyncpg = Mock()
        mock_asyncpg.PostgresError = PostgresError
        mock_asyncpg.connect = AsyncMock(side_effect=PostgresError("Connection refused"))

        # Act & Assert
        with (
            patch.dict("sys.modules", {"asyncpg": mock_asyncpg}),
            patch("asynctasq.cli.commands.migrate.logger"),
            raises(MigrationError, match="Connection failed"),
        ):
            from asynctasq.cli.commands.migrate import _run_postgres_migration

            await _run_postgres_migration(config, dry_run=False, force=False)

    @mark.asyncio
    async def test_postgres_migration_generic_postgres_error(self) -> None:
        # Arrange
        config = Config(driver="postgres")

        PostgresError = type("PostgresError", (Exception,), {})

        mock_asyncpg = Mock()
        mock_asyncpg.PostgresError = PostgresError
        mock_asyncpg.connect = AsyncMock(side_effect=PostgresError("unknown error"))

        # Act & Assert
        with (
            patch.dict("sys.modules", {"asyncpg": mock_asyncpg}),
            patch("asynctasq.cli.commands.migrate.logger"),
            raises(MigrationError, match="PostgreSQL error during migration"),
        ):
            from asynctasq.cli.commands.migrate import _run_postgres_migration

            await _run_postgres_migration(config, dry_run=False, force=False)

    @mark.asyncio
    async def test_postgres_migration_unexpected_error(self) -> None:
        # Arrange
        config = Config(driver="postgres")

        mock_asyncpg = Mock()
        mock_asyncpg.PostgresError = type("PostgresError", (Exception,), {})
        mock_asyncpg.connect = AsyncMock(side_effect=ValueError("unexpected"))

        # Act & Assert
        with (
            patch.dict("sys.modules", {"asyncpg": mock_asyncpg}),
            patch("asynctasq.cli.commands.migrate.logger"),
            raises(MigrationError, match="Unexpected error during migration"),
        ):
            from asynctasq.cli.commands.migrate import _run_postgres_migration

            await _run_postgres_migration(config, dry_run=False, force=False)


@mark.unit
class TestRunMySQLMigration:
    """Test _run_mysql_migration function with comprehensive mocking."""

    @mark.asyncio
    async def test_mysql_migration_success_with_fresh_install(self) -> None:
        # Arrange
        config = Config(
            driver="mysql",
            mysql=MySQLConfig(dsn="mysql://user:pass@localhost:3306/testdb"),
        )

        # Create proper mocks
        mock_cursor = Mock()
        mock_cursor.execute = AsyncMock()
        mock_cursor.fetchone = AsyncMock(side_effect=[(0,), (0,), (0,), (1,), (1,), (1,)])

        # Mock cursor context manager
        class CursorContext:
            async def __aenter__(self):
                return mock_cursor

            async def __aexit__(self, *args):
                pass

        mock_conn = Mock()
        mock_conn.cursor = Mock(return_value=CursorContext())
        mock_conn.commit = AsyncMock()
        mock_conn.ensure_closed = AsyncMock()

        # Mock asyncmy module
        mock_asyncmy = Mock()
        mock_asyncmy.connect = AsyncMock(return_value=mock_conn)
        mock_asyncmy.errors = Mock()
        mock_asyncmy.errors.Error = type("Error", (Exception,), {})

        # Act
        with (
            patch.dict(
                "sys.modules", {"asyncmy": mock_asyncmy, "asyncmy.errors": mock_asyncmy.errors}
            ),
            patch("asynctasq.cli.commands.migrate.logger"),
        ):
            from asynctasq.cli.commands.migrate import _run_mysql_migration

            await _run_mysql_migration(config, dry_run=False, force=False)

        # Assert
        mock_asyncmy.connect.assert_awaited_once()
        mock_conn.commit.assert_awaited_once()
        mock_conn.ensure_closed.assert_awaited_once()

    @mark.asyncio
    async def test_mysql_migration_already_migrated(self) -> None:
        # Arrange
        config = Config(driver="mysql")

        mock_cursor = Mock()
        mock_cursor.execute = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=(1,))  # All checks return 1

        # Mock cursor context manager
        class CursorContext:
            async def __aenter__(self):
                return mock_cursor

            async def __aexit__(self, *args):
                pass

        mock_conn = Mock()
        mock_conn.cursor = Mock(return_value=CursorContext())
        mock_conn.ensure_closed = AsyncMock()

        # Mock asyncmy.errors module
        mock_errors = Mock()
        mock_errors.Error = type("Error", (Exception,), {})

        mock_asyncmy = Mock()
        mock_asyncmy.connect = AsyncMock(return_value=mock_conn)
        mock_asyncmy.errors = mock_errors

        # Act
        with (
            patch.dict("sys.modules", {"asyncmy": mock_asyncmy, "asyncmy.errors": mock_errors}),
            patch("asynctasq.cli.commands.migrate.logger"),
        ):
            from asynctasq.cli.commands.migrate import _run_mysql_migration

            await _run_mysql_migration(config, dry_run=False, force=False)

        # Assert
        mock_conn.ensure_closed.assert_awaited_once()

    @mark.asyncio
    async def test_mysql_migration_with_dry_run(self) -> None:
        # Arrange
        config = Config(driver="mysql")

        mock_cursor = Mock()
        mock_cursor.execute = AsyncMock()

        # Mock cursor context manager
        class CursorContext:
            async def __aenter__(self):
                return mock_cursor

            async def __aexit__(self, *args):
                pass

        mock_conn = Mock()
        mock_conn.cursor = Mock(return_value=CursorContext())
        mock_conn.commit = AsyncMock()
        mock_conn.ensure_closed = AsyncMock()

        # Mock asyncmy.errors module
        mock_errors = Mock()
        mock_errors.Error = type("Error", (Exception,), {})

        mock_asyncmy = Mock()
        mock_asyncmy.connect = AsyncMock(return_value=mock_conn)
        mock_asyncmy.errors = mock_errors

        # Act
        with (
            patch.dict("sys.modules", {"asyncmy": mock_asyncmy, "asyncmy.errors": mock_errors}),
            patch("asynctasq.cli.commands.migrate.logger"),
        ):
            from asynctasq.cli.commands.migrate import _run_mysql_migration

            await _run_mysql_migration(config, dry_run=True, force=False)

        # Assert
        mock_conn.ensure_closed.assert_awaited_once()

    @mark.asyncio
    async def test_mysql_migration_with_force_flag(self) -> None:
        # Arrange
        config = Config(driver="mysql")

        mock_cursor = Mock()
        mock_cursor.execute = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=(1,))  # Verification returns 1

        # Mock cursor context manager
        class CursorContext:
            async def __aenter__(self):
                return mock_cursor

            async def __aexit__(self, *args):
                pass

        mock_conn = Mock()
        mock_conn.cursor = Mock(return_value=CursorContext())
        mock_conn.commit = AsyncMock()
        mock_conn.ensure_closed = AsyncMock()

        # Mock asyncmy.errors module
        mock_errors = Mock()
        mock_errors.Error = type("Error", (Exception,), {})

        mock_asyncmy = Mock()
        mock_asyncmy.connect = AsyncMock(return_value=mock_conn)
        mock_asyncmy.errors = mock_errors

        # Act
        with (
            patch.dict("sys.modules", {"asyncmy": mock_asyncmy, "asyncmy.errors": mock_errors}),
            patch("asynctasq.cli.commands.migrate.logger"),
        ):
            from asynctasq.cli.commands.migrate import _run_mysql_migration

            await _run_mysql_migration(config, dry_run=False, force=True)

        # Assert
        mock_conn.commit.assert_awaited_once()
        mock_conn.ensure_closed.assert_awaited_once()

    @mark.asyncio
    async def test_mysql_migration_verification_fails(self) -> None:
        # Arrange
        config = Config(driver="mysql")

        mock_cursor = Mock()
        mock_cursor.execute = AsyncMock()
        # Initial check: all 0, final verification: partial 0
        mock_cursor.fetchone = AsyncMock(side_effect=[(0,), (0,), (0,), (1,), (0,), (0,)])

        # Mock cursor context manager
        class CursorContext:
            async def __aenter__(self):
                return mock_cursor

            async def __aexit__(self, *args):
                pass

        mock_conn = Mock()
        mock_conn.cursor = Mock(return_value=CursorContext())
        mock_conn.commit = AsyncMock()
        mock_conn.ensure_closed = AsyncMock()

        # Mock asyncmy.errors module
        mock_errors = Mock()
        mock_errors.Error = type("Error", (Exception,), {})

        mock_asyncmy = Mock()
        mock_asyncmy.connect = AsyncMock(return_value=mock_conn)
        mock_asyncmy.errors = mock_errors

        # Act & Assert
        with (
            patch.dict("sys.modules", {"asyncmy": mock_asyncmy, "asyncmy.errors": mock_errors}),
            patch("asynctasq.cli.commands.migrate.logger"),
            raises(MigrationError, match="Schema verification failed"),
        ):
            from asynctasq.cli.commands.migrate import _run_mysql_migration

            await _run_mysql_migration(config, dry_run=False, force=False)

        mock_conn.ensure_closed.assert_awaited_once()

    @mark.asyncio
    async def test_mysql_migration_unknown_database_error(self) -> None:
        # Arrange
        config = Config(driver="mysql")

        MySQLError = type("Error", (Exception,), {})

        mock_asyncmy = Mock()
        mock_asyncmy.errors = Mock()
        mock_asyncmy.errors.Error = MySQLError
        mock_asyncmy.connect = AsyncMock(side_effect=MySQLError("Unknown database"))

        # Act & Assert
        with (
            patch.dict(
                "sys.modules", {"asyncmy": mock_asyncmy, "asyncmy.errors": mock_asyncmy.errors}
            ),
            patch("asynctasq.cli.commands.migrate.logger"),
            raises(MigrationError, match="Database connection failed"),
        ):
            from asynctasq.cli.commands.migrate import _run_mysql_migration

            await _run_mysql_migration(config, dry_run=False, force=False)

    @mark.asyncio
    async def test_mysql_migration_access_denied_error(self) -> None:
        # Arrange
        config = Config(driver="mysql")

        MySQLError = type("Error", (Exception,), {})

        mock_asyncmy = Mock()
        mock_asyncmy.errors = Mock()
        mock_asyncmy.errors.Error = MySQLError
        mock_asyncmy.connect = AsyncMock(side_effect=MySQLError("Access denied"))

        # Act & Assert
        with (
            patch.dict(
                "sys.modules", {"asyncmy": mock_asyncmy, "asyncmy.errors": mock_asyncmy.errors}
            ),
            patch("asynctasq.cli.commands.migrate.logger"),
            raises(MigrationError, match="Authentication failed"),
        ):
            from asynctasq.cli.commands.migrate import _run_mysql_migration

            await _run_mysql_migration(config, dry_run=False, force=False)

    @mark.asyncio
    async def test_mysql_migration_connection_refused_error(self) -> None:
        # Arrange
        config = Config(driver="mysql")

        MySQLError = type("Error", (Exception,), {})

        mock_asyncmy = Mock()
        mock_asyncmy.errors = Mock()
        mock_asyncmy.errors.Error = MySQLError
        mock_asyncmy.connect = AsyncMock(side_effect=MySQLError("Can't connect"))

        # Act & Assert
        with (
            patch.dict(
                "sys.modules", {"asyncmy": mock_asyncmy, "asyncmy.errors": mock_asyncmy.errors}
            ),
            patch("asynctasq.cli.commands.migrate.logger"),
            raises(MigrationError, match="Connection failed"),
        ):
            from asynctasq.cli.commands.migrate import _run_mysql_migration

            await _run_mysql_migration(config, dry_run=False, force=False)

    @mark.asyncio
    async def test_mysql_migration_generic_mysql_error(self) -> None:
        # Arrange
        config = Config(driver="mysql")

        MySQLError = type("Error", (Exception,), {})

        mock_asyncmy = Mock()
        mock_asyncmy.errors = Mock()
        mock_asyncmy.errors.Error = MySQLError
        mock_asyncmy.connect = AsyncMock(side_effect=MySQLError("unknown error"))

        # Act & Assert
        with (
            patch.dict(
                "sys.modules", {"asyncmy": mock_asyncmy, "asyncmy.errors": mock_asyncmy.errors}
            ),
            patch("asynctasq.cli.commands.migrate.logger"),
            raises(MigrationError, match="MySQL error during migration"),
        ):
            from asynctasq.cli.commands.migrate import _run_mysql_migration

            await _run_mysql_migration(config, dry_run=False, force=False)

    @mark.asyncio
    async def test_mysql_migration_unexpected_error(self) -> None:
        # Arrange
        config = Config(driver="mysql")

        mock_asyncmy = Mock()
        mock_asyncmy.errors = Mock()
        mock_asyncmy.errors.Error = type("Error", (Exception,), {})
        mock_asyncmy.connect = AsyncMock(side_effect=ValueError("unexpected"))

        # Act & Assert
        with (
            patch.dict(
                "sys.modules", {"asyncmy": mock_asyncmy, "asyncmy.errors": mock_asyncmy.errors}
            ),
            patch("asynctasq.cli.commands.migrate.logger"),
            raises(MigrationError, match="Unexpected error during migration"),
        ):
            from asynctasq.cli.commands.migrate import _run_mysql_migration

            await _run_mysql_migration(config, dry_run=False, force=False)


if __name__ == "__main__":
    main([__file__, "-s", "-m", "unit"])
