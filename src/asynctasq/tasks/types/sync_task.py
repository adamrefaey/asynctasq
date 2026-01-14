"""SyncTask for sync I/O-bound tasks via ThreadPoolExecutor.

This module provides the SyncTask class for synchronous I/O-bound tasks
that need to run in a thread pool to avoid blocking the async event loop.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, override

from asynctasq.tasks.core.base_task import BaseTask
from asynctasq.tasks.utils.execution_helpers import execute_in_thread


class SyncTask(BaseTask):
    """Synchronous I/O-bound task executed in a thread pool.

    Use SyncTask for synchronous I/O-bound operations that would block the event loop:
    - Synchronous HTTP libraries (requests)
    - Blocking file I/O operations
    - Synchronous database drivers (psycopg2, pymysql)
    - Third-party libraries without async support
    - Legacy code that cannot be easily converted to async

    The execute() method runs in a ThreadPoolExecutor, preventing event loop blocking.
    For CPU-intensive work, use SyncProcessTask to bypass the GIL.

    Examples
    --------
    HTTP request with synchronous library:

    >>> from asynctasq.tasks import SyncTask
    >>> import requests
    >>>
    >>> class FetchWebpage(SyncTask):
    ...     url: str
    ...
    ...     def execute(self):
    ...         response = requests.get(self.url)
    ...         return response.text
    >>>
    >>> # Dispatch to queue
    >>> task_id = await FetchWebpage(url="https://example.com").dispatch()

    Database operation with synchronous driver:

    >>> class QueryDatabase(SyncTask):
    ...     config: TaskConfig = {
    ...         "queue": "database",
    ...         "timeout": 60,
    ...     }
    ...     query: str
    ...
    ...     def execute(self):
    ...         import psycopg2
    ...         conn = psycopg2.connect("dbname=mydb")
    ...         cursor = conn.cursor()
    ...         cursor.execute(self.query)
    ...         return cursor.fetchall()
    """

    @override
    async def run(self) -> Any:
        """Execute synchronous task in ThreadPoolExecutor.

        This method is called by the task execution framework and should not
        be overridden by users. Implement execute() instead.

        Returns
        -------
        Any
            Result from the execute() method
        """
        return await execute_in_thread(self.execute)

    @abstractmethod
    def execute(self) -> Any:
        """Execute sync I/O-bound logic (user implementation required).

        Implement this method with your task's business logic. This method
        runs in a separate thread from ThreadPoolExecutor to prevent blocking
        the async event loop.

        Returns
        -------
        Any
            Result of the synchronous operation

        Notes
        -----
        - This method runs in a thread pool worker, not the main event loop
        - The return value must be serializable
        - Avoid CPU-intensive operations; use SyncProcessTask for those
        - Thread-safe operations only (or use proper locking)
        - Exceptions raised here will trigger retry logic based on task configuration
        """
        ...
