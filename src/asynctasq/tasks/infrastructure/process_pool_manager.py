"""Process pool management for CPU-bound task execution.

Provides thread-safe process pool managers with support for both synchronous
and asynchronous workloads. Designed for multiprocessing environments where
each worker process maintains isolated state and resources.

Key features:
- Separate pools for sync and async tasks with warm event loops
- Automatic resource cleanup and lifecycle management
- Thread-safe operations with proper locking
- Context manager support for RAII pattern
- Configurable worker limits and task recycling
- Process-local state management for multiprocessing safety
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
import logging
import multiprocessing.context
import os
import threading
import types
from typing import Any, Final, Literal, Self, TypedDict

logger = logging.getLogger(__name__)


class PoolStats(TypedDict):
    """Type definition for pool statistics."""

    status: Literal["initialized", "not_initialized"]
    pool_size: int
    max_tasks_per_child: int


ProcessPoolStats = dict[Literal["sync", "async"], PoolStats]


# Global variables for warm event loop (set by process initializer)
# These are process-local by design - each subprocess gets its own event loop
_process_loop: asyncio.AbstractEventLoop | None = None
_loop_thread: threading.Thread | None = None

# Metrics: Track fallback usage for observability (process-local)
_fallback_count = 0
_fallback_lock = threading.Lock()

# Default max_tasks_per_child to prevent memory leaks (best practice from research)
DEFAULT_MAX_TASKS_PER_CHILD: Final = 100


def _setup_subprocess_io() -> None:
    """Configure subprocess stdout/stderr to be unbuffered.

    Ensures print() statements and logging output from subprocesses
    appear immediately in the parent process terminal. This is especially
    important on macOS/Windows where 'spawn' context creates fresh processes.

    Called by ProcessPoolExecutor as the worker initializer function.
    """
    import sys

    # Force unbuffered output for immediate visibility
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(line_buffering=True)  # type: ignore[attr-defined]


def init_warm_event_loop() -> None:
    """Initialize persistent event loop in subprocess.

    Called by ProcessPoolExecutor as the worker initializer function.
    Creates a dedicated event loop running in a background daemon thread
    to avoid the overhead of creating new loops for each async task.

    This function is automatically invoked once per worker process during
    pool initialization. The event loop remains active for the lifetime
    of the worker process.

    Note:
        This function sets global variables that are process-local.
        Each worker process gets its own independent event loop.
    """
    global _process_loop, _loop_thread

    # Setup subprocess I/O for proper print() visibility
    _setup_subprocess_io()

    # Create new event loop for this process
    _process_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_process_loop)

    # Run event loop in background thread
    _loop_thread = threading.Thread(target=_process_loop.run_forever, daemon=True)
    _loop_thread.start()

    logger.debug(
        "Warm event loop initialized in subprocess",
        extra={
            "thread_id": _loop_thread.ident,
            "loop_id": id(_process_loop),
        },
    )


def get_warm_event_loop() -> asyncio.AbstractEventLoop | None:
    """Get the warm event loop for the current process.

    Returns:
        The active event loop if running in a worker process with
        warm event loop initialized, None otherwise.

    Note:
        Returns None if called outside a process pool worker or
        if the warm event loop was not properly initialized.
    """
    return _process_loop


def get_fallback_count() -> int:
    """Get the asyncio.run() fallback counter for this process.

    Returns:
        Number of times async tasks fell back to asyncio.run() instead
        of using the warm event loop. High counts may indicate missing
        proper pool initialization.

    Note:
        This is a process-local counter. Each worker maintains its own count.
    """
    with _fallback_lock:
        return _fallback_count


def increment_fallback_count() -> int:
    """Thread-safely increment and return the fallback counter.

    Returns:
        The new counter value after incrementing.

    Note:
        Used internally to track async task execution patterns.
        Higher values suggest suboptimal event loop usage.
    """
    global _fallback_count
    with _fallback_lock:
        _fallback_count += 1
        return _fallback_count


@dataclass(kw_only=True)
class ProcessPoolManager:
    """Instance-based manager for sync and async process pools with context manager support.

    Provides thread-safe process pool management with automatic cleanup.
    Use as async context manager for automatic resource management:

    Example:
        ```python
        async with ProcessPoolManager() as manager:
            pool = manager.get_sync_pool()
            result = await loop.run_in_executor(pool, sync_func)
        # Pools automatically shut down
        ```

    Or manage lifecycle manually:
        ```python
        manager = ProcessPoolManager()
        await manager.initialize()
        pool = manager.get_sync_pool()
        # ... use pools ...
        await manager.shutdown()
        ```
    """

    # Configuration parameters
    sync_max_workers: int | None = None
    async_max_workers: int | None = None
    sync_max_tasks_per_child: int | None = None
    async_max_tasks_per_child: int | None = None
    mp_context: multiprocessing.context.BaseContext | None = None

    # Runtime state (not part of init, created automatically)
    _sync_pool: ProcessPoolExecutor | None = field(default=None, init=False)
    _async_pool: ProcessPoolExecutor | None = field(default=None, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    _initialized: bool = field(default=False, init=False)

    async def __aenter__(self) -> Self:
        """Enter async context manager (initializes pools)."""
        await self.initialize()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Exit async context manager (shuts down pools)."""
        await self.shutdown()

    async def initialize(self) -> None:
        """Initialize both sync and async pools (idempotent)."""
        with self._lock:
            if self._initialized:
                logger.warning("Process pools already initialized, skipping initialization")
                return

            logger.info(
                "Initializing process pools",
                extra={
                    "sync_workers": self.sync_max_workers or self._get_cpu_count(),
                    "async_workers": self.async_max_workers or self._get_cpu_count(),
                    "sync_max_tasks_per_child": self.sync_max_tasks_per_child,
                    "async_max_tasks_per_child": self.async_max_tasks_per_child,
                },
            )

            self._sync_pool = self._create_pool(
                pool_type="sync",
                max_workers=self.sync_max_workers,
                max_tasks_per_child=self.sync_max_tasks_per_child or DEFAULT_MAX_TASKS_PER_CHILD,
                mp_context=self.mp_context,
                initializer=_setup_subprocess_io,
                initargs=(),
            )

            self._async_pool = self._create_pool(
                pool_type="async",
                max_workers=self.async_max_workers,
                max_tasks_per_child=self.async_max_tasks_per_child or DEFAULT_MAX_TASKS_PER_CHILD,
                mp_context=self.mp_context,
                initializer=init_warm_event_loop,
                initargs=(),
            )

            self._initialized = True
            logger.info("Process pools initialized successfully")

    def get_sync_pool(self) -> ProcessPoolExecutor:
        """Get sync process pool (auto-initializes if needed).

        Returns:
            Sync ProcessPoolExecutor

        Raises:
            RuntimeError: If pool initialization fails
        """
        with self._lock:
            if self._sync_pool is None:
                logger.warning("Auto-initializing sync pool (prefer explicit initialize())")
                self._sync_pool = self._create_pool(
                    pool_type="sync",
                    max_workers=self.sync_max_workers,
                    max_tasks_per_child=self.sync_max_tasks_per_child
                    or DEFAULT_MAX_TASKS_PER_CHILD,
                    mp_context=self.mp_context,
                    initializer=_setup_subprocess_io,
                    initargs=(),
                )
                self._initialized = True
            return self._sync_pool

    def get_async_pool(self) -> ProcessPoolExecutor:
        """Get async process pool (auto-initializes if needed).

        Returns:
            Async ProcessPoolExecutor with warm event loop

        Raises:
            RuntimeError: If pool initialization fails
        """
        with self._lock:
            if self._async_pool is None:
                logger.warning("Auto-initializing async pool (prefer explicit initialize())")
                self._async_pool = self._create_pool(
                    pool_type="async",
                    max_workers=self.async_max_workers,
                    max_tasks_per_child=self.async_max_tasks_per_child
                    or DEFAULT_MAX_TASKS_PER_CHILD,
                    mp_context=self.mp_context,
                    initializer=init_warm_event_loop,
                    initargs=(),
                )
                self._initialized = True
            return self._async_pool

    def _create_pool(
        self,
        pool_type: Literal["sync", "async"],
        max_workers: int | None,
        max_tasks_per_child: int,
        mp_context: multiprocessing.context.BaseContext | None,
        initializer: Callable[..., Any] | None,
        initargs: tuple[Any, ...],
    ) -> ProcessPoolExecutor:
        """Create process pool with given configuration.

        Args:
            pool_type: "sync" or "async"
            max_workers: Max workers (None = CPU count)
            max_tasks_per_child: Tasks per worker before restart
            mp_context: Multiprocessing context
            initializer: Callable to run on worker startup
            initargs: Arguments for initializer

        Returns:
            Configured ProcessPoolExecutor

        Raises:
            ValueError: If max_workers is <= 0
            TypeError: If max_workers is not an integer
        """
        # Determine actual max_workers (None defaults to CPU count)
        actual_max_workers = max_workers if max_workers is not None else self._get_cpu_count()

        # Validation happens in ProcessPoolExecutor constructor
        # It will raise ValueError if max_workers <= 0 or TypeError if not int

        logger.info(
            f"{pool_type.capitalize()} process pool created",
            extra={
                "pool_size": actual_max_workers,
                "max_tasks_per_child": max_tasks_per_child,
                "pool_type": pool_type,
            },
        )

        return ProcessPoolExecutor(
            max_workers=actual_max_workers,
            max_tasks_per_child=max_tasks_per_child,
            mp_context=mp_context,
            initializer=initializer,
            initargs=initargs,
        )

    def _get_cpu_count(self) -> int:
        """Get CPU count with fallback."""
        return getattr(os, "process_cpu_count", os.cpu_count)() or 4

    async def shutdown(self, wait: bool = True, cancel_futures: bool = False) -> None:
        """Shutdown both pools and free resources (thread-safe).

        Args:
            wait: Wait for pending tasks to complete
            cancel_futures: Cancel pending futures (Python 3.9+)
        """
        errors: list[Exception] = []

        with self._lock:
            if self._sync_pool is not None:
                logger.info(
                    "Shutting down sync process pool",
                    extra={"wait": wait, "cancel_futures": cancel_futures},
                )
                try:
                    self._sync_pool.shutdown(wait=wait, cancel_futures=cancel_futures)
                except Exception as e:
                    logger.exception("Error during sync process pool shutdown")
                    errors.append(e)
                finally:
                    self._sync_pool = None
                    logger.info("Sync process pool reference cleared")

            if self._async_pool is not None:
                logger.info(
                    "Shutting down async process pool",
                    extra={"wait": wait, "cancel_futures": cancel_futures},
                )
                try:
                    self._async_pool.shutdown(wait=wait, cancel_futures=cancel_futures)
                except Exception as e:
                    logger.exception("Error during async process pool shutdown")
                    errors.append(e)
                finally:
                    self._async_pool = None
                    logger.info("Async process pool reference cleared")

            self._initialized = False

            # Raise collected errors if any occurred
            if errors:
                if len(errors) == 1:
                    raise errors[0]
                # Python 3.11+ ExceptionGroup for multiple errors
                raise ExceptionGroup("Multiple errors during pool shutdown", errors)

    def is_initialized(self) -> bool:
        """Check if pools are initialized.

        Returns True if either sync or async pool exists, regardless of whether
        initialize() was called explicitly or pools were auto-created lazily.
        """
        with self._lock:
            return self._sync_pool is not None or self._async_pool is not None

    def get_stats(self) -> ProcessPoolStats:
        """Get pool statistics.

        Returns:
            Dict with sync/async pool status and configuration
        """
        with self._lock:
            # Get actual pool sizes (resolve None to CPU count)
            sync_pool_size = (
                self.sync_max_workers
                if self.sync_max_workers is not None
                else self._get_cpu_count()
            )
            async_pool_size = (
                self.async_max_workers
                if self.async_max_workers is not None
                else self._get_cpu_count()
            )

            sync_status: Literal["initialized", "not_initialized"] = (
                "initialized" if self._sync_pool is not None else "not_initialized"
            )
            async_status: Literal["initialized", "not_initialized"] = (
                "initialized" if self._async_pool is not None else "not_initialized"
            )

            return {
                "sync": PoolStats(
                    status=sync_status,
                    pool_size=sync_pool_size,
                    max_tasks_per_child=self.sync_max_tasks_per_child
                    or DEFAULT_MAX_TASKS_PER_CHILD,
                ),
                "async": PoolStats(
                    status=async_status,
                    pool_size=async_pool_size,
                    max_tasks_per_child=self.async_max_tasks_per_child
                    or DEFAULT_MAX_TASKS_PER_CHILD,
                ),
            }


# Process-local default instance for convenience
# Note: In multiprocessing, each process gets its own copy of this global
_default_manager: ProcessPoolManager | None = None
_default_manager_lock = threading.Lock()


def get_default_manager() -> ProcessPoolManager:
    """Get or create default ProcessPoolManager instance for this process.

    Important: In multiprocessing contexts, each process maintains its own
    default manager instance. This is usually the desired behavior for
    process pools, but be aware that managers are not shared between processes.

    For shared state across processes, consider explicit manager passing
    or process-safe alternatives like Manager() objects.

    Returns:
        Default ProcessPoolManager instance for this process
    """
    global _default_manager
    with _default_manager_lock:
        if _default_manager is None:
            _default_manager = ProcessPoolManager()
        return _default_manager


def set_default_manager(manager: ProcessPoolManager) -> None:
    """Set custom default manager for this process.

    Warning: In multiprocessing contexts, this only affects the current process.
    Other processes will maintain their own default managers.

    Args:
        manager: ProcessPoolManager instance to use as default in this process
    """
    global _default_manager
    with _default_manager_lock:
        _default_manager = manager
