"""Unit tests for CLI main module.

Testing Strategy:
- pytest 9.0.1 with asyncio_mode="auto" (no decorators needed)
- AAA pattern (Arrange, Act, Assert)
- Mock command execution and external dependencies
- Test error handling and exit codes
- Fast, isolated tests
"""

import argparse
from unittest.mock import MagicMock, patch

from pytest import main, mark, raises

from async_task.cli.commands.migrate import MigrationError
from async_task.cli.main import main as cli_main
from async_task.cli.main import run_command


@mark.unit
class TestRunCommand:
    """Test run_command() function."""

    @patch("async_task.cli.main.build_config")
    @patch("async_task.cli.main.asyncio.run")
    @patch("async_task.cli.main.run_worker")
    def test_run_command_worker(self, mock_run_worker, mock_asyncio_run, mock_build_config) -> None:
        # Arrange
        args = argparse.Namespace(command="worker", driver="redis")
        mock_config = MagicMock()
        mock_build_config.return_value = mock_config

        # Act
        run_command(args)

        # Assert
        mock_build_config.assert_called_once_with(args)
        mock_run_worker.assert_called_once_with(args, mock_config)
        # Verify asyncio.run was called once with a coroutine (run_worker is async)
        mock_asyncio_run.assert_called_once()
        # Verify the argument passed to asyncio.run is a coroutine
        import asyncio

        call_args = mock_asyncio_run.call_args[0]
        assert len(call_args) == 1
        assert asyncio.iscoroutine(call_args[0])

    @patch("async_task.cli.main.build_config")
    @patch("async_task.cli.main.asyncio.run")
    @patch("async_task.cli.main.run_migrate")
    def test_run_command_migrate(
        self, mock_run_migrate, mock_asyncio_run, mock_build_config
    ) -> None:
        # Arrange
        args = argparse.Namespace(command="migrate", driver="postgres")
        mock_config = MagicMock()
        mock_build_config.return_value = mock_config

        # Act
        run_command(args)

        # Assert
        mock_build_config.assert_called_once_with(args)
        mock_asyncio_run.assert_called_once()

    @patch("async_task.cli.main.build_config")
    @patch("async_task.cli.main.asyncio.run")
    def test_run_command_unknown_command_raises_error(
        self, mock_asyncio_run, mock_build_config
    ) -> None:
        # Arrange
        args = argparse.Namespace(command="unknown")
        mock_config = MagicMock()
        mock_build_config.return_value = mock_config

        # Act & Assert
        with raises(ValueError, match="Unknown command: unknown"):
            run_command(args)

        # Ensure asyncio.run was never called since we raise before it
        mock_asyncio_run.assert_not_called()


@mark.unit
class TestMain:
    """Test main() function."""

    @patch("async_task.cli.main.setup_logging")
    @patch("async_task.cli.main.create_parser")
    @patch("async_task.cli.main.run_command")
    def test_main_success(self, mock_run_command, mock_create_parser, mock_setup_logging) -> None:
        # Arrange
        mock_parser = MagicMock()
        mock_args = MagicMock()
        mock_parser.parse_args.return_value = mock_args
        mock_create_parser.return_value = mock_parser

        # Act
        cli_main()

        # Assert
        mock_setup_logging.assert_called_once()
        mock_create_parser.assert_called_once()
        mock_parser.parse_args.assert_called_once()
        mock_run_command.assert_called_once_with(mock_args)

    @patch("async_task.cli.main.setup_logging")
    @patch("async_task.cli.main.create_parser")
    @patch("async_task.cli.main.run_command")
    @patch("sys.exit")
    def test_main_keyboard_interrupt(
        self, mock_exit, mock_run_command, mock_create_parser, mock_setup_logging
    ) -> None:
        # Arrange
        mock_parser = MagicMock()
        mock_args = MagicMock()
        mock_parser.parse_args.return_value = mock_args
        mock_create_parser.return_value = mock_parser
        mock_run_command.side_effect = KeyboardInterrupt()

        # Act
        cli_main()

        # Assert
        mock_setup_logging.assert_called_once()
        mock_exit.assert_called_once_with(0)

    @patch("async_task.cli.main.setup_logging")
    @patch("async_task.cli.main.create_parser")
    @patch("async_task.cli.main.run_command")
    @patch("async_task.cli.main.logger")
    @patch("sys.exit")
    def test_main_migration_error(
        self, mock_exit, mock_logger, mock_run_command, mock_create_parser, mock_setup_logging
    ) -> None:
        # Arrange
        mock_parser = MagicMock()
        mock_args = MagicMock()
        mock_parser.parse_args.return_value = mock_args
        mock_create_parser.return_value = mock_parser
        mock_run_command.side_effect = MigrationError("Migration failed")

        # Act
        cli_main()

        # Assert
        mock_setup_logging.assert_called_once()
        mock_logger.error.assert_called_once_with("Migration failed")
        mock_exit.assert_called_once_with(1)

    @patch("async_task.cli.main.setup_logging")
    @patch("async_task.cli.main.create_parser")
    @patch("async_task.cli.main.run_command")
    @patch("async_task.cli.main.logger")
    @patch("sys.exit")
    def test_main_generic_exception(
        self, mock_exit, mock_logger, mock_run_command, mock_create_parser, mock_setup_logging
    ) -> None:
        # Arrange
        mock_parser = MagicMock()
        mock_args = MagicMock()
        mock_parser.parse_args.return_value = mock_args
        mock_create_parser.return_value = mock_parser
        mock_run_command.side_effect = ValueError("Something went wrong")

        # Act
        cli_main()

        # Assert
        mock_setup_logging.assert_called_once()
        mock_logger.exception.assert_called_once()
        mock_exit.assert_called_once_with(1)

    @patch("async_task.cli.main.setup_logging")
    @patch("async_task.cli.main.create_parser")
    @patch("async_task.cli.main.run_command")
    @patch("async_task.cli.main.logger")
    @patch("sys.exit")
    def test_main_parser_error(
        self, mock_exit, mock_logger, mock_run_command, mock_create_parser, mock_setup_logging
    ) -> None:
        # Arrange
        mock_parser = MagicMock()
        mock_create_parser.return_value = mock_parser
        mock_parser.parse_args.side_effect = SystemExit(2)  # argparse raises SystemExit on error

        # Act & Assert
        # SystemExit from argparse should propagate (not caught by our exception handler)
        with raises(SystemExit):
            cli_main()

        # Assert
        # SystemExit from argparse should propagate (not caught)
        # But in real usage, argparse handles this
        mock_setup_logging.assert_called_once()
        assert mock_run_command.called is False


if __name__ == "__main__":
    main([__file__, "-s", "-m", "unit"])
