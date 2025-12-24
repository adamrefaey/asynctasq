"""Utilities for running coroutines with automatic event loop detection.

Provides a single `run()` helper that automatically detects and uses the
running event loop, or creates a new uvloop-based loop if none is running.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


async def _cleanup_asynctasq():
    """Cleanup AsyncTasQ resources if initialized."""
    try:
        from asynctasq.core.dispatcher import cleanup

        await cleanup()
    except TimeoutError:
        logger.warning("AsyncTasQ cleanup timed out")
    except Exception:
        # Ignore cleanup errors
        pass

    # Cleanup user-supplied SQLAlchemy engine
    try:
        from sqlalchemy.ext.asyncio import AsyncEngine

        from asynctasq.config import Config

        config = Config.get()
        if config.sqlalchemy_engine and isinstance(config.sqlalchemy_engine, AsyncEngine):
            try:
                await config.sqlalchemy_engine.dispose()
            except Exception:
                pass
    except ImportError:
        pass
    except Exception:
        pass


def run(coro: Any):
    """Run coroutine using a new event loop.

    Creates a new event loop (uvloop if available, asyncio otherwise) and runs
    the coroutine to completion. This is similar to asyncio.run() but with
    automatic uvloop support and AsyncTasQ cleanup.

    Args:
        coro: The coroutine to run

    Returns:
        The result of the coroutine

    Raises:
        RuntimeError: If called from within a running event loop

    Note:
        - This function creates a NEW event loop and cannot be called from
          within an existing event loop
        - If you're already in an async context (FastAPI, Jupyter, etc.),
          use 'await' directly instead
        - For running event loops, use asynctasq.init() to register cleanup
          hooks automatically

    Example:
        >>> from asynctasq.utils.loop import run
        >>> async def main():
        ...     await some_async_task()
        >>> run(main())
    """
    try:
        # Check if there's already a running event loop
        asyncio.get_running_loop()
        # If we're here, a loop is already running - cannot use run()
        raise RuntimeError(
            "asynctasq.utils.loop.run() cannot be called from a running event loop. "
            "Use 'await' directly instead. For automatic cleanup in running loops, "
            "call asynctasq.init() to register cleanup hooks."
        )
    except RuntimeError as e:
        # Check if the error is "no running loop" vs "cannot call run()"
        if "cannot be called" in str(e):
            raise
        # No event loop is running, proceed to create one

    # Create a new event loop
    # Try to use uvloop for best performance, fall back to asyncio if unavailable
    try:
        import uvloop

        loop = uvloop.new_event_loop()
        logger.debug("Using uvloop event loop")
    except ImportError:
        loop = asyncio.new_event_loop()
        logger.debug("Using asyncio event loop (uvloop not available)")

    asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(coro)
    finally:
        try:
            # Cleanup AsyncTasQ resources before shutting down asyncgens
            loop.run_until_complete(_cleanup_asynctasq())
        except Exception:
            pass
        try:
            # Shutdown async generators
            loop.run_until_complete(loop.shutdown_asyncgens())
        except Exception:
            pass
        try:
            # Shutdown default executor
            loop.run_until_complete(loop.shutdown_default_executor())
        except Exception:
            pass
        finally:
            # Close the loop
            loop.close()
            # Reset the event loop to None
            asyncio.set_event_loop(None)
