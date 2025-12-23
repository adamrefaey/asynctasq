"""Base task implementation providing foundation for all task types.

Defines BaseTask, the abstract base class for all task types. Provides configuration
management, lifecycle hooks (failed, should_retry), method chaining API (on_queue,
delay, retry_after), dispatch mechanism, and attempt tracking.
"""

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
    }
)


class BaseTask[T](ABC):
    """Abstract base class for all asynchronous task types.

    Provides foundation for creating background tasks that can be dispatched to a queue,
    executed by workers, and automatically retried on failure. Uses Template Method pattern:
    framework calls run() (implemented by subclasses), users override execute() with logic.

    Type Parameter
    --------------
    T : Return type of the task's execute() method

    Attributes
    ----------
    config : TaskConfig
        Task configuration (queue, retries, timeout)
    _task_id : str | None
        Unique task identifier (set by dispatcher)
    _current_attempt : int
        Execution attempt counter (starts at 0)
    _dispatched_at : datetime | None
        Timestamp when task was dispatched
    _delay_seconds : int | None
        Scheduled delay before execution
    """

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

    @classmethod
    def _extract_config_from_class(cls) -> dict[str, Any]:
        """Extract TaskConfig values from class attributes.

        Returns
        -------
        dict[str, Any]
            Dictionary with queue, max_attempts, retry_delay, timeout from class attributes
        """
        return {
            "queue": getattr(cls, "queue", "default"),
            "max_attempts": getattr(cls, "max_attempts", 3),
            "retry_delay": getattr(cls, "retry_delay", 60),
            "timeout": getattr(cls, "timeout", None),
        }

    def __init__(self, **kwargs: Any) -> None:
        """Initialize task instance with custom parameters.

        Initializes configuration from class attributes and sets user-provided parameters
        as instance attributes. All keyword arguments become accessible as self.param_name.

        Parameters
        ----------
        **kwargs : Any
            Arbitrary keyword arguments that become task instance attributes

        Raises
        ------
        ValueError
            If parameter name starts with underscore or matches reserved names
        """
        # Initialize configuration from class attributes if present
        # This supports the pattern: class MyTask: queue = "custom"
        config_values = self._extract_config_from_class()
        self.config = TaskConfig(**config_values)

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

        Called by worker when beginning task execution. Centralizes attempt incrementing
        logic. Counter starts at 0 and increments to 1 before first execution.

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
        """Lifecycle hook called when task permanently fails after exhausting all retries.

        Override to implement custom failure handling (alerting, cleanup, logging). Called
        after all retry attempts exhausted. Exceptions raised here are logged but don't
        affect task processing. Keep idempotent as may be called multiple times on restart.

        Parameters
        ----------
        exception : Exception
            Exception that caused the final failure
        """
        ...

    def should_retry(self, exception: Exception) -> bool:
        """Lifecycle hook to determine if task should retry after an exception.

        Override to implement custom retry logic based on exception type. Combined with
        max_attempts limit: both must be True for retry to occur. Default returns True.

        Parameters
        ----------
        exception : Exception
            Exception that occurred during task execution

        Returns
        -------
        bool
            True to retry, False to fail immediately and skip remaining attempts
        """
        return True

    @abstractmethod
    async def run(self) -> T:
        """Execute task using the subclass-defined execution strategy (framework entry point).

        Abstract method implemented by task type subclasses to define execution strategy
        (async/sync, process/thread). Framework calls this from TaskExecutor with timeout
        wrapper. Users should implement execute() method, not override run().

        Returns
        -------
        T
            Result of task execution
        """
        ...

    def on_queue(self, queue_name: str) -> Self:
        """Set the queue name for task dispatch (method chaining).

        Parameters
        ----------
        queue_name : str
            Name of the queue to dispatch the task to

        Returns
        -------
        Self
            Returns self for method chaining
        """
        from dataclasses import replace

        self.config = replace(self.config, queue=queue_name)
        return self

    def delay(self, seconds: int) -> Self:
        """Set execution delay before task runs (method chaining).

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
        """Set retry delay between failed attempts (method chaining).

        Parameters
        ----------
        seconds : int
            Number of seconds to wait between retry attempts

        Returns
        -------
        Self
            Returns self for method chaining
        """
        from dataclasses import replace

        self.config = replace(self.config, retry_delay=seconds)
        return self

    async def dispatch(self) -> str:
        """Dispatch task to queue backend for asynchronous execution.

        This method takes NO arguments. Task configuration (queue, delays, retries)
        must be set via method chaining (.on_queue(), .delay(), .retry_after())
        before calling dispatch().

        Serializes task and submits to configured queue backend for processing by a worker.

        Returns
        -------
        str
            Unique task identifier (UUID)

        Example
        -------
        ```python
        # Class-based task
        task_id = await MyTask(x=5).delay(60).on_queue("custom").dispatch()

        # Function-based task
        task_id = await my_task(x=5).delay(60).on_queue("custom").dispatch()
        ```
        """
        from asynctasq.core.dispatcher import get_dispatcher

        # Pass driver override to get_dispatcher if set
        driver_override = self.config.driver_override
        return await get_dispatcher(driver_override).dispatch(self)
