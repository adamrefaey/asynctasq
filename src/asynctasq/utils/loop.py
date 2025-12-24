"""Utilities for running coroutines using uvloop where possible.

Provides a single `run()` helper for uvloop's optimized runner.
"""

from __future__ import annotations

import logging
from typing import Any

import uvloop

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
    """Run coroutine using a fresh uvloop event loop.

    This mirrors `asyncio.run()` semantics but ensures the event loop
    implementation is provided by `uvloop` regardless of global policy.
    """
    loop = uvloop.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        # Cleanup AsyncTasQ resources before shutting down asyncgens
        loop.run_until_complete(_cleanup_asynctasq())
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        finally:
            loop.close()
