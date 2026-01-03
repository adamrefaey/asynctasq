"""FunctionTask and @task decorator with smart execution routing."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import functools
import inspect
from typing import Any, Protocol, TypeGuard, final, overload

from asynctasq.drivers.base_driver import BaseDriver
from asynctasq.tasks.core.base_task import BaseTask


def _is_async_callable(func: Callable[..., Any]) -> TypeGuard[Callable[..., Awaitable[Any]]]:
    """Type guard for async callables."""
    return inspect.iscoroutinefunction(func)


def _run_async_in_subprocess(
    func: Callable[..., Awaitable[Any]], args: tuple[Any, ...], kwargs: dict[str, Any]
) -> Any:
    """Helper to run async function in subprocess.

    Uses the project's event loop runner which automatically detects
    and uses uvloop if available, otherwise falls back to asyncio.

    Must be module-level for ProcessPoolExecutor compatibility.
    """

    async def async_wrapper():
        return await func(*args, **kwargs)

    from asynctasq.utils.loop import run

    return run(async_wrapper())


@final
class FunctionTask[T](BaseTask[T]):
    """Internal wrapper for @task decorated functions.

    Routes execution based on function type and process flag (async/sync × I/O-bound/CPU-bound).
    Do not subclass; use @task decorator instead.
    """

    @classmethod
    def _get_additional_reserved_names(cls) -> frozenset[str]:
        """FunctionTask reserves func, args, kwargs."""
        return frozenset({"func", "args", "kwargs"})

    def __init__(
        self,
        func: Callable[..., T],
        *args: Any,
        use_process: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize with wrapped function and arguments.

        Args:
            func: Function to wrap
            *args: Positional arguments
            use_process: Whether to use process pool for execution
            **kwargs: Keyword arguments

        Raises:
            ValueError: If kwargs use reserved names
        """
        # Call parent init which handles all validation
        super().__init__(**kwargs)

        # FunctionTask-specific setup
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self._use_process = use_process

        # Override config with decorator values
        # FunctionTask config always comes from @task decorator, not class attributes
        self.config = {
            **self.config,
            "queue": getattr(func, "_task_queue", self.config.get("queue")) or "default",
            "max_attempts": getattr(func, "_task_max_attempts", self.config.get("max_attempts"))
            or 3,
            "retry_delay": getattr(func, "_task_retry_delay", self.config.get("retry_delay")) or 60,
            "timeout": getattr(func, "_task_timeout", self.config.get("timeout")),
            "visibility_timeout": getattr(
                func, "_task_visibility_timeout", self.config.get("visibility_timeout")
            )
            or 300,
            "driver": getattr(func, "_task_driver", self.config.get("driver")),
            "correlation_id": self.config.get("correlation_id"),
        }

    async def run(self) -> T:
        """Execute via appropriate executor (async/sync × thread/process)."""
        # Resolve any LazyOrmProxy parameters before executing the task
        await self._resolve_lazy_proxies()

        if inspect.iscoroutinefunction(self.func):
            return await self._execute_async()
        return await self._execute_sync()

    async def _resolve_lazy_proxies(self) -> None:
        """Resolve all LazyOrmProxy instances in args and kwargs."""
        from asynctasq.serializers.hooks.orm.lazy_proxy import resolve_lazy_proxies

        # Resolve args
        if self.args:
            self.args = await resolve_lazy_proxies(self.args)

        # Resolve kwargs
        if self.kwargs:
            self.kwargs = await resolve_lazy_proxies(self.kwargs)

    async def _execute_async(self) -> T:
        """Execute async function (direct await or via process pool)."""
        if self._use_process:
            return await self._execute_async_process()
        return await self._execute_async_direct()

    async def _execute_async_direct(self) -> T:
        """Execute async function via direct await (I/O-bound path)."""
        if not _is_async_callable(self.func):
            raise TypeError(f"Expected async function, got {type(self.func).__name__}")

        # Type checker now knows self.func is Callable[..., Awaitable[Any]]
        return await self.func(*self.args, **self.kwargs)

    async def _execute_async_process(self) -> T:
        """Execute async function via subprocess with asyncio.run() (CPU-bound path)."""
        if not _is_async_callable(self.func):
            raise TypeError(f"Expected async function, got {type(self.func).__name__}")

        from asynctasq.tasks.infrastructure.process_pool_manager import get_default_manager

        pool = get_default_manager().get_async_pool()
        loop = asyncio.get_running_loop()

        # Use module-level helper for ProcessPoolExecutor compatibility
        return await loop.run_in_executor(
            pool, _run_async_in_subprocess, self.func, self.args, self.kwargs
        )

    async def _execute_sync(self) -> T:
        """Execute sync function via thread pool or process pool."""
        loop = asyncio.get_running_loop()
        partial_func = functools.partial(self.func, *self.args, **self.kwargs)

        if self._use_process:
            return await self._execute_sync_process(partial_func, loop)
        return await self._execute_sync_thread(partial_func, loop)

    async def _execute_sync_thread(
        self, func: Callable[[], T], loop: asyncio.AbstractEventLoop
    ) -> T:
        """Execute sync function via ThreadPoolExecutor (I/O-bound path)."""
        return await loop.run_in_executor(None, func)

    async def _execute_sync_process(
        self, func: Callable[[], T], loop: asyncio.AbstractEventLoop
    ) -> T:
        """Execute sync function via ProcessPoolExecutor (CPU-bound path)."""
        from asynctasq.tasks.infrastructure.process_pool_manager import get_default_manager

        pool = get_default_manager().get_sync_pool()
        return await loop.run_in_executor(pool, func)


class TaskFunctionWrapper[T]:
    """Wrapper that makes function-based tasks behave like class-based tasks.

    When called, creates a FunctionTask instance that can be configured via
    method chaining (.on_queue(), .delay(), .retry_after()) before calling
    .dispatch() with NO arguments.

    The API is consistent with class-based tasks:
    - Call the function with its arguments to create a task instance
    - Configure the instance using method chaining (optional)
    - Call .dispatch() with NO arguments to queue the task
    """

    def __init__(self, func: Callable[..., T]) -> None:
        """Initialize wrapper with function and its task configuration.

        Args:
            func: The wrapped function with _task_* attributes
        """
        self._func = func
        # Cache task configuration to avoid repeated attribute lookups
        self._task_config = {
            "queue": getattr(func, "_task_queue", "default"),
            "max_attempts": getattr(func, "_task_max_attempts", 3),
            "retry_delay": getattr(func, "_task_retry_delay", 60),
            "timeout": getattr(func, "_task_timeout", None),
            "driver": getattr(func, "_task_driver", None),
            "process": getattr(func, "_task_process", False),
        }

        # Copy function attributes for introspection (includes __name__, __doc__, etc.)
        functools.update_wrapper(self, func)
        # Keep reference to original for debugging
        self.__wrapped__ = func

    def _create_task_instance(self, *args: Any, **kwargs: Any) -> FunctionTask[T]:
        """Create FunctionTask instance with cached configuration.

        Args:
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            FunctionTask instance ready for dispatch or configuration
        """
        return FunctionTask(
            self._func,
            *args,
            use_process=self._task_config["process"],
            **kwargs,
        )

    def __call__(self, *args: Any, **kwargs: Any) -> FunctionTask[T]:
        """Create task instance for configuration chaining (like class-based tasks).

        This enables the pattern: task(args).on_queue("name").dispatch()

        Args:
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            FunctionTask instance for method chaining

        Example:
            ```python
            @task
            async def my_task(x: int) -> int:
                return x * 2

            # Create instance, configure, then dispatch
            task_id = await my_task(x=5).on_queue("custom").dispatch()
            ```
        """
        return self._create_task_instance(*args, **kwargs)

    def __repr__(self) -> str:
        """Return helpful representation showing it's a task wrapper."""
        return f"<TaskFunction {self._func.__module__}.{self._func.__qualname__}>"

    def __str__(self) -> str:
        """Return string representation."""
        return f"TaskFunction({self._func.__name__})"


class TaskFunction[T](Protocol):
    """Protocol for @task decorated function.

    Function-based tasks are called to create task instances, which are then
    dispatched using the standard BaseTask.dispatch() method. This makes the
    API consistent with class-based tasks.
    """

    __name__: str
    __doc__: str | None
    __module__: str
    __qualname__: str
    __annotations__: dict[str, Any]

    def __call__(self, *args: Any, **kwargs: Any) -> FunctionTask[T]:
        """Create task instance for configuration chaining.

        Returns:
            FunctionTask instance for method chaining
        """
        ...


@overload
def task[T](_func: Callable[..., T], /) -> TaskFunction[T]:
    """@task without arguments."""
    ...


@overload
def task[T](
    _func: None = None,
    /,
    *,
    queue: str = "default",
    max_attempts: int = 3,
    retry_delay: int = 60,
    timeout: int | None = None,
    visibility_timeout: int = 3600,
    driver: str | BaseDriver | None = None,
    process: bool = False,
) -> Callable[[Callable[..., T]], TaskFunction[T]]:
    """@task with keyword arguments."""
    ...


def task[T](
    _func: Callable[..., T] | None = None,
    /,
    *,
    queue: str = "default",
    max_attempts: int = 3,
    retry_delay: int = 60,
    timeout: int | None = None,
    visibility_timeout: int = 3600,
    driver: str | BaseDriver | None = None,
    process: bool = False,
) -> TaskFunction[T] | Callable[[Callable[..., T]], TaskFunction[T]]:
    """Decorator to mark function as task.

    The decorated function becomes callable and returns a FunctionTask instance
    that can be configured via method chaining before dispatch.

    Args:
        queue: Queue name (default: "default")
        max_attempts: Max attempt count (default: 3)
        retry_delay: Retry delay in seconds (default: 60)
        timeout: Task timeout in seconds (default: None)
        visibility_timeout: Visibility timeout for crash recovery in seconds (default: 3600)
        driver: Driver override (default: None)
        process: Use process pool for CPU-bound work (default: False)

    Returns:
        Decorated function that creates FunctionTask instances when called.
        Call the function with args, then call .dispatch() with NO arguments.

    Example:
        ```python
        @task
        async def process_data(data: str) -> str:
            return data.upper()

        # Dispatch - note that dispatch() takes NO arguments
        task_id = await process_data("hello").dispatch()

        # With method chaining
        task_id = await process_data("hello").delay(60).dispatch()

        @task(queue="emails", process=True)
        def heavy_computation(x: int) -> int:
            return sum(range(x))

        # dispatch() never takes arguments - configure via chaining
        task_id = await heavy_computation(1000).on_queue("cpu").dispatch()
        ```
    """

    def decorator(func: Callable[..., T]) -> TaskFunction[T]:
        """Apply task configuration to function and wrap it."""
        # Store task configuration on function as attributes
        # This allows FunctionTask to read config during __init__
        func._task_queue = queue  # type: ignore[attr-defined]
        func._task_max_attempts = max_attempts  # type: ignore[attr-defined]
        func._task_retry_delay = retry_delay  # type: ignore[attr-defined]
        func._task_timeout = timeout  # type: ignore[attr-defined]
        func._task_visibility_timeout = visibility_timeout  # type: ignore[attr-defined]
        func._task_driver = driver  # type: ignore[attr-defined]
        func._task_process = process  # type: ignore[attr-defined]
        func._is_task = True  # type: ignore[attr-defined]

        # Wrap function with TaskFunctionWrapper for consistent API
        return TaskFunctionWrapper(func)  # type: ignore[return-value]

    # Support both @task and @task()
    if callable(_func):
        # Being used as @task (without parentheses)
        return decorator(_func)
    else:
        # Being used as @task(...) (with arguments)
        return decorator
