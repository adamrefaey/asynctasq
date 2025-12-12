"""Integration tests for FunctionTask with process execution and @task decorator."""

import asyncio
import hashlib
import os

import pytest
import pytest_asyncio

from asynctasq.core.dispatcher import Dispatcher
from asynctasq.drivers.redis_driver import RedisDriver
from asynctasq.serializers.msgpack_serializer import MsgpackSerializer
from asynctasq.tasks.infrastructure.process_pool_manager import ProcessPoolManager
from asynctasq.tasks.types.function_task import FunctionTask, task

# Test Redis connection
REDIS_URL = os.getenv("ASYNCTASQ_REDIS_URL", "redis://localhost:6379")


# ============================================================================
# Module-level functions for process pool testing (must be picklable)
# ============================================================================


def cpu_bound_factorial(n: int) -> int:
    """Compute factorial - CPU-bound work suitable for process pool."""
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result


def cpu_bound_hash(iterations: int) -> str:
    """Compute hash repeatedly - CPU-intensive work."""
    result = "0" * 64
    for _ in range(iterations):
        result = hashlib.sha256(result.encode()).hexdigest()
    return result


def simple_multiply(x: int, y: int) -> int:
    """Simple multiplication for testing args."""
    return x * y


def simple_add(a: int = 0, b: int = 0) -> int:
    """Simple addition for testing kwargs."""
    return a + b


async def async_cpu_bound(n: int) -> int:
    """Async function that does CPU-bound work."""
    # Simulate async CPU-bound work (sum of range)
    return sum(range(n))


async def async_io_bound(delay: float) -> str:
    """Async I/O-bound function."""
    await asyncio.sleep(delay)
    return f"completed after {delay}s"


# ============================================================================
# @task decorated functions for integration testing
# ============================================================================


@task(queue="test-function-task", process=True)
def task_factorial(n: int) -> int:
    """CPU-bound factorial task."""
    return cpu_bound_factorial(n)


@task(queue="test-function-task", process=True)
def task_hash(iterations: int) -> str:
    """CPU-bound hash task."""
    return cpu_bound_hash(iterations)


@task(queue="test-function-task", process=False)
async def task_async_io(delay: float) -> str:
    """Async I/O-bound task."""
    return await async_io_bound(delay)


@task(queue="test-function-task", process=True, timeout=10)
async def task_async_process(n: int) -> int:
    """Async function executed in process pool."""
    return await async_cpu_bound(n)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def manager() -> ProcessPoolManager:
    """Create ProcessPoolManager instance."""
    return ProcessPoolManager()


@pytest_asyncio.fixture
async def redis_driver(manager):
    """Create and connect Redis driver."""
    driver = RedisDriver(url=REDIS_URL)
    await driver.connect()

    # Clean test queue
    if driver.client:
        await driver.client.delete("asynctasq:queue:test-function-task")
        await driver.client.delete("asynctasq:queue:test-function-task:processing")
        await driver.client.delete("asynctasq:queue:test-function-task:delayed")

    yield driver

    # Cleanup
    if driver.client:
        await driver.client.delete("asynctasq:queue:test-function-task")
        await driver.client.delete("asynctasq:queue:test-function-task:processing")
        await driver.client.delete("asynctasq:queue:test-function-task:delayed")
    await driver.disconnect()


@pytest_asyncio.fixture
async def dispatcher(redis_driver):
    """Create dispatcher with Redis driver."""
    serializer = MsgpackSerializer()
    return Dispatcher(driver=redis_driver, serializer=serializer)


# ============================================================================
# Integration Tests: FunctionTask with process=True (sync functions)
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_function_task_sync_process_execution(manager):
    """Test sync function executed in process pool."""
    # Arrange
    await manager.initialize()
    task_instance = FunctionTask(cpu_bound_factorial, 5, use_process=True)

    # Act
    result = await task_instance.run()

    # Assert
    assert result == 120  # 5! = 120

    # Cleanup
    await manager.shutdown(wait=True)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_function_task_sync_process_with_kwargs(manager):
    """Test sync function in process pool with kwargs."""
    # Arrange
    await manager.initialize()
    task_instance = FunctionTask(simple_add, use_process=True, a=10, b=20)

    # Act
    result = await task_instance.run()

    # Assert
    assert result == 30

    # Cleanup
    await manager.shutdown(wait=True)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_function_task_sync_process_cpu_intensive(manager):
    """Test CPU-intensive work in process pool."""
    # Arrange
    await manager.initialize()
    task_instance = FunctionTask(cpu_bound_hash, 100, use_process=True)

    # Act
    result = await task_instance.run()

    # Assert
    assert isinstance(result, str)
    assert len(result) == 64  # SHA256 hex digest length

    # Cleanup
    await manager.shutdown(wait=True)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_function_task_sync_process_concurrent_execution(manager):
    """Test concurrent sync process execution."""
    # Arrange
    await manager.initialize()

    # Create multiple tasks
    tasks = [FunctionTask(cpu_bound_factorial, n, use_process=True) for n in [3, 4, 5, 6]]

    # Act - execute concurrently
    results = await asyncio.gather(*[task.run() for task in tasks])

    # Assert
    assert results == [6, 24, 120, 720]  # 3!, 4!, 5!, 6!

    # Cleanup
    await manager.shutdown(wait=True)


# ============================================================================
# Integration Tests: FunctionTask with process=True (async functions)
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_function_task_async_process_execution(manager):
    """Test async function executed in process pool."""
    # Arrange
    await manager.initialize()
    task_instance = FunctionTask(async_cpu_bound, 10, use_process=True)

    # Act
    result = await task_instance.run()

    # Assert
    assert result == 45  # sum(0..9)

    # Cleanup
    await manager.shutdown(wait=True)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_function_task_async_process_concurrent(manager):
    """Test concurrent async process execution."""
    # Arrange
    await manager.initialize()

    # Create multiple async tasks
    tasks = [FunctionTask(async_cpu_bound, n, use_process=True) for n in [5, 10, 15, 20]]

    # Act - execute concurrently
    results = await asyncio.gather(*[task.run() for task in tasks])

    # Assert
    assert results == [10, 45, 105, 190]  # sum(0..4), sum(0..9), etc.

    # Cleanup
    await manager.shutdown(wait=True)


# ============================================================================
# Integration Tests: FunctionTask with process=False (async direct)
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_function_task_async_direct_execution():
    """Test async function executed directly (I/O-bound path)."""
    # Arrange
    task_instance = FunctionTask(async_io_bound, 0.01, use_process=False)

    # Act
    result = await task_instance.run()

    # Assert
    assert result == "completed after 0.01s"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_function_task_async_direct_with_kwargs():
    """Test async function with kwargs executed directly."""

    # Arrange
    async def async_add(x: int, y: int) -> int:
        await asyncio.sleep(0.001)
        return x + y

    task_instance = FunctionTask(async_add, use_process=False, x=15, y=25)

    # Act
    result = await task_instance.run()

    # Assert
    assert result == 40


# ============================================================================
# Integration Tests: FunctionTask with process=False (sync thread pool)
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_function_task_sync_thread_execution():
    """Test sync function executed in thread pool (default)."""
    # Arrange
    task_instance = FunctionTask(simple_multiply, 7, 8, use_process=False)

    # Act
    result = await task_instance.run()

    # Assert
    assert result == 56


@pytest.mark.integration
@pytest.mark.asyncio
async def test_function_task_sync_thread_with_kwargs():
    """Test sync function in thread pool with kwargs."""
    # Arrange
    task_instance = FunctionTask(simple_add, use_process=False, a=100, b=200)

    # Act
    result = await task_instance.run()

    # Assert
    assert result == 300


# ============================================================================
# Integration Tests: Edge cases and error handling
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_function_task_process_pool_reuse(manager):
    """Test process pool can be reused across multiple tasks."""
    # Arrange
    await manager.initialize()

    # Act - run multiple tasks using same pool
    result1 = await FunctionTask(cpu_bound_factorial, 3, use_process=True).run()
    result2 = await FunctionTask(cpu_bound_factorial, 4, use_process=True).run()
    result3 = await FunctionTask(cpu_bound_factorial, 5, use_process=True).run()

    # Assert
    assert result1 == 6
    assert result2 == 24
    assert result3 == 120

    # Cleanup
    await manager.shutdown(wait=True)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_function_task_mixed_process_and_thread(manager):
    """Test mixing process and thread execution."""
    # Arrange
    await manager.initialize()

    # Act - run process and thread tasks
    process_result = await FunctionTask(cpu_bound_factorial, 5, use_process=True).run()
    thread_result = await FunctionTask(simple_multiply, 5, 6, use_process=False).run()

    # Assert
    assert process_result == 120
    assert thread_result == 30

    # Cleanup
    await manager.shutdown(wait=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
