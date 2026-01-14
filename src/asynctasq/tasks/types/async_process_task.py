"""AsyncProcessTask for async CPU-bound tasks via ProcessPoolExecutor.

This module provides the AsyncProcessTask class for async CPU-intensive operations
that need to run in separate processes to bypass Python's GIL (Global Interpreter Lock).
Uses warm event loops for optimal performance, with fallback to on-demand loop creation.
"""

from __future__ import annotations

from abc import abstractmethod
import asyncio
import inspect
import logging
from typing import Any, override

from asynctasq.tasks.core.base_task import BaseTask
from asynctasq.tasks.infrastructure.process_pool_manager import (
    get_default_manager,
    get_warm_event_loop,
    increment_fallback_count,
)
from asynctasq.utils.loop import run

logger = logging.getLogger(__name__)


class AsyncProcessTask(BaseTask):
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

    Examples
    --------
    CPU-intensive data processing with async operations:

    >>> from asynctasq.tasks import AsyncProcessTask
    >>> import numpy as np
    >>>
    >>> class ProcessLargeDataset(AsyncProcessTask):
    ...     data_url: str
    ...     config: TaskConfig = {
    ...         "queue": "cpu_intensive",
    ...         "timeout": 300,
    ...     }
    ...
    ...     async def execute(self):
    ...         # Async I/O to fetch data
    ...         async with httpx.AsyncClient() as client:
    ...             data = await client.get(self.data_url)
    ...
    ...         # CPU-intensive processing (runs in subprocess, bypasses GIL)
    ...         processed = np.array(data.json()).mean(axis=0)
    ...         return {"result": processed.tolist()}

    Notes
    -----
    - All task parameters and return values must be serializable
    - Process pool is shared across tasks for efficiency
    - Warm event loops reduce overhead compared to creating new loops per task
    """

    @override
    async def run(self) -> Any:
        """Execute task in ProcessPoolExecutor with warm event loop.

        This method is called by the task execution framework and should not
        be overridden by users. Implement execute() instead.

        Returns
        -------
        Any
            Result from the execute() method executed in a subprocess
        """
        # Get process pool (auto-initializes if needed)
        pool = get_default_manager().get_async_pool()

        # Get current event loop
        loop = asyncio.get_running_loop()

        # Run execute() in process pool with warm event loop or fallback runner
        return await loop.run_in_executor(pool, self._run_async_in_process)

    def _run_async_in_process(self) -> Any:
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
    async def execute(self) -> Any:
        """Execute async CPU-bound logic (user implementation required).

        Implement this method with your task's CPU-intensive business logic.
        This method runs in a subprocess, bypassing Python's GIL for true
        parallel execution of CPU-bound code.

        Returns
        -------
        Any
            Result of the async CPU-bound operation

        Notes
        -----
        - This method runs in a subprocess, not the main process
        - All arguments and return values must be serializable
        - Use async/await for any I/O operations within the CPU-bound work
        - The subprocess has its own event loop for async operations
        - Exceptions raised here will trigger retry logic based on task configuration
        - Shared state (globals, files) must be handled with care due to multiprocessing
        """
        ...

    def __reduce__(self) -> tuple[Any, ...]:
        """Custom serialization support for ProcessPoolExecutor inter-process communication.

        When AsyncProcessTask is sent to a subprocess via ProcessPoolExecutor,
        Python's multiprocessing internally uses pickle for IPC. This method ensures
        the task can be reconstructed in the subprocess even if it was originally
        loaded from a __main__ module.

        Returns
        -------
        tuple
            Reduction tuple: (callable, args) where callable(*args) reconstructs the object
        """
        # Get the class file path for reliable reconstruction
        class_file = getattr(self, "_original_class_file", None)
        if not class_file:
            try:
                class_file = inspect.getfile(self.__class__)
                # Only store if it's a real file (not built-in or C extension)
                if class_file and class_file.startswith("<"):
                    class_file = None
            except (TypeError, OSError):
                class_file = None

        # Prepare reconstruction data
        return (
            _reconstruct_async_process_task,
            (
                self.__class__.__module__,
                self.__class__.__name__,
                class_file,
                self.__dict__.copy(),
            ),
        )


def _reconstruct_async_process_task(
    module_name: str, class_name: str, class_file: str | None, state: dict[str, Any]
) -> Any:
    """Reconstruct AsyncProcessTask instance in subprocess.

    This function is called during inter-process communication to recreate the task
    instance in the subprocess. It uses FunctionResolver to handle __main__ modules correctly.

    Parameters
    ----------
    module_name : str
        Original module name (may be __asynctasq_main_xxx__)
    class_name : str
        Class name
    class_file : str | None
        Path to the class file (for __main__ modules)
    state : dict
        Instance __dict__ to restore

    Returns
    -------
    Any
        Reconstructed task instance
    """
    from asynctasq.tasks.services.function_resolver import FunctionResolver

    # Normalize __asynctasq_main_xxx__ back to __main__ for resolution
    if module_name.startswith("__asynctasq_main_"):
        module_name = "__main__"

    # Use FunctionResolver to load the module (handles __main__ correctly)
    resolver = FunctionResolver()
    module = resolver.get_module(module_name, class_file)
    task_class = getattr(module, class_name)

    # Create a new instance without calling __init__
    # We'll restore the state directly
    instance = task_class.__new__(task_class)
    instance.__dict__.update(state)

    return instance
