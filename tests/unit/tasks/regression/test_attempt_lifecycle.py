"""Regression tests for task attempt lifecycle.

Testing Strategy:
- Verify attempt counter increments correctly through retry cycles
- Ensure re-enqueue happens when retries are available
- Confirm permanent failure handling when max attempts reached
- Validate serialization/deserialization preserves attempt state
"""

from datetime import UTC, datetime
from typing import Any

import pytest
from pytest import main, mark

from asynctasq.core.worker import Worker
from asynctasq.drivers.base_driver import BaseDriver
from asynctasq.serializers import MsgpackSerializer
from asynctasq.tasks.core.base_task import BaseTask
from asynctasq.tasks.services.executor import TaskExecutor
from asynctasq.tasks.services.serializer import TaskSerializer


class FailingTask(BaseTask[None]):
    """Test task that always fails with RuntimeError."""

    async def run(self) -> None:
        """Execute task (always raises RuntimeError)."""
        raise RuntimeError("failure")


class DummyDriver(BaseDriver):
    """Minimal in-memory driver for testing without external dependencies."""

    def __init__(self) -> None:
        """Initialize driver with empty queues."""
        self.enqueued: list[tuple[str, bytes, int, int, int]] = []
        self.processing: list[bytes] = []

    async def connect(self) -> None:
        """No-op connection for in-memory driver."""
        pass

    async def disconnect(self) -> None:
        """No-op disconnection for in-memory driver."""
        pass

    async def enqueue(
        self,
        queue_name: str,
        task_data: bytes,
        delay_seconds: int = 0,
        current_attempt: int = 0,
        visibility_timeout: int = 0,
    ) -> None:
        """Store serialized payloads for inspection."""
        self.enqueued.append(
            (queue_name, task_data, delay_seconds, current_attempt, visibility_timeout)
        )

    async def dequeue(self, queue_name: str, poll_seconds: int = 0) -> bytes | None:
        """Return nothing - test will directly call worker._process_task."""
        return None

    async def ack(self, queue_name: str, receipt_handle: bytes) -> None:
        """No-op acknowledgment."""
        pass

    async def nack(self, queue_name: str, receipt_handle: bytes) -> None:
        """No-op negative acknowledgment."""
        pass

    async def retry_task(self, task_id: str) -> bool:
        """Return False - retries not supported in test driver."""
        return False

    async def delete_task(self, task_id: str) -> bool:
        """Return False - deletion not supported in test driver."""
        return False

    async def get_tasks(
        self, status: str | None = None, queue: str | None = None, limit: int = 50, offset: int = 0
    ) -> tuple[list[tuple[bytes, str, str]], int]:
        """Return empty task list."""
        return ([], 0)

    async def get_task_by_id(self, task_id: str) -> bytes | None:
        """Return None - task lookup not supported."""
        return None

    async def get_running_tasks(self, limit: int = 50, offset: int = 0) -> list[tuple[bytes, str]]:
        """Return empty running tasks list."""
        return []

    async def get_worker_stats(self) -> list[dict[str, Any]]:
        """Return empty worker stats."""
        return []

    async def get_queue_stats(self, queue: str) -> dict[str, Any]:
        """Return empty queue stats."""
        return {}

    async def get_all_queue_names(self) -> list[str]:
        """Return empty queue names list."""
        return []

    async def get_global_stats(self) -> dict[str, int]:
        """Return empty global stats."""
        return {}

    async def get_queue_size(
        self, queue_name: str, include_delayed: bool, include_in_flight: bool
    ) -> int:
        """Return 0 for queue size."""
        return 0

    async def mark_failed(self, queue_name: str, receipt_handle: bytes) -> None:
        """No-op mark failed."""
        pass


@mark.unit
@mark.asyncio
async def test_attempt_lifecycle_reenqueue_and_final_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that attempt counter increments correctly through retry and final failure.

    This regression test validates:
    1. Task starts with attempt=0 after serialization
    2. Worker increments to attempt=1 when processing starts
    3. First failure re-enqueues task (attempt stays at 1)
    4. Second processing increments to attempt=2
    5. Final failure does not re-enqueue (permanent failure)
    """
    # Arrange
    driver = DummyDriver()
    serializer = MsgpackSerializer()
    worker = Worker(queue_driver=driver, queues=["default"], concurrency=1, serializer=serializer)
    task_serializer = TaskSerializer(serializer)

    # Create and serialize a fresh task (attempt should be 0)
    task = FailingTask()
    serialized = task_serializer.serialize(task)

    # Verify deserialization preserves attempt=0
    deserialized = await task_serializer.deserialize(serialized)
    assert deserialized.current_attempt == 0, "Fresh task should have attempt=0"

    # Simulate worker starting first attempt
    deserialized.mark_attempt_started()
    assert deserialized.current_attempt == 1, "First attempt should be 1"

    # Set up monkeypatches for first failure (should retry)
    start_time = datetime.now(UTC)
    task_data = serialized
    reenqueue_calls: list[tuple[str, bytes, int, int]] = []

    async def fake_enqueue(
        queue: str, data: bytes, delay_seconds: int = 0, current_attempt: int = 0
    ) -> None:
        reenqueue_calls.append((queue, data, delay_seconds, current_attempt))

    monkeypatch.setattr(driver, "enqueue", fake_enqueue)

    def should_retry_first(self: TaskExecutor, task: BaseTask, exc: Exception) -> bool:
        # Retry if attempt < 2 (i.e., retry once)
        return task.current_attempt < 2

    monkeypatch.setattr(TaskExecutor, "should_retry", should_retry_first)

    # Act - First failure (should re-enqueue)
    await worker._handle_task_failure(
        deserialized, RuntimeError("boom"), "default", start_time, task_data
    )

    # Assert - Task was re-enqueued once
    assert len(reenqueue_calls) == 1, "First failure should re-enqueue task"

    # Act - Simulate worker picking up the task again and starting second attempt
    deserialized.mark_attempt_started()
    assert deserialized.current_attempt == 2, "Second attempt should be 2"

    # Set up for permanent failure (no more retries)
    def should_retry_never(self: TaskExecutor, task: BaseTask, exc: Exception) -> bool:
        return False

    monkeypatch.setattr(TaskExecutor, "should_retry", should_retry_never)

    async def fake_mark_failed(queue: str, data: bytes) -> None:
        pass

    monkeypatch.setattr(driver, "mark_failed", fake_mark_failed)

    # Act - Second failure (should NOT re-enqueue, permanent failure)
    await worker._handle_task_failure(
        deserialized, RuntimeError("boom"), "default", start_time, task_data
    )

    # Assert - No additional re-enqueue happened (still only 1 from first failure)
    assert len(reenqueue_calls) == 1, "Permanent failure should not re-enqueue"


if __name__ == "__main__":
    main([__file__, "-s", "-m", "unit"])
