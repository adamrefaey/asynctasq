"""Process pool management for CPU-bound task execution."""

from __future__ import annotations

import asyncio
from concurrent.futures import ProcessPoolExecutor
import logging
import os
import threading
from typing import Any

logger = logging.getLogger(__name__)

# Global variables for warm event loop (set by process initializer)
_process_loop: asyncio.AbstractEventLoop | None = None
_loop_thread: threading.Thread | None = None

# Metrics: Track fallback usage for observability
_fallback_count = 0
_fallback_lock = threading.Lock()

# Default max_tasks_per_child to prevent memory leaks (best practice from research)
DEFAULT_MAX_TASKS_PER_CHILD = 100


def init_warm_event_loop() -> None:
    """Initialize persistent event loop in subprocess (called by ProcessPoolExecutor initializer).

    Creates dedicated event loop in background thread to avoid overhead of creating new loop per task.
    """
    global _process_loop, _loop_thread

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
    """Get warm event loop for this process (None if not initialized or outside process pool)."""
    return _process_loop


def get_fallback_count() -> int:
    """Get asyncio.run() fallback count (high counts indicate missing warm_up() call)."""
    with _fallback_lock:
        return _fallback_count


def increment_fallback_count() -> int:
    """Increment and return fallback counter (thread-safe)."""
    global _fallback_count
    with _fallback_lock:
        _fallback_count += 1
        return _fallback_count


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

    def __init__(
        self,
        sync_max_workers: int | None = None,
        async_max_workers: int | None = None,
        sync_max_tasks_per_child: int | None = None,
        async_max_tasks_per_child: int | None = None,
        mp_context: Any | None = None,
    ) -> None:
        """Initialize process pool manager (pools created lazily or via initialize()).

        Args:
            sync_max_workers: Max workers for sync pool (default: CPU count)
            async_max_workers: Max workers for async pool (default: CPU count)
            sync_max_tasks_per_child: Tasks per worker before restart (default: 100)
            async_max_tasks_per_child: Tasks per worker before restart (default: 100)
            mp_context: Multiprocessing context (default: None, uses default context)
        """
        self._sync_max_workers = sync_max_workers
        self._async_max_workers = async_max_workers
        self._sync_max_tasks_per_child = sync_max_tasks_per_child or DEFAULT_MAX_TASKS_PER_CHILD
        self._async_max_tasks_per_child = async_max_tasks_per_child or DEFAULT_MAX_TASKS_PER_CHILD
        self._mp_context = mp_context

        self._sync_pool: ProcessPoolExecutor | None = None
        self._async_pool: ProcessPoolExecutor | None = None
        self._lock = threading.Lock()
        self._initialized = False

    async def __aenter__(self) -> ProcessPoolManager:
        """Enter async context manager (initializes pools)."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
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
                    "sync_workers": self._sync_max_workers or self._get_cpu_count(),
                    "async_workers": self._async_max_workers or self._get_cpu_count(),
                    "sync_max_tasks_per_child": self._sync_max_tasks_per_child,
                    "async_max_tasks_per_child": self._async_max_tasks_per_child,
                },
            )

            self._sync_pool = self._create_pool(
                pool_type="sync",
                max_workers=self._sync_max_workers,
                max_tasks_per_child=self._sync_max_tasks_per_child,
                mp_context=self._mp_context,
                initializer=None,
                initargs=(),
            )

            self._async_pool = self._create_pool(
                pool_type="async",
                max_workers=self._async_max_workers,
                max_tasks_per_child=self._async_max_tasks_per_child,
                mp_context=self._mp_context,
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
                    max_workers=self._sync_max_workers,
                    max_tasks_per_child=self._sync_max_tasks_per_child,
                    mp_context=self._mp_context,
                    initializer=None,
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
                    max_workers=self._async_max_workers,
                    max_tasks_per_child=self._async_max_tasks_per_child,
                    mp_context=self._mp_context,
                    initializer=init_warm_event_loop,
                    initargs=(),
                )
                self._initialized = True
            return self._async_pool

    def _create_pool(
        self,
        pool_type: str,
        max_workers: int | None,
        max_tasks_per_child: int,
        mp_context: Any | None,
        initializer: Any | None,
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
        with self._lock:
            if self._sync_pool is not None:
                logger.info(
                    "Shutting down sync process pool",
                    extra={"wait": wait, "cancel_futures": cancel_futures},
                )
                try:
                    self._sync_pool.shutdown(wait=wait, cancel_futures=cancel_futures)
                except Exception:
                    logger.exception("Error during sync process pool shutdown")
                    raise
                else:
                    self._sync_pool = None
                    logger.info("Sync process pool shutdown complete")

            if self._async_pool is not None:
                logger.info(
                    "Shutting down async process pool",
                    extra={"wait": wait, "cancel_futures": cancel_futures},
                )
                try:
                    self._async_pool.shutdown(wait=wait, cancel_futures=cancel_futures)
                except Exception:
                    logger.exception("Error during async process pool shutdown")
                    raise
                else:
                    self._async_pool = None
                    logger.info("Async process pool shutdown complete")

            self._initialized = False

    def is_initialized(self) -> bool:
        """Check if pools are initialized.

        Returns True if either sync or async pool exists, regardless of whether
        initialize() was called explicitly or pools were auto-created lazily.
        """
        with self._lock:
            return self._sync_pool is not None or self._async_pool is not None

    def get_stats(self) -> dict[str, Any]:
        """Get pool statistics.

        Returns:
            Dict with sync/async pool status and configuration
        """
        with self._lock:
            # Get actual pool sizes (resolve None to CPU count)
            sync_pool_size = (
                self._sync_max_workers
                if self._sync_max_workers is not None
                else self._get_cpu_count()
            )
            async_pool_size = (
                self._async_max_workers
                if self._async_max_workers is not None
                else self._get_cpu_count()
            )

            return {
                "sync": {
                    "status": "initialized" if self._sync_pool is not None else "not_initialized",
                    "pool_size": sync_pool_size,
                    "max_tasks_per_child": self._sync_max_tasks_per_child,
                },
                "async": {
                    "status": "initialized" if self._async_pool is not None else "not_initialized",
                    "pool_size": async_pool_size,
                    "max_tasks_per_child": self._async_max_tasks_per_child,
                },
            }


# Global default instance for convenience (can be replaced for dependency injection)
_default_manager: ProcessPoolManager | None = None
_default_manager_lock = threading.Lock()


def get_default_manager() -> ProcessPoolManager:
    """Get or create default global ProcessPoolManager instance.

    This provides a convenient global instance while still allowing
    dependency injection by setting the default manager explicitly.

    Returns:
        Default ProcessPoolManager instance
    """
    global _default_manager
    with _default_manager_lock:
        if _default_manager is None:
            _default_manager = ProcessPoolManager()
        return _default_manager


def set_default_manager(manager: ProcessPoolManager) -> None:
    """Set custom default manager (for dependency injection).

    Args:
        manager: ProcessPoolManager instance to use as default
    """
    global _default_manager
    with _default_manager_lock:
        _default_manager = manager
