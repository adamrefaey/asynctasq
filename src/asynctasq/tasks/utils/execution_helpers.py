"""Execution helpers for task types that need thread or process pool execution.

This module provides utility functions for executing synchronous code in
thread pools or process pools, enabling async tasks to offload blocking
operations without stalling the event loop.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from concurrent.futures import Executor


async def execute_in_thread(sync_callable: Callable[[], Any]) -> Any:
    """Execute synchronous callable in the default ThreadPoolExecutor.

    Runs the provided synchronous function in a thread pool to avoid blocking
    the async event loop. Uses asyncio's default ThreadPoolExecutor.

    Parameters
    ----------
    sync_callable : Callable[[], T]
        A zero-argument synchronous function to execute in a thread

    Returns
    -------
    T
        The result returned by sync_callable

    Examples
    --------
    >>> async def process_data():
    ...     def cpu_light_sync_work() -> int:
    ...         return sum(range(1000000))
    ...     result = await execute_in_thread(cpu_light_sync_work)
    ...     return result

    Notes
    -----
    - Uses asyncio's default ThreadPoolExecutor (shared across the event loop)
    - Suitable for I/O-bound synchronous operations
    - NOT suitable for CPU-intensive work (use execute_in_process_sync instead)
    - The callable must be thread-safe if it accesses shared state
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, sync_callable)


def _sync_process_task_worker(serialized_task: bytes) -> Any:
    """Worker function for executing SyncProcessTask in subprocess.

    This function is defined at module level so it can be pickled by multiprocessing.
    It deserializes the task and executes it in the subprocess.

    Parameters
    ----------
    serialized_task : bytes
        The serialized task data

    Returns
    -------
    Any
        The result from the task's execute() method
    """
    import asyncio

    from asynctasq.tasks.services.serializer import TaskSerializer

    # Deserialize the task using asyncio.run since deserialize is async
    serializer = TaskSerializer()
    task = asyncio.run(serializer.deserialize(serialized_task))

    # Execute the task's execute() method (which is synchronous for SyncProcessTask)
    # Type ignore because we know this is a SyncProcessTask at runtime
    return task.execute()  # type: ignore[attr-defined]


async def execute_in_process_sync(sync_callable: Callable[[], Any]) -> Any:
    """Execute synchronous callable in ProcessPoolExecutor for CPU-bound work.

    Runs the provided synchronous function in a process pool to bypass Python's
    Global Interpreter Lock (GIL) and enable true parallel execution of
    CPU-intensive operations.

    Parameters
    ----------
    sync_callable : Callable[[], T]
        A zero-argument synchronous function to execute in a subprocess.
        Must be picklable and its return value must be serializable.

    Returns
    -------
    T
        The result returned by sync_callable

    Examples
    --------
    >>> import numpy as np
    >>>
    >>> async def heavy_computation():
    ...     def compute_matrix() -> list:
    ...         matrix = np.random.rand(1000, 1000)
    ...         result = np.linalg.inv(matrix @ matrix.T)
    ...         return result.tolist()
    ...     result = await execute_in_process_sync(compute_matrix)
    ...     return result

    Notes
    -----
    - Uses a shared ProcessPoolExecutor managed by ProcessPoolManager
    - Bypasses Python's GIL for true parallel CPU-bound execution
    - The callable and its return value must be picklable/serializable
    - Each process has independent memory space (no shared state)
    - Subprocess startup overhead makes this slower for small tasks
    - Best for computationally expensive operations (>100ms)
    """
    from asynctasq.tasks.infrastructure.process_pool_manager import get_default_manager

    pool: Executor = get_default_manager().get_sync_pool()
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(pool, sync_callable)
