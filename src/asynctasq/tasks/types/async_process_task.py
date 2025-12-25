"""AsyncProcessTask for async CPU-bound tasks via ProcessPoolExecutor.

This module provides the AsyncProcessTask class for async CPU-intensive operations
that need to run in separate processes to bypass Python's GIL (Global Interpreter Lock).
Uses warm event loops for optimal performance, with fallback to on-demand loop creation.
"""

from __future__ import annotations

from abc import abstractmethod
import asyncio
import logging
from typing import override

from asynctasq.tasks.core.base_task import BaseTask
from asynctasq.tasks.infrastructure.process_pool_manager import (
    get_default_manager,
    get_warm_event_loop,
    increment_fallback_count,
)
from asynctasq.utils.loop import run

logger = logging.getLogger(__name__)


class AsyncProcessTask[T](BaseTask[T]):
    """Asynchronous CPU-bound task executed in a separate process.

    Use AsyncProcessTask for CPU-intensive async operations that bypass the GIL:
    - Machine learning inference with async I/O preprocessing
    - Parallel data processing with async result aggregation
    - Cryptographic operations with async callbacks
    - Image/video processing with async storage operations
    - Scientific computations with async data loading

    The task runs in a ProcessPoolExecutor with warm event loops for performance.
    For I/O-bound async work, use AsyncTask instead (runs in main event loop).
    For synchronous CPU work, use SyncProcessTask.

    Type Parameters
    ---------------
    T : type
        Return type of the task's execute() method

    Examples
    --------
    CPU-intensive data processing with async operations:

    >>> from asynctasq.tasks import AsyncProcessTask
    >>> import numpy as np
    >>>
    >>> class ProcessLargeDataset(AsyncProcessTask[dict]):
    ...     data_url: str
    ...     config: TaskConfig = {
    ...         "queue": "cpu_intensive",
    ...         "timeout": 300,
    ...     }
    ...
    ...     async def execute(self) -> dict:
    ...         # Async I/O to fetch data
    ...         async with httpx.AsyncClient() as client:
    ...             data = await client.get(self.data_url)
    ...
    ...         # CPU-intensive processing (runs in subprocess, bypasses GIL)
    ...         processed = np.array(data.json()).mean(axis=0)
    ...         return {"result": processed.tolist()}

    Notes
    -----
    - All task parameters and return values must be msgpack-serializable
    - Process pool is shared across tasks for efficiency
    - Warm event loops reduce overhead compared to creating new loops per task
    """

    @override
    async def run(self) -> T:
        """Execute task in ProcessPoolExecutor with warm event loop.

        This method is called by the task execution framework and should not
        be overridden by users. Implement execute() instead.

        Returns
        -------
        T
            Result from the execute() method executed in a subprocess
        """
        # Get process pool (auto-initializes if needed)
        pool = get_default_manager().get_async_pool()

        # Get current event loop
        loop = asyncio.get_running_loop()

        # Run execute() in process pool with warm event loop or fallback runner
        return await loop.run_in_executor(pool, self._run_async_in_process)

    def _run_async_in_process(self) -> T:
        """Run async execute() using warm event loop with fallback.

        Attempts to use a pre-initialized warm event loop for performance.
        Falls back to creating a new loop if warm loop is unavailable.

        Returns
        -------
        T
            Result from execute() method

        Warnings
        --------
        Logs a warning if fallback loop creation is used, as this has
        performance impact. Initialize the process pool manager during
        worker startup to enable warm loops.
        """
        process_loop = get_warm_event_loop()

        if process_loop is not None:
            # Fast path: use pre-initialized warm event loop
            future = asyncio.run_coroutine_threadsafe(self.execute(), process_loop)
            return future.result()

        # Fallback path: create new event loop (performance impact)
        current_count = increment_fallback_count()

        logger.warning(
            "Warm event loop not available, falling back to on-demand loop creation",
            extra={
                "task_class": self.__class__.__name__,
                "fallback_count": current_count,
                "performance_impact": "high",
                "recommendation": "Call manager.initialize() during worker startup",
            },
        )
        # Use the event loop runner to create and run a new loop
        return run(self.execute())

    @abstractmethod
    async def execute(self) -> T:
        """Execute async CPU-bound logic (user implementation required).

        Implement this method with your task's CPU-intensive business logic.
        This method runs in a subprocess, bypassing Python's GIL for true
        parallel execution of CPU-bound code.

        Returns
        -------
        T
            Result of the async CPU-bound operation

        Notes
        -----
        - This method runs in a subprocess, not the main process
        - All arguments and return values must be msgpack-serializable
        - Use async/await for any I/O operations within the CPU-bound work
        - The subprocess has its own event loop for async operations
        - Exceptions raised here will trigger retry logic based on task configuration
        - Shared state (globals, files) must be handled with care due to multiprocessing
        """
        ...
