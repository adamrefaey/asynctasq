"""Base task implementation providing foundation for all task types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Self

from asynctasq.tasks.core.task_config import TaskConfig

# Reserved parameter names that would shadow task methods/attributes
RESERVED_NAMES = frozenset(
    {
        "config",
        "run",
        "execute",
        "dispatch",
        "failed",
        "should_retry",
        "on_queue",
        "delay",
        "retry_after",
        "max_attempts",
        "timeout",
    }
)


class BaseTask[T](ABC):
    """Abstract base class for all asynchronous task types.

    Provides foundation for creating background tasks that can be dispatched to a queue,
    executed by workers, and automatically retried on failure.

    Type Parameter
    --------------
    T : Return type of the task's execute() method

    Example
    -------
    ```python
    from asynctasq.tasks import AsyncTask, TaskConfig

    class SendEmail(AsyncTask[str]):
        # Optional: set defaults via config dict (type-safe)
        config: TaskConfig = {
            "queue": "emails",
            "max_attempts": 5,
            "timeout": 30,
        }

        # Task parameters
        to: str
        subject: str

        async def execute(self) -> str:
            # Send email logic
            return f"Sent to {self.to}"

    # Usage - uses config defaults
    task_id = await SendEmail(to="user@example.com", subject="Hi").dispatch()

    # Override defaults with method chaining
    task_id = await SendEmail(to="admin@example.com", subject="Alert")
        .max_attempts(10)
        .timeout(60)
        .retry_after(120)
        .dispatch()
    ```
    """

    # Task configuration
    config: TaskConfig

    # Delay configuration (separate from TaskConfig for runtime flexibility)
    _delay_seconds: int | None = None

    @classmethod
    def _get_additional_reserved_names(cls) -> frozenset[str]:
        """Extension point for subclasses to declare additional reserved parameter names.

        Returns
        -------
        frozenset[str]
            Set of additional reserved parameter names (default: empty set)
        """
        return frozenset()

    def __init__(self, **kwargs: Any) -> None:
        """Initialize task instance with custom parameters.

        Parameters
        ----------
        **kwargs : Any
            Arbitrary keyword arguments that become task instance attributes

        Raises
        ------
        ValueError
            If parameter name starts with underscore or matches reserved names
        """
        # Combine base reserved names with subclass-specific ones
        all_reserved = RESERVED_NAMES | self._get_additional_reserved_names()

        for key, value in kwargs.items():
            if key.startswith("_"):
                raise ValueError(
                    f"Parameter name '{key}' is reserved for internal use. "
                    f"Task parameters cannot start with underscore."
                )
            if key in all_reserved:
                raise ValueError(
                    f"Parameter name '{key}' is a reserved name that would "
                    f"shadow a task method or attribute. Choose a different name."
                )
            setattr(self, key, value)

        # Metadata (managed internally by dispatcher/worker)
        self._task_id: str | None = None
        # Number of attempts that have already been executed.
        # Starts at 0; worker will increment to 1 when execution actually starts.
        self._current_attempt: int = 0
        self._dispatched_at: datetime | None = None

    def mark_attempt_started(self) -> int:
        """Increment the current attempt counter and return the new value.

        Returns
        -------
        int
            New attempt number after incrementing (1 for first attempt, 2 for first retry, etc.)
        """
        self._current_attempt += 1
        return self._current_attempt

    @property
    def current_attempt(self) -> int:
        """Read-only view of the current attempt counter.

        Returns
        -------
        int
            Current attempt number (0 before first execution, 1 for first attempt, 2 for first retry)
        """
        return self._current_attempt

    async def failed(self, exception: Exception) -> None:  # noqa: B027
        """Lifecycle hook called when task permanently fails.

        Called after all retry attempts exhausted. Exceptions raised here are logged but don't
        affect task processing.

        Parameters
        ----------
        exception : Exception
            Exception that caused the final failure
        """
        ...

    def should_retry(self, exception: Exception) -> bool:
        """Lifecycle hook to determine if task should retry after an exception.

        Override this method to implement custom retry logic based on exception type.
        Combined with max_attempts limit: both conditions must be True for retry.
        Default implementation always returns True (retry unless max_attempts reached).

        Parameters
        ----------
        exception : Exception
            The exception that caused the task execution to fail

        Returns
        -------
        bool
            True to allow retry (if within max_attempts), False to fail immediately

        Examples
        --------
        Skip retries for specific exception types:

        >>> def should_retry(self, exception: Exception) -> bool:
        ...     # Don't retry validation errors
        ...     if isinstance(exception, ValueError):
        ...         return False
        ...     return True

        Notes
        -----
        - The framework checks current_attempt < max_attempts separately
        - Returning False skips all remaining retry attempts
        - This method is called after each failed execution attempt
        - Current attempt number is available via self._current_attempt
        """
        return True

    @abstractmethod
    async def run(self) -> T:
        """Execute task using the subclass-defined execution strategy.

        Framework calls this from TaskExecutor with timeout wrapper.
        Users should implement execute() method, not override run().

        Returns
        -------
        T
            Result of task execution
        """
        ...

    def on_queue(self, queue_name: str) -> Self:
        """Set the queue name for task dispatch.

        Parameters
        ----------
        queue_name : str
            Name of the queue to dispatch the task to

        Returns
        -------
        Self
            Returns self for method chaining
        """
        self.config = {**self.config, "queue": queue_name}
        return self

    def delay(self, seconds: int) -> Self:
        """Set execution delay before task runs.

        Parameters
        ----------
        seconds : int
            Number of seconds to delay task execution

        Returns
        -------
        Self
            Returns self for method chaining
        """
        self._delay_seconds = seconds
        return self

    def retry_after(self, seconds: int) -> Self:
        """Set retry delay between failed attempts.

        Parameters
        ----------
        seconds : int
            Number of seconds to wait between retry attempts

        Returns
        -------
        Self
            Returns self for method chaining
        """
        self.config = {**self.config, "retry_delay": seconds}
        return self

    def max_attempts(self, attempts: int) -> Self:
        """Set maximum number of retry attempts.

        Parameters
        ----------
        attempts : int
            Maximum number of times to retry failed task (including initial attempt)

        Returns
        -------
        Self
            Returns self for method chaining
        """
        self.config = {**self.config, "max_attempts": attempts}
        return self

    def timeout(self, seconds: int | None) -> Self:
        """Set task execution timeout.

        Parameters
        ----------
        seconds : int | None
            Maximum number of seconds for task execution (None = no timeout)

        Returns
        -------
        Self
            Returns self for method chaining
        """
        self.config = {**self.config, "timeout": seconds}
        return self

    async def dispatch(self) -> str:
        """Dispatch task to queue backend for asynchronous execution.

        Returns
        -------
        str
            Unique task identifier (UUID)
        """
        from asynctasq.core.dispatcher import get_dispatcher

        # Pass driver override to get_dispatcher if set
        driver = self.config.get("driver")
        return await get_dispatcher(driver).dispatch(self)
