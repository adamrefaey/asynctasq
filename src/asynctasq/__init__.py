"""AsyncTasQ - Modern async-first task queue for Python."""

import asyncio
import importlib.metadata
import logging

try:
    __version__ = importlib.metadata.version("asynctasq")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0"

from asynctasq.config import Config, ConfigOverrides
from asynctasq.core.dispatcher import cleanup
from asynctasq.monitoring import EventEmitter, EventRegistry

logger = logging.getLogger(__name__)

# Track whether we've registered cleanup hooks
_cleanup_registered = False


def _register_cleanup_hooks() -> None:
    """Register cleanup hooks for the current event loop.

    This function intelligently detects the event loop context and registers
    appropriate cleanup hooks:
    - For running event loops: Attaches cleanup to loop.close()
    - For non-running contexts: Defers registration until first async call

    This is called automatically by init() but can be called manually if needed.
    """
    global _cleanup_registered

    if _cleanup_registered:
        logger.debug("Cleanup hooks already registered")
        return

    try:
        # Try to get the running event loop
        loop = asyncio.get_running_loop()

        # We have a running loop - register cleanup hook to run when loop closes
        from asynctasq.utils.cleanup_hooks import register

        async def async_cleanup():
            """Async cleanup wrapper."""
            await cleanup()

        register(async_cleanup, loop=loop)
        logger.debug(f"Registered cleanup hook for running event loop {id(loop)}")
        _cleanup_registered = True
    except RuntimeError:
        # No running loop yet - will register when first async function is called
        # This is handled by ensure_cleanup_registered() below
        logger.debug("No running event loop - cleanup will be registered on first async call")
    except Exception as e:
        logger.debug(f"Could not register cleanup hooks: {e}")
        _cleanup_registered = True


async def ensure_cleanup_registered():
    """Ensure cleanup hooks are registered for the current running loop.

    This is called automatically when AsyncTasQ is used in async context
    to ensure cleanup hooks are attached to the event loop.
    """
    global _cleanup_registered

    if _cleanup_registered:
        return

    try:
        loop = asyncio.get_running_loop()
        from asynctasq.utils.cleanup_hooks import register

        async def async_cleanup():
            """Async cleanup wrapper."""
            await cleanup()

        register(async_cleanup, loop=loop)
        logger.debug(f"Registered cleanup hook for running event loop {id(loop)}")
        _cleanup_registered = True
    except Exception as e:
        logger.debug(f"Could not register cleanup hooks: {e}")


def init(
    config_overrides: ConfigOverrides | None = None,
    event_emitters: list[EventEmitter] | None = None,
) -> None:
    """Initialize AsyncTasQ with configuration and event emitters.

    This function must be called before using any AsyncTasQ functionality.
    It is recommended to call it as early as possible in your main script.

    This function automatically registers cleanup hooks that work with any
    event loop (asyncio, uvloop, or custom):
    - If called from within a running event loop, cleanup is attached to
      that loop's close() method
    - If called outside an event loop, atexit handlers are registered

    Args:
        config_overrides: Optional configuration overrides to customize
            AsyncTasQ behavior (driver settings, timeouts, etc.)
        event_emitters: Optional list of additional event emitters to register
            for monitoring and logging task/worker events

    Note:
        AsyncTasQ now works seamlessly with any event loop:
        - Use `asyncio.run()` or `asynctasq.utils.loop.run()` for scripts
        - Use `await` directly in FastAPI, Jupyter, or other async contexts
        - Cleanup happens automatically when the event loop closes

    Example:
        >>> import asynctasq
        >>> import asyncio
        >>>
        >>> # Initialize with Redis driver
        >>> asynctasq.init({
        ...     'driver': 'redis',
        ...     'redis_url': 'redis://localhost:6379',
        ... })
        >>>
        >>> # Works with any event loop
        >>> async def main():
        ...     # Your async code here
        ...     pass
        >>>
        >>> # Option 1: Use standard asyncio
        >>> asyncio.run(main())
        >>>
        >>> # Option 2: Use AsyncTasQ's runner (with uvloop support)
        >>> from asynctasq.utils.loop import run
        >>> run(main())
        >>>
        >>> # Option 3: In FastAPI/running loop - just await directly
        >>> # Cleanup happens automatically when the loop closes
    """
    # Apply configuration overrides
    if config_overrides:
        Config.set(**config_overrides)
    else:
        # Ensure config is initialized even without overrides
        Config.get()

    # Initialize default event emitters based on config
    EventRegistry.init()

    # Add any additional event emitters
    if event_emitters:
        for emitter in event_emitters:
            EventRegistry.add(emitter)

    # Register cleanup hooks for the current event loop context
    _register_cleanup_hooks()
