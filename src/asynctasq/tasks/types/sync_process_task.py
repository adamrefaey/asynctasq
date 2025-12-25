"""SyncProcessTask for sync CPU-bound tasks via ProcessPoolExecutor.

This module provides the SyncProcessTask class for synchronous CPU-intensive
operations that need to run in separate processes to bypass Python's GIL.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, override

from asynctasq.tasks.core.base_task import BaseTask

if TYPE_CHECKING:
    pass


class SyncProcessTask[T](BaseTask[T]):
    """Synchronous CPU-bound task executed in a separate process.

    Use SyncProcessTask for CPU-intensive synchronous operations that bypass the GIL:
    - Heavy numerical computations (NumPy, SciPy)
    - Machine learning model training
    - Data processing and transformations
    - Cryptographic operations
    - Image/video encoding and processing
    - Scientific simulations

    The execute() method runs in a ProcessPoolExecutor, enabling true parallel
    execution of CPU-bound code by bypassing Python's Global Interpreter Lock.

    For I/O-bound work, use AsyncTask or SyncTask instead.
    For async CPU work, use AsyncProcessTask.

    Type Parameters
    ---------------
    T : type
        Return type of the task's execute() method

    Examples
    --------
    CPU-intensive numerical computation:

    >>> from asynctasq.tasks import SyncProcessTask
    >>> import numpy as np
    >>>
    >>> class ComputeMatrix(SyncProcessTask[np.ndarray]):
    ...     size: int
    ...     config: TaskConfig = {
    ...         "queue": "cpu_intensive",
    ...         "timeout": 600,
    ...     }
    ...
    ...     def execute(self) -> np.ndarray:
    ...         # CPU-intensive matrix operations
    ...         matrix = np.random.rand(self.size, self.size)
    ...         result = np.linalg.inv(matrix @ matrix.T)
    ...         return result.tolist()  # Convert to serializable format

    Image processing:

    >>> class ProcessImage(SyncProcessTask[bytes]):
    ...     image_path: str
    ...
    ...     def execute(self) -> bytes:
    ...         from PIL import Image
    ...         img = Image.open(self.image_path)
    ...         # CPU-intensive image transformations
    ...         processed = img.resize((800, 600)).filter(ImageFilter.SHARPEN)
    ...         return processed.tobytes()

    Notes
    -----
    - All task parameters and return values must be msgpack-serializable
    - The execute() method runs in a subprocess, not the main process
    - Shared state (globals, files) must be handled carefully with multiprocessing
    """

    @override
    async def run(self) -> T:
        """Execute synchronous task in ProcessPoolExecutor.

        This method is called by the task execution framework and should not
        be overridden by users. Implement execute() instead.

        Returns
        -------
        T
            Result from the execute() method executed in a subprocess
        """
        import asyncio

        from asynctasq.tasks.infrastructure.process_pool_manager import get_default_manager
        from asynctasq.tasks.services.serializer import TaskSerializer
        from asynctasq.tasks.utils.execution_helpers import _sync_process_task_worker

        # Serialize this task instance using msgpack
        serializer = TaskSerializer()
        serialized_task = serializer.serialize(self)

        # Get the process pool
        pool = get_default_manager().get_sync_pool()

        # Execute the worker function with the serialized task
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(pool, _sync_process_task_worker, serialized_task)

    @abstractmethod
    def execute(self) -> T:
        """Execute sync CPU-bound logic (user implementation required).

        Implement this method with your task's CPU-intensive business logic.
        This method runs in a subprocess, bypassing Python's GIL for true
        parallel execution of CPU-bound code.

        Returns
        -------
        T
            Result of the synchronous CPU-bound operation

        Notes
        -----
        - This method runs in a subprocess, not the main process or thread pool
        - All arguments and return values must be msgpack-serializable
        - Use this for pure CPU-bound synchronous code
        - The subprocess runs independently and cannot access main process state
        - Exceptions raised here will trigger retry logic based on task configuration
        - For CPU work with async operations, use AsyncProcessTask instead
        """
        ...
