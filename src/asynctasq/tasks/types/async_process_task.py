"""AsyncProcessTask for async CPU-bound tasks via ProcessPoolExecutor.

Uses a module-level runner helper from `asynctasq.utils.loop` as a fallback
when a warm event loop is not available in the subprocess.
"""

from __future__ import annotations

from abc import abstractmethod
import asyncio
import logging

from asynctasq.tasks.core.base_task import BaseTask
from asynctasq.tasks.infrastructure.process_pool_manager import (
    get_default_manager,
    get_warm_event_loop,
    increment_fallback_count,
)

logger = logging.getLogger(__name__)


class AsyncProcessTask[T](BaseTask[T]):
    """Async CPU-bound task via ProcessPoolExecutor with warm event loops.

    For async CPU-bound work (e.g., ML inference with async preprocessing).
    For I/O-bound work, use AsyncTask.
    """

    async def run(self) -> T:
        """Execute task via ProcessPoolExecutor with warm event loop."""
        # Get process pool (auto-initializes if needed)
        pool = get_default_manager().get_async_pool()

        # Get current event loop
        loop = asyncio.get_running_loop()

        # Run execute() in process pool with a uvloop-based runner helper
        return await loop.run_in_executor(pool, self._run_async_in_process)

    def _run_async_in_process(self) -> T:
        """Run async execute() using warm event loop (falls back to uvloop runner)."""
        process_loop = get_warm_event_loop()

        if process_loop is not None:
            # Use warm event loop (fast path)
            future = asyncio.run_coroutine_threadsafe(self.execute(), process_loop)
            return future.result()
        else:
            # Fallback to uvloop-based runner if warm loop not initialized
            current_count = increment_fallback_count()

            logger.warning(
                "Warm event loop not available, falling back to uvloop runner",
                extra={
                    "task_class": self.__class__.__name__,
                    "fallback_count": current_count,
                    "performance_impact": "high",
                    "recommendation": "Call manager.initialize() during worker startup",
                },
            )
            # Use the uvloop-based runner directly in subprocess fallback.
            from asynctasq.utils.loop import run as uv_run

            return uv_run(self.execute())

    @abstractmethod
    async def execute(self) -> T:
        """Execute async CPU-bound logic (user implementation, runs in subprocess).

        Note:
            Arguments and return value must be serializable (msgpack-compatible).
        """
        ...
