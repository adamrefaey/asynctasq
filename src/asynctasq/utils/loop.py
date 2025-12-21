"""Utilities for running coroutines using uvloop where possible.

Provides a single `run()` helper for uvloop's optimized runner.
"""

from __future__ import annotations

import logging
from typing import Any

import uvloop

logger = logging.getLogger(__name__)


def run(coro: Any):
    """Run coroutine using a fresh uvloop event loop.

    This mirrors `asyncio.run()` semantics but ensures the event loop
    implementation is provided by `uvloop` regardless of global policy.
    """
    loop = uvloop.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        finally:
            loop.close()
