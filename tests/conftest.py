"""Pytest configuration for project tests.

Sets uvloop as the global event loop policy so tests run with uvloop.
This must be import-safe and not assume uvloop is available at runtime.
"""

from __future__ import annotations

try:
    import asyncio

    import uvloop

    # Set uvloop as the default event loop policy for the test process.
    # Note: asyncio.set_event_loop_policy is deprecated in Python 3.14+, but
    # tests here target supported versions where this is acceptable.
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except Exception:
    # If uvloop is not installed or setting the policy fails, proceed with
    # the default asyncio policy. Tests that rely on uvloop should ensure
    # uvloop is available in the test environment.
    pass
