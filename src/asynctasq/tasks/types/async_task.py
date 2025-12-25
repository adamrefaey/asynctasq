"""AsyncTask for async I/O-bound tasks.

This module provides the AsyncTask class for defining asynchronous I/O-bound
background tasks that run in the event loop without blocking.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import override

from asynctasq.tasks.core.base_task import BaseTask


class AsyncTask[T](BaseTask[T]):
    """Async I/O-bound task executed in the event loop.

    Use AsyncTask for I/O-bound operations that benefit from async/await:
    - Database queries (asyncpg, motor, etc.)
    - HTTP requests (aiohttp, httpx)
    - File I/O (aiofiles)
    - Network operations
    - Any operation that involves waiting for external resources

    For CPU-intensive computations, use AsyncProcessTask or SyncProcessTask instead
    to avoid blocking the event loop.

    Type Parameters
    ---------------
    T : type
        Return type of the task's execute() method

    Examples
    --------
    Fetch data from an API:

    >>> from asynctasq.tasks import AsyncTask
    >>> import httpx
    >>>
    >>> class FetchUserData(AsyncTask[dict]):
    ...     user_id: int
    ...
    ...     async def execute(self) -> dict:
    ...         async with httpx.AsyncClient() as client:
    ...             response = await client.get(f"https://api.example.com/users/{self.user_id}")
    ...             return response.json()
    >>>
    >>> # Dispatch task to queue
    >>> task_id = await FetchUserData(user_id=123).dispatch()

    With configuration:

    >>> class SendEmail(AsyncTask[str]):
    ...     config: TaskConfig = {
    ...         "queue": "emails",
    ...         "max_attempts": 5,
    ...         "timeout": 30,
    ...     }
    ...     to: str
    ...     subject: str
    ...     body: str
    ...
    ...     async def execute(self) -> str:
    ...         # Send email via async SMTP
    ...         return f"Email sent to {self.to}"
    """

    @override
    async def run(self) -> T:
        """Execute task by delegating to the user-defined execute() method.

        This method is called by the task execution framework and should not
        be overridden by users. Implement execute() instead.

        Returns
        -------
        T
            Result from the execute() method
        """
        return await self.execute()

    @abstractmethod
    async def execute(self) -> T:
        """Execute async I/O-bound logic (user implementation required).

        Implement this method with your task's business logic. This method
        runs in the event loop and should use async/await for I/O operations.

        Returns
        -------
        T
            Result of the async operation

        Notes
        -----
        - Use async/await for all I/O operations to avoid blocking the event loop
        - The return value must be msgpack-serializable
        - Exceptions raised here will trigger retry logic based on task configuration
        - This method is automatically wrapped with timeout enforcement if configured
        """
        ...
