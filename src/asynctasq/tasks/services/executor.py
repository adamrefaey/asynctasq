"""Task execution and lifecycle management.

Framework-level error handling: timeout, retry logic, user hooks (should_retry, failed).
Performance-optimized for high-throughput task processing.
See docs/error-handling-architecture.md for complete documentation.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

# Import Config at module level to avoid repeated imports
from asynctasq.config import Config

if TYPE_CHECKING:
    from asynctasq.drivers.base_driver import BaseDriver
    from asynctasq.tasks.core.base_task import BaseTask
    from asynctasq.tasks.services.repository import TaskRepository
    from asynctasq.tasks.services.serializer import TaskSerializer

logger = logging.getLogger(__name__)

# Metrics: Track failed hook errors for observability
# Use simple atomic counter instead of lock (sufficient for incrementing)
_failed_hook_error_count: int = 0


def get_failed_hook_error_count() -> int:
    """Get count of errors in task.failed() hooks (for monitoring/alerting).

    Returns:
        Total number of failed hook errors since process start
    """
    return _failed_hook_error_count


def reset_failed_hook_error_count() -> None:
    """Reset failed hook error counter (for testing)."""
    global _failed_hook_error_count
    _failed_hook_error_count = 0


class TaskExecutor:
    """Handles task execution, retry logic, and lifecycle hooks.

    Performance optimizations:
    - Cached config access
    - Minimized attribute lookups
    - No async lock for simple counter

    Note: Does not use __slots__ to allow instance attribute patching in tests.
    Memory overhead is negligible as TaskExecutor is typically instantiated once per worker.
    """

    def __init__(
        self,
        driver: BaseDriver | None = None,
        serializer: TaskSerializer | None = None,
        repository: TaskRepository | None = None,
    ) -> None:
        """Initialize with optional dependencies."""
        self.driver = driver
        self.serializer = serializer
        self.repository = repository

    async def execute(self, task: BaseTask, timeout: float | None = None) -> None:
        """Execute task with timeout (framework entry point).

        Wraps task.run() with timeout. Caller handles exceptions.

        Args:
            task: Task instance to execute
            timeout: Optional timeout override (uses task.config.get("timeout") if None)

        Raises:
            Exception: Any exception from task.run()
        """
        effective_timeout = timeout if timeout is not None else task.config.get("timeout")

        if effective_timeout:
            await asyncio.wait_for(task.run(), timeout=effective_timeout)
        else:
            await task.run()

    def should_retry(self, task: BaseTask, exception: Exception) -> bool:
        """Determine if task should retry after exception.

        Combines framework policy (current_attempt < max_attempts) with user policy (task.should_retry()).

        Args:
            task: Task that failed
            exception: Exception that occurred

        Returns:
            True to retry, False if permanently failed
        """
        config = Config.get()
        max_attempts = task.config.get("max_attempts", config.task_defaults.max_attempts)
        return task._current_attempt < max_attempts and task.should_retry(exception)

    async def handle_failed(self, task: BaseTask, exception: Exception) -> None:
        """Call task.failed() hook when retries exhausted (best-effort).

        Tracks failures in the hook itself for observability (use get_failed_hook_error_count()).

        Args:
            task: Task that permanently failed
            exception: Exception that caused failure
        """
        try:
            await task.failed(exception)
        except Exception as e:
            from asynctasq.tasks.utils.logger import log_task_error

            # Increment counter without lock (atomic in CPython due to GIL)
            global _failed_hook_error_count
            _failed_hook_error_count += 1

            log_task_error(
                task,
                "Error in task.failed() handler",
                error=str(e),
                original_error=str(exception),
                failed_hook_errors=_failed_hook_error_count,
            )

    async def retry_task(self, task_id: str) -> bool:
        """Retry failed task by ID.

        Tries driver.retry_task() first, falls back to repository lookup.

        Args:
            task_id: Task ID to retry

        Returns:
            True if retry succeeded, False otherwise

        Raises:
            ValueError: If driver or repository not configured
        """
        driver = self.driver
        if driver is None:
            raise ValueError("Driver required for retry_task operation")

        # Try driver's direct retry first (efficient for Postgres/MySQL)
        if await driver.retry_task(task_id):
            return True

        # Fall back to repository lookup + retry_raw_task (for Redis)
        repository = self.repository
        if repository is None:
            raise ValueError(
                "TaskRepository required for retry_task fallback when driver "
                "doesn't support efficient ID-based retry"
            )

        result = await repository._find_task_with_metadata(task_id)
        if result is None:
            return False

        raw_bytes, queue_name, _ = result
        if queue_name is None:
            return False
        return await driver.retry_raw_task(queue_name, raw_bytes)
