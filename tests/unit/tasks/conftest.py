"""Shared test fixtures and utilities for task testing.

This module provides reusable utilities to eliminate code duplication
across test files, particularly for common task patterns.
"""

import asyncio

import pytest

from asynctasq.tasks import AsyncProcessTask, SyncProcessTask
from asynctasq.tasks.infrastructure.process_pool_manager import (
    ProcessPoolManager,
    get_default_manager,
    set_default_manager,
)


def factorial(n: int) -> int:
    """Pure factorial function (no task logic).

    Args:
        n: The number to compute factorial of

    Returns:
        Factorial of n
    """
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result


# Module-level task classes (needed for pickling in process pool)
class SharedSyncFactorialTask(SyncProcessTask[int]):
    """Shared test task that computes factorial in separate process."""

    n: int

    def execute(self) -> int:
        """Compute factorial of self.n."""
        return factorial(self.n)


class SharedAsyncFactorialTask(AsyncProcessTask[int]):
    """Shared test task that computes factorial asynchronously in separate process."""

    n: int

    async def execute(self) -> int:
        """Compute factorial of self.n asynchronously."""
        result = 1
        for i in range(1, self.n + 1):
            result *= i
            # Yield to event loop periodically
            if i % 1000 == 0:
                await asyncio.sleep(0)
        return result


@pytest.fixture(autouse=True, scope="function")
def reset_default_manager(event_loop):
    """Reset the default process pool manager before and after each test.

    This fixture ensures test isolation by:
    1. Shutting down any existing default manager before the test
    2. Creating a fresh default manager for the test
    3. Shutting down the manager after the test completes

    This prevents process pool state from bleeding between tests.
    """
    # Shutdown any existing default manager from previous tests
    try:
        manager = get_default_manager()
        if manager.is_initialized():
            event_loop.run_until_complete(manager.shutdown(wait=True, cancel_futures=True))
    except Exception:
        pass  # Ignore errors if manager doesn't exist or is already shut down

    # Create a fresh default manager for this test
    fresh_manager = ProcessPoolManager()
    set_default_manager(fresh_manager)

    # Run the test
    yield fresh_manager

    # Cleanup after test
    try:
        if fresh_manager.is_initialized():
            event_loop.run_until_complete(fresh_manager.shutdown(wait=True, cancel_futures=True))
    except Exception:
        pass  # Ignore cleanup errors
