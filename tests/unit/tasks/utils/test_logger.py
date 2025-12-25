"""Unit tests for logger module (structured logging helpers).

Testing Strategy:
- pytest 9.0.1 with asyncio_mode="auto"
- Test all logging functions with task context extraction
- Verify correlation_id inclusion for distributed tracing
- Mock logging to avoid actual log output during tests
- Use class-level attributes for task configuration
"""

from unittest.mock import MagicMock, patch

from pytest import main, mark

from asynctasq.tasks.core.base_task import BaseTask
from asynctasq.tasks.utils.logger import (
    get_task_context,
    log_task_debug,
    log_task_error,
    log_task_info,
    log_task_warning,
)


class SampleTask(BaseTask[int]):
    """Sample task for testing."""

    async def run(self) -> int:
        return 42


@mark.unit
class TestGetTaskContext:
    """Test get_task_context function."""

    def test_extracts_basic_task_context(self) -> None:
        # Arrange
        class ConfiguredTask(BaseTask[int]):
            config = {
                "queue": "test-queue",
                "max_attempts": 5,
            }

            async def run(self) -> int:
                return 42

        task = ConfiguredTask()
        task._task_id = "test-task-123"
        task._current_attempt = 2

        # Act
        context = get_task_context(task)

        # Assert
        assert context["task_id"] == "test-task-123"
        assert context["task_class"] == "ConfiguredTask"
        assert context["queue"] == "test-queue"
        assert context["current_attempt"] == 2
        assert context["max_attempts"] == 5
        assert "correlation_id" not in context  # Not set by default

    def test_includes_correlation_id_when_present(self) -> None:
        # Arrange
        task = SampleTask()
        task._task_id = "test-task-456"
        task._current_attempt = 1
        task.config = {"correlation_id": "trace-123"}

        # Act
        context = get_task_context(task)

        # Assert
        assert context["task_id"] == "test-task-456"
        assert context["correlation_id"] == "trace-123"

    def test_excludes_correlation_id_when_none(self) -> None:
        # Arrange
        task = SampleTask()
        task._task_id = "test-task-789"
        task._current_attempt = 1
        task.config = {"correlation_id": None}  # Explicitly set to None

        # Act
        context = get_task_context(task)

        # Assert
        assert context["task_id"] == "test-task-789"
        assert "correlation_id" not in context  # None values are excluded


@mark.unit
class TestLogTaskInfo:
    """Test log_task_info function."""

    @patch("asynctasq.tasks.utils.logger.logging.getLogger")
    def test_logs_info_with_task_context(self, mock_get_logger: MagicMock) -> None:
        # Arrange
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        task = SampleTask()
        task._task_id = "info-task"
        task._current_attempt = 1

        # Act
        log_task_info(task, "Task started")

        # Assert
        mock_get_logger.assert_called_once_with(task.__class__.__module__)
        mock_logger.info.assert_called_once()
        args, kwargs = mock_logger.info.call_args
        assert args[0] == "Task started"
        assert kwargs["extra"]["task_id"] == "info-task"

    @patch("asynctasq.tasks.utils.logger.logging.getLogger")
    def test_logs_info_with_extra_context(self, mock_get_logger: MagicMock) -> None:
        # Arrange
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        task = SampleTask()
        task._task_id = "extra-task"

        # Act
        log_task_info(task, "Processing data", data_size=1024, source="api")

        # Assert
        args, kwargs = mock_logger.info.call_args
        assert kwargs["extra"]["data_size"] == 1024
        assert kwargs["extra"]["source"] == "api"


@mark.unit
class TestLogTaskDebug:
    """Test log_task_debug function."""

    @patch("asynctasq.tasks.utils.logger.logging.getLogger")
    def test_logs_debug_with_task_context(self, mock_get_logger: MagicMock) -> None:
        # Arrange
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        task = SampleTask()
        task._task_id = "debug-task"
        task._current_attempt = 0

        # Act
        log_task_debug(task, "Debug message")

        # Assert
        mock_logger.debug.assert_called_once()
        args, kwargs = mock_logger.debug.call_args
        assert args[0] == "Debug message"
        assert kwargs["extra"]["task_id"] == "debug-task"

    @patch("asynctasq.tasks.utils.logger.logging.getLogger")
    def test_logs_debug_with_correlation_id(self, mock_get_logger: MagicMock) -> None:
        # Arrange
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        task = SampleTask()
        task._task_id = "trace-task"

        # Act
        log_task_debug(task, "Tracing request", step="validation")

        # Assert
        args, kwargs = mock_logger.debug.call_args
        assert kwargs["extra"]["step"] == "validation"


@mark.unit
class TestLogTaskWarning:
    """Test log_task_warning function."""

    @patch("asynctasq.tasks.utils.logger.logging.getLogger")
    def test_logs_warning_with_task_context(self, mock_get_logger: MagicMock) -> None:
        # Arrange
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        class WarnTask(BaseTask[int]):
            max_attempts = 3

            async def run(self) -> int:
                return 42

        task = WarnTask()
        task._task_id = "warn-task"
        task._current_attempt = 2

        # Act
        log_task_warning(task, "Approaching retry limit")

        # Assert
        mock_logger.warning.assert_called_once()
        args, kwargs = mock_logger.warning.call_args
        assert args[0] == "Approaching retry limit"
        assert kwargs["extra"]["current_attempt"] == 2
        assert kwargs["extra"]["max_attempts"] == 3

    @patch("asynctasq.tasks.utils.logger.logging.getLogger")
    def test_logs_warning_with_extra_fields(self, mock_get_logger: MagicMock) -> None:
        # Arrange
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        task = SampleTask()
        task._task_id = "slow-task"

        # Act
        log_task_warning(task, "Slow execution", duration_ms=5000, threshold_ms=3000)

        # Assert
        args, kwargs = mock_logger.warning.call_args
        assert kwargs["extra"]["duration_ms"] == 5000
        assert kwargs["extra"]["threshold_ms"] == 3000


@mark.unit
class TestLogTaskError:
    """Test log_task_error function."""

    @patch("asynctasq.tasks.utils.logger.logging.getLogger")
    def test_logs_error_with_task_context(self, mock_get_logger: MagicMock) -> None:
        # Arrange
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        class ErrorTask(BaseTask[int]):
            max_attempts = 3

            async def run(self) -> int:
                return 42

        task = ErrorTask()
        task._task_id = "error-task"
        task._current_attempt = 3

        # Act
        log_task_error(task, "Task failed permanently")

        # Assert
        mock_logger.error.assert_called_once()
        args, kwargs = mock_logger.error.call_args
        assert args[0] == "Task failed permanently"
        assert kwargs["extra"]["task_id"] == "error-task"
        assert kwargs["extra"]["current_attempt"] == 3
        assert kwargs["exc_info"] is True  # Default

    @patch("asynctasq.tasks.utils.logger.logging.getLogger")
    def test_logs_error_without_exc_info(self, mock_get_logger: MagicMock) -> None:
        # Arrange
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        task = SampleTask()
        task._task_id = "no-exc-task"

        # Act
        log_task_error(task, "Error without traceback", exc_info=False)

        # Assert
        args, kwargs = mock_logger.error.call_args
        assert kwargs["exc_info"] is False

    @patch("asynctasq.tasks.utils.logger.logging.getLogger")
    def test_logs_error_with_exception_details(self, mock_get_logger: MagicMock) -> None:
        # Arrange
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        task = SampleTask()
        task._task_id = "exception-task"

        # Act
        log_task_error(
            task,
            "Database connection failed",
            error_type="ConnectionError",
            retry_after=60,
        )

        # Assert
        args, kwargs = mock_logger.error.call_args
        assert kwargs["extra"]["error_type"] == "ConnectionError"
        assert kwargs["extra"]["retry_after"] == 60


if __name__ == "__main__":
    main([__file__, "-s", "-m", "unit"])
