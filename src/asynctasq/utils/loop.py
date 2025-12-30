"""Utilities for running coroutines with automatic event loop detection.

Provides a single `run()` helper that automatically detects and uses the
running event loop, or creates a new uvloop-based loop if none is running.

Best Practices Applied (2025):
- Uses asyncio.Runner with uvloop for Python 3.11+
- Proper shutdown sequence: asyncgens -> executor -> cleanup
- Graceful error handling during cleanup phases
- Uses asyncio.run() semantics with uvloop optimization
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
    """Run coroutine using a new event loop with uvloop optimization.

    Creates a new event loop (uvloop if available, asyncio otherwise) and runs
    the coroutine to completion. This follows asyncio.run() semantics with
    automatic uvloop support and proper cleanup sequence.

    Args:
        coro: The coroutine to run

    Returns:
        The result of the coroutine

    Raises:
        RuntimeError: If called from within a running event loop

    Best Practices (2025):
        - Uses asyncio.Runner with uvloop (Python 3.12+ min requirement)
        - Proper shutdown order: asyncgens → executor → cleanup → close
        - Graceful error handling at each cleanup phase
        - Matches asyncio.run() behavior with performance optimization

    Note:
        - This function creates a NEW event loop and cannot be called from
          within an existing event loop
        - If you're already in an async context (FastAPI, Jupyter, etc.),
          use 'await' directly instead
        - For running event loops, use asynctasq.init() to register cleanup
          hooks automatically
        - uvloop provides 2-4x performance improvement over standard asyncio

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

    # Use asyncio.Runner with uvloop for best performance
    # This is the modern recommended approach per 2025 best practices (Python 3.11+)
    # Since min supported version is 3.12, we always use Runner
    try:
        import uvloop

        # Use Runner with uvloop factory - combines best of both worlds
        with asyncio.Runner(loop_factory=uvloop.new_event_loop) as runner:
            logger.debug("Using asyncio.Runner with uvloop")
            try:
                return runner.run(coro)
            finally:
                # Runner handles asyncgens and executor shutdown automatically
                # We only need to cleanup AsyncTasQ resources
                try:
                    runner.run(_cleanup_asynctasq())
                except Exception as e:
                    logger.debug(f"AsyncTasQ cleanup completed with warnings: {e}")
    except ImportError:
        # uvloop not available, use standard Runner
        with asyncio.Runner() as runner:
            logger.debug("Using asyncio.Runner (uvloop not available)")
            try:
                return runner.run(coro)
            finally:
                try:
                    runner.run(_cleanup_asynctasq())
                except Exception as e:
                    logger.debug(f"AsyncTasQ cleanup completed with warnings: {e}")
