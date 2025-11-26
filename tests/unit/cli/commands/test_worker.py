"""Unit tests for worker command.

Testing Strategy:
- pytest 9.0.1 with asyncio_mode="strict" (explicit @mark.asyncio decorators required)
- AAA pattern (Arrange, Act, Assert)
- Mock Worker and DriverFactory to avoid real connections
- Fast, isolated tests
"""

import argparse
from unittest.mock import AsyncMock, MagicMock, patch

from pytest import main, mark

from async_task.cli.commands.worker import run_worker
from async_task.config import Config


@mark.unit
class TestRunWorker:
    """Test run_worker() function."""

    @patch("async_task.cli.commands.worker.Worker")
    @patch("async_task.cli.commands.worker.DriverFactory")
    @patch("async_task.cli.commands.worker.parse_queues")
    @patch("async_task.cli.commands.worker.logger")
    @mark.asyncio
    async def test_run_worker_with_defaults(
        self, mock_logger, mock_parse_queues, mock_driver_factory, mock_worker_class
    ) -> None:
        # Arrange
        args = argparse.Namespace(queues=None, concurrency=10)
        config = Config(driver="redis")
        mock_driver = MagicMock()
        mock_driver_factory.create_from_config.return_value = mock_driver
        mock_worker = AsyncMock()
        mock_worker_class.return_value = mock_worker
        mock_parse_queues.return_value = ["default"]

        # Act
        await run_worker(args, config)

        # Assert
        mock_parse_queues.assert_called_once_with(None)
        mock_driver_factory.create_from_config.assert_called_once_with(config)
        mock_worker_class.assert_called_once_with(
            queue_driver=mock_driver,
            queues=["default"],
            concurrency=10,
        )
        mock_worker.start.assert_awaited_once()
        mock_logger.info.assert_called_once()

    @patch("async_task.cli.commands.worker.Worker")
    @patch("async_task.cli.commands.worker.DriverFactory")
    @patch("async_task.cli.commands.worker.parse_queues")
    @patch("async_task.cli.commands.worker.logger")
    @mark.asyncio
    async def test_run_worker_with_custom_queues(
        self, mock_logger, mock_parse_queues, mock_driver_factory, mock_worker_class
    ) -> None:
        # Arrange
        args = argparse.Namespace(queues="high,low", concurrency=20)
        config = Config(driver="redis")
        mock_driver = MagicMock()
        mock_driver_factory.create_from_config.return_value = mock_driver
        mock_worker = AsyncMock()
        mock_worker_class.return_value = mock_worker
        mock_parse_queues.return_value = ["high", "low"]

        # Act
        await run_worker(args, config)

        # Assert
        mock_parse_queues.assert_called_once_with("high,low")
        mock_worker_class.assert_called_once_with(
            queue_driver=mock_driver,
            queues=["high", "low"],
            concurrency=20,
        )

    @patch("async_task.cli.commands.worker.Worker")
    @patch("async_task.cli.commands.worker.DriverFactory")
    @patch("async_task.cli.commands.worker.parse_queues")
    @patch("async_task.cli.commands.worker.logger")
    @mark.asyncio
    async def test_run_worker_with_different_driver(
        self, mock_logger, mock_parse_queues, mock_driver_factory, mock_worker_class
    ) -> None:
        # Arrange
        args = argparse.Namespace(queues=None, concurrency=5)
        config = Config(driver="sqs")
        mock_driver = MagicMock()
        mock_driver_factory.create_from_config.return_value = mock_driver
        mock_worker = AsyncMock()
        mock_worker_class.return_value = mock_worker
        mock_parse_queues.return_value = ["default"]

        # Act
        await run_worker(args, config)

        # Assert
        mock_driver_factory.create_from_config.assert_called_once_with(config)
        mock_logger.info.assert_called_once()
        assert "driver=sqs" in str(mock_logger.info.call_args)

    @patch("async_task.cli.commands.worker.Worker")
    @patch("async_task.cli.commands.worker.DriverFactory")
    @patch("async_task.cli.commands.worker.parse_queues")
    @mark.asyncio
    async def test_run_worker_logs_correct_info(
        self, mock_parse_queues, mock_driver_factory, mock_worker_class
    ) -> None:
        # Arrange
        args = argparse.Namespace(queues="high,low", concurrency=15)
        config = Config(driver="postgres")
        mock_driver = MagicMock()
        mock_driver_factory.create_from_config.return_value = mock_driver
        mock_worker = AsyncMock()
        mock_worker_class.return_value = mock_worker
        mock_parse_queues.return_value = ["high", "low"]

        # Act
        with patch("async_task.cli.commands.worker.logger") as mock_logger:
            await run_worker(args, config)

            # Assert
            mock_logger.info.assert_called_once()
            log_message = str(mock_logger.info.call_args)
            assert "driver=postgres" in log_message
            assert "queues=['high', 'low']" in log_message or "high" in log_message
            assert "concurrency=15" in log_message

    @patch("async_task.cli.commands.worker.Worker")
    @patch("async_task.cli.commands.worker.DriverFactory")
    @patch("async_task.cli.commands.worker.parse_queues")
    @mark.asyncio
    async def test_run_worker_awaits_worker_start(
        self, mock_parse_queues, mock_driver_factory, mock_worker_class
    ) -> None:
        # Arrange
        args = argparse.Namespace(queues=None, concurrency=10)
        config = Config(driver="redis")
        mock_driver = MagicMock()
        mock_driver_factory.create_from_config.return_value = mock_driver
        mock_worker = AsyncMock()
        mock_worker_class.return_value = mock_worker
        mock_parse_queues.return_value = ["default"]

        # Act
        await run_worker(args, config)

        # Assert
        mock_worker.start.assert_awaited_once()


if __name__ == "__main__":
    main([__file__, "-s", "-m", "unit"])
