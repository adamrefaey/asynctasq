"""Unit tests for migrate command.

Testing Strategy:
- pytest 9.0.1 with asyncio_mode="auto" (no decorators needed)
- AAA pattern (Arrange, Act, Assert)
- Mock the internal _run_postgres_migration and _run_mysql_migration functions
- Fast, isolated tests
"""

import argparse
from unittest.mock import patch

from pytest import main, mark, raises

from asynctasq.cli.commands.migrate import MigrationError, run_migrate
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


if __name__ == "__main__":
    main([__file__, "-s", "-m", "unit"])
