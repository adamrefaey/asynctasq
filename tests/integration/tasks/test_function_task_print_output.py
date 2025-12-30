"""Test that print statements in @task decorated functions are visible."""

import sys

import pytest

from asynctasq.config import Config
from asynctasq.core.dispatcher import Dispatcher
from asynctasq.core.driver_factory import DriverFactory
from asynctasq.core.worker import Worker
from asynctasq.tasks import task


# Define tasks at module level for serializability
@task
async def print_async_task(message: str) -> str:
    """Async task that prints."""
    print(f"ASYNC PRINT: {message}")
    sys.stdout.flush()
    return f"async:{message}"


@task
def print_sync_task(message: str) -> str:
    """Sync task that prints."""
    print(f"SYNC PRINT: {message}")
    sys.stdout.flush()
    return f"sync:{message}"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_async_function_task_print_visible(capfd):
    """Verify print statements in async @task functions appear in stdout."""
    config = Config.get()
    driver = DriverFactory.create(config.driver, config)
    await driver.connect()

    try:
        # Clear queue
        while await driver.dequeue("default"):
            pass

        # Create dispatcher and worker
        dispatcher = Dispatcher(driver)
        worker = Worker(
            queue_driver=driver,
            queues=["default"],
            concurrency=1,
            max_tasks=1,
        )

        # Dispatch task
        await dispatcher.dispatch(print_async_task(message="Hello Async"))

        # Process with worker
        await worker.start()

        # Capture output
        captured = capfd.readouterr()

        # Verify print appeared
        assert "ASYNC PRINT: Hello Async" in captured.out

    finally:
        await driver.disconnect()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_sync_function_task_print_visible(capfd):
    """Verify print statements in sync @task functions appear in stdout."""
    config = Config.get()
    driver = DriverFactory.create(config.driver, config)
    await driver.connect()

    try:
        # Clear queue
        while await driver.dequeue("default"):
            pass

        # Create dispatcher and worker
        dispatcher = Dispatcher(driver)
        worker = Worker(
            queue_driver=driver,
            queues=["default"],
            concurrency=1,
            max_tasks=1,
        )

        # Dispatch task
        await dispatcher.dispatch(print_sync_task(message="Hello Sync"))

        # Process with worker
        await worker.start()

        # Capture output
        captured = capfd.readouterr()

        # Verify print appeared
        assert "SYNC PRINT: Hello Sync" in captured.out

    finally:
        await driver.disconnect()
