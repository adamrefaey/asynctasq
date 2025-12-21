"""Pytest configuration to run tests with uvloop.

This conftest provides an `event_loop` fixture that creates a fresh uvloop
event loop for each test and performs proper cleanup. The project requires
uvloop to be available in the test environment.
"""

from __future__ import annotations

import asyncio

import pytest
import uvloop


@pytest.fixture
def event_loop():
    """Create and yield a uvloop-based event loop for each test.

    This mirrors the behaviour of `src/asynctasq/utils/loop.run()` which also
    creates fresh uvloop loops for subprocess runners.
    """
    loop = uvloop.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        yield loop
    finally:
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        finally:
            loop.close()
