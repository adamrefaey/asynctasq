"""Pytest configuration to run tests with uvloop.

This conftest provides an `event_loop` fixture that creates a fresh uvloop
event loop for each test and performs proper cleanup. The project requires
uvloop to be available in the test environment.

It also provides an `ensure_migrations` fixture that automatically runs
database migrations for PostgreSQL and MySQL before any tests execute.
"""

from __future__ import annotations

import asyncio
import logging
import os

import pytest
import uvloop

logger = logging.getLogger(__name__)


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


@pytest.fixture(scope="session", autouse=True)
def ensure_migrations():
    """Ensure database migrations are run before any tests execute.

    This fixture automatically runs 'asynctasq migrate' for both PostgreSQL
    and MySQL databases. It runs once per test session and is automatically
    applied to all tests.

    The fixture checks if databases are available before attempting migration,
    so it gracefully skips if Docker services are not running.
    """
    import subprocess
    import sys

    # Only run migrations if we're in the asynctasq project root
    if not os.path.exists("src/asynctasq"):
        return

    logger.info("🚀 Running database migrations for test infrastructure...")

    # PostgreSQL migration
    try:
        result = subprocess.run(
            [sys.executable, "-m", "asynctasq", "migrate", "--driver", "postgres"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            logger.info("✅ PostgreSQL migration completed")
        else:
            # Log but don't fail - tests might not need postgres
            logger.warning(f"⚠️  PostgreSQL migration skipped or failed: {result.stderr}")
    except Exception as e:
        logger.warning(f"⚠️  PostgreSQL migration failed: {e}")

    # MySQL migration
    try:
        result = subprocess.run(
            [sys.executable, "-m", "asynctasq", "migrate", "--driver", "mysql"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            logger.info("✅ MySQL migration completed")
        else:
            # Log but don't fail - tests might not need mysql
            logger.warning(f"⚠️  MySQL migration skipped or failed: {result.stderr}")
    except Exception as e:
        logger.warning(f"⚠️  MySQL migration failed: {e}")

    logger.info("✅ Migration setup complete")
