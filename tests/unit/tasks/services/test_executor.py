"""Tests for task lifecycle hooks (before_execute, after_execute) and TaskExecutor.

Testing Strategy:
- pytest 9.0.1 with asyncio_mode="auto"
- Test TaskExecutor methods: execute, should_retry, prepare_retry, handle_failed
- Test failed hook error counting
- Test retry_task with driver and repository fallback
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock

from pytest import mark, raises

from asynctasq.tasks import AsyncTask, SyncTask
from asynctasq.tasks.services.executor import (
    TaskExecutor,
    get_failed_hook_error_count,
    reset_failed_hook_error_count,
)


class HookedAsyncTask(AsyncTask[str]):
    """Task with lifecycle hooks for testing."""

    def __init__(self, value: str, should_fail: bool = False) -> None:
        super().__init__()
        self.value = value
        self.should_fail = should_fail
        self.before_called = False
        self.after_called = False
        self.start_time: float | None = None
        self.end_time: float | None = None

    async def execute(self) -> str:
        """Execute task logic."""
        if self.should_fail:
            raise ValueError("Task execution failed")
        await asyncio.sleep(0.01)  # Simulate work
        return f"processed_{self.value}"

    async def before_execute(self) -> None:
        """Hook called before execution."""
        self.before_called = True
        self.start_time = time.time()

    async def after_execute(self, result: str) -> None:
        """Hook called after execution."""
        self.after_called = True
        self.end_time = time.time()


class HookedSyncTask(SyncTask[int]):
    """Sync task with lifecycle hooks for testing."""

    def __init__(self, value: int) -> None:
        super().__init__()
        self.value = value
        self.before_called = False
        self.after_called = False

    def execute(self) -> int:
        """Execute task logic."""
        return self.value * 2

    async def before_execute(self) -> None:
        """Hook called before execution."""
        self.before_called = True

    async def after_execute(self, result: int) -> None:
        """Hook called after execution."""
        self.after_called = True


class BeforeExecuteFailureTask(AsyncTask[str]):
    """Task where before_execute raises exception."""

    async def execute(self) -> str:
        return "success"

    async def before_execute(self) -> None:
        raise RuntimeError("before_execute failed")


class AfterExecuteFailureTask(AsyncTask[str]):
    """Task where after_execute raises exception."""

    async def execute(self) -> str:
        return "success"

    async def after_execute(self, result: str) -> None:
        raise RuntimeError("after_execute failed")


@mark.unit
class TestTaskExecutor:
    """Test TaskExecutor class."""

    @mark.asyncio
    async def test_execute_runs_task_without_timeout(self) -> None:
        # Arrange
        executor = TaskExecutor()

        class SimpleTask(AsyncTask[str]):
            def __init__(self) -> None:
                super().__init__()
                self.executed = False

            async def execute(self) -> str:
                self.executed = True
                return "done"

        task = SimpleTask()

        # Act
        await executor.execute(task, timeout=None)

        # Assert
        assert task.executed is True

    @mark.asyncio
    async def test_execute_with_explicit_timeout(self) -> None:
        # Arrange
        executor = TaskExecutor()

        class TimedTask(AsyncTask[str]):
            def __init__(self) -> None:
                super().__init__()
                self.executed = False

            async def execute(self) -> str:
                self.executed = True
                return "done"

        task = TimedTask()

        # Act
        await executor.execute(task, timeout=5.0)

        # Assert
        assert task.executed is True

    @mark.asyncio
    async def test_execute_with_task_config_timeout(self) -> None:
        # Arrange
        executor = TaskExecutor()

        class TimeoutTask(AsyncTask[str]):
            timeout = 10  # int, not float

            async def execute(self) -> str:
                return "done"

        task = TimeoutTask()

        # Act
        await executor.execute(task, timeout=None)

        # Assert (should use task.config.timeout)
        assert task.config.timeout == 10

    @mark.asyncio
    async def test_execute_raises_timeout_error(self) -> None:
        # Arrange
        executor = TaskExecutor()

        class SlowTask(AsyncTask[str]):
            async def execute(self) -> str:
                await asyncio.sleep(10)  # Very slow
                return "done"

        task = SlowTask()

        # Act & Assert
        with raises(asyncio.TimeoutError):
            await executor.execute(task, timeout=0.01)

    @mark.asyncio
    async def test_should_retry_returns_true_when_attempts_below_max(self) -> None:
        # Arrange
        executor = TaskExecutor()

        class RetryableTask(AsyncTask[str]):
            max_retries = 3

            async def execute(self) -> str:
                return "done"

        task = RetryableTask()
        task._attempts = 1
        exception = ValueError("Transient error")

        # Act
        result = executor.should_retry(task, exception)

        # Assert
        assert result is True

    @mark.asyncio
    async def test_should_retry_returns_false_when_max_retries_reached(self) -> None:
        # Arrange
        executor = TaskExecutor()

        class FailedTask(AsyncTask[str]):
            max_retries = 3

            async def execute(self) -> str:
                return "done"

        task = FailedTask()
        task._attempts = 3
        exception = ValueError("Permanent error")

        # Act
        result = executor.should_retry(task, exception)

        # Assert
        assert result is False

    @mark.asyncio
    async def test_should_retry_calls_task_should_retry(self) -> None:
        # Arrange
        executor = TaskExecutor()

        class CustomRetryTask(AsyncTask[str]):
            max_retries = 3

            async def execute(self) -> str:
                return "done"

            def should_retry(self, exception: Exception) -> bool:
                # Custom logic: don't retry ValueError
                return not isinstance(exception, ValueError)

        task = CustomRetryTask()
        task._attempts = 1

        # Act
        result_value_error = executor.should_retry(task, ValueError("test"))
        result_runtime_error = executor.should_retry(task, RuntimeError("test"))

        # Assert
        assert result_value_error is False  # Custom logic rejects
        assert result_runtime_error is True  # Custom logic allows

    @mark.asyncio
    async def test_prepare_retry_increments_attempts(self) -> None:
        # Arrange
        executor = TaskExecutor()
        task = HookedAsyncTask("test")
        task._attempts = 1

        # Act
        result = executor.prepare_retry(task)

        # Assert
        assert result._attempts == 2

    @mark.asyncio
    async def test_handle_failed_calls_task_failed_hook(self) -> None:
        # Arrange
        await reset_failed_hook_error_count()  # Reset counter
        executor = TaskExecutor()

        class FailedHookTask(AsyncTask[str]):
            def __init__(self) -> None:
                super().__init__()
                self.failed_called = False
                self.failed_exception: Exception | None = None

            async def execute(self) -> str:
                return "done"

            async def failed(self, exception: Exception) -> None:
                self.failed_called = True
                self.failed_exception = exception

        task = FailedHookTask()
        exception = RuntimeError("Final failure")

        # Act
        await executor.handle_failed(task, exception)

        # Assert
        assert task.failed_called is True
        assert task.failed_exception == exception

    @mark.asyncio
    async def test_handle_failed_logs_hook_errors(self) -> None:
        # Arrange
        await reset_failed_hook_error_count()
        executor = TaskExecutor()

        class BrokenFailedHookTask(AsyncTask[str]):
            async def execute(self) -> str:
                return "done"

            async def failed(self, exception: Exception) -> None:
                raise ValueError("Hook itself failed")

        task = BrokenFailedHookTask()
        exception = RuntimeError("Original error")

        # Act (should not raise, just log)
        await executor.handle_failed(task, exception)

        # Assert
        count = await get_failed_hook_error_count()
        assert count == 1  # Error was counted

    @mark.asyncio
    async def test_retry_task_with_driver_efficient_retry(self) -> None:
        # Arrange
        driver = AsyncMock()
        driver.retry_task.return_value = True
        executor = TaskExecutor(driver=driver)

        # Act
        result = await executor.retry_task("task-123")

        # Assert
        driver.retry_task.assert_called_once_with("task-123")
        assert result is True

    @mark.asyncio
    async def test_retry_task_without_driver_raises_error(self) -> None:
        # Arrange
        executor = TaskExecutor(driver=None)

        # Act & Assert
        with raises(ValueError, match="Driver required for retry_task operation"):
            await executor.retry_task("task-123")

    @mark.asyncio
    async def test_retry_task_fallback_to_repository(self) -> None:
        # Arrange
        driver = AsyncMock()
        driver.retry_task.return_value = False  # Efficient retry fails
        driver.retry_raw_task.return_value = True

        repository = AsyncMock()
        repository._find_task_with_metadata.return_value = (
            b"task_bytes",
            "queue1",
            "failed",
        )

        executor = TaskExecutor(driver=driver, repository=repository)

        # Act
        result = await executor.retry_task("task-123")

        # Assert
        repository._find_task_with_metadata.assert_called_once_with("task-123")
        driver.retry_raw_task.assert_called_once_with("queue1", b"task_bytes")
        assert result is True

    @mark.asyncio
    async def test_retry_task_fallback_without_repository_returns_false(self) -> None:
        # Arrange
        driver = AsyncMock()
        driver.retry_task.return_value = False
        executor = TaskExecutor(driver=driver, repository=None)

        # Act & Assert
        with raises(
            ValueError,
            match="TaskRepository required for retry_task fallback when driver",
        ):
            await executor.retry_task("task-123")

    @mark.asyncio
    async def test_retry_task_fallback_task_not_found(self) -> None:
        # Arrange
        driver = AsyncMock()
        driver.retry_task.return_value = False

        repository = AsyncMock()
        repository._find_task_with_metadata.return_value = None

        executor = TaskExecutor(driver=driver, repository=repository)

        # Act
        result = await executor.retry_task("nonexistent")

        # Assert
        assert result is False

    @mark.asyncio
    async def test_retry_task_fallback_without_queue_name(self) -> None:
        # Arrange
        driver = AsyncMock()
        driver.retry_task.return_value = False

        repository = AsyncMock()
        repository._find_task_with_metadata.return_value = (
            b"task_bytes",
            None,  # No queue name
            "failed",
        )

        executor = TaskExecutor(driver=driver, repository=repository)

        # Act
        result = await executor.retry_task("task-123")

        # Assert
        assert result is False

    @mark.asyncio
    async def test_get_and_reset_failed_hook_error_count(self) -> None:
        # Arrange
        await reset_failed_hook_error_count()
        executor = TaskExecutor()

        class BrokenHookTask(AsyncTask[str]):
            async def execute(self) -> str:
                return "done"

            async def failed(self, exception: Exception) -> None:
                raise ValueError("Hook error")

        # Act
        await executor.handle_failed(BrokenHookTask(), RuntimeError("err1"))
        await executor.handle_failed(BrokenHookTask(), RuntimeError("err2"))
        count_before = await get_failed_hook_error_count()
        await reset_failed_hook_error_count()
        count_after = await get_failed_hook_error_count()

        # Assert
        assert count_before == 2
        assert count_after == 0
