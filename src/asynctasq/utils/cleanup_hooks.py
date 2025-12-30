"""Asyncio event loop cleanup hooks - atexit for asyncio.

This module provides functionality to register cleanup callbacks that run when
an asyncio event loop closes, similar to how atexit works for process termination.

Inspired by asyncio-atexit (https://github.com/minrk/asyncio-atexit) but
tailored specifically for AsyncTasQ's cleanup needs.

Best Practices Applied (2025):
- Uses asyncio.get_running_loop() instead of deprecated get_event_loop()
- Proper async/sync callback handling with graceful degradation
- WeakKeyDictionary prevents memory leaks from loop references
- Comprehensive error handling prevents callback failures from cascading
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import inspect
import logging
from typing import Any
from weakref import WeakKeyDictionary

logger = logging.getLogger(__name__)

# Registry of cleanup callbacks per event loop
_registry: WeakKeyDictionary[asyncio.AbstractEventLoop, _RegistryEntry] = WeakKeyDictionary()


class _RegistryEntry:
    """Manages cleanup callbacks for a single event loop."""

    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop
        self.callbacks: list[Callable[[], Any]] = []
        self._original_close: Callable[[], None] | None = None
        self._patched = False

    def add_callback(self, callback: Callable[[], Any]) -> None:
        """Add a cleanup callback."""
        if callback not in self.callbacks:
            self.callbacks.append(callback)

    def remove_callback(self, callback: Callable[[], Any]) -> None:
        """Remove a cleanup callback."""
        while callback in self.callbacks:
            self.callbacks.remove(callback)

    def patch_loop_close(self) -> None:
        """Patch the event loop's close method to run cleanup callbacks."""
        if self._patched:
            return

        # Store the original close method
        self._original_close = self.loop.close

        # Create a new close method that runs cleanup first
        def close_with_cleanup():
            """Close the loop after running cleanup callbacks."""
            try:
                # Run cleanup callbacks synchronously
                self._run_cleanup_sync()
            except Exception as e:
                logger.exception(f"Error during asyncio cleanup: {e}")
            finally:
                # Call the original close method
                if self._original_close:
                    self._original_close()

        # Replace the loop's close method
        self.loop.close = close_with_cleanup  # type: ignore
        self._patched = True

    def _run_cleanup_sync(self) -> None:
        """Run cleanup callbacks synchronously.

        This is called when the loop is being closed, so we can't use
        await or schedule new tasks. We need to handle both sync and
        async callbacks appropriately.

        Best Practice (2025):
            - Callbacks run in registration order for predictable cleanup sequence
            - Async callbacks use run_until_complete if loop is still open
            - Graceful degradation: logs warning if async callback can't run
            - Error isolation: one failing callback doesn't prevent others
        """
        if not self.callbacks:
            return

        # Make a copy to avoid modification during iteration
        callbacks = self.callbacks.copy()

        for callback in callbacks:
            callback_name = getattr(callback, "__name__", str(callback))
            try:
                if inspect.iscoroutinefunction(callback):
                    # For async callbacks, we need to run them with run_until_complete
                    # if the loop is not already closed
                    if not self.loop.is_closed() and not self.loop.is_running():
                        # Safe to run async callback
                        self.loop.run_until_complete(callback())
                    else:
                        # Cannot run async callback - loop is closed or running
                        loop_state = "closed" if self.loop.is_closed() else "running"
                        logger.warning(
                            f"Cannot run async cleanup callback '{callback_name}' "
                            f"- loop is {loop_state}. Consider running cleanup earlier."
                        )
                else:
                    # Sync callback - just call it directly
                    callback()
            except asyncio.CancelledError:
                # Task was cancelled during cleanup - this is expected during shutdown
                logger.debug(
                    f"Cleanup callback '{callback_name}' was cancelled (expected during shutdown)"
                )
            except Exception as e:
                # Don't let one failing callback prevent others from running
                # Log with full traceback for debugging
                logger.exception(f"Error in cleanup callback '{callback_name}': {e}")


def register(callback: Callable[[], Any], *, loop: asyncio.AbstractEventLoop | None = None) -> None:
    """Register a cleanup callback to run when the event loop closes.

    This is similar to atexit.register but for asyncio event loops. The callback
    will be called when the event loop's close() method is invoked.

    Args:
        callback: A callable (sync or async) to execute during loop cleanup.
                 Async callbacks will be awaited if the loop is still running.
        loop: The event loop to attach to. If None, uses the running loop
              (preferred) or falls back to get_event_loop() for compatibility.

    Example:
        >>> async def cleanup():
        ...     await some_async_cleanup()
        >>> from asynctasq.utils import cleanup_hooks
        >>> cleanup_hooks.register(cleanup)

    Best Practices (2025):
        - The callback receives no arguments
        - Multiple callbacks can be registered
        - Callbacks execute in registration order (FIFO)
        - Exceptions in callbacks don't prevent others from running
        - Uses get_running_loop() (preferred) over deprecated get_event_loop()

    Note:
        If no event loop exists, the callback cannot be registered.
        Create/start an event loop before registering cleanup hooks.
    """
    if loop is None:
        try:
            # Try to get the running loop first (modern best practice)
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop - fall back to get_event_loop() for compatibility
            # Note: get_event_loop() is deprecated but still needed for some cases
            try:
                loop = asyncio.get_event_loop_policy().get_event_loop()
            except RuntimeError:
                # No event loop available at all
                logger.warning(
                    "Cannot register cleanup callback - no event loop available. "
                    "Create an event loop first or pass it explicitly. "
                    "Use asyncio.run() or asyncio.Runner for automatic loop management."
                )
                return

    # Get or create the registry entry for this loop
    entry = _registry.get(loop)
    if entry is None:
        entry = _RegistryEntry(loop)
        _registry[loop] = entry
        # Patch the loop's close method to run cleanup
        entry.patch_loop_close()

    # Add the callback to the registry
    entry.add_callback(callback)
    callback_name = getattr(callback, "__name__", str(callback))
    logger.debug(
        f"Registered cleanup callback '{callback_name}' for event loop {id(loop)} "
        f"({len(entry.callbacks)} total callbacks)"
    )


def unregister(
    callback: Callable[[], Any], *, loop: asyncio.AbstractEventLoop | None = None
) -> None:
    """Unregister a cleanup callback.

    Args:
        callback: The callback to remove
        loop: The event loop to remove from. If None, uses the running loop
              or current event loop policy's loop.
    """
    if loop is None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                return

    entry = _registry.get(loop)
    if entry is not None:
        entry.remove_callback(callback)
        callback_name = getattr(callback, "__name__", str(callback))
        logger.debug(f"Unregistered cleanup callback {callback_name} from event loop {id(loop)}")


def _get_registry_entry(loop: asyncio.AbstractEventLoop | None = None) -> _RegistryEntry | None:
    """Get the registry entry for a loop (internal use)."""
    if loop is None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return None
    return _registry.get(loop)
