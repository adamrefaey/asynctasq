"""Tests for event types and data structures."""

from datetime import UTC, datetime

from pytest import fixture, main, mark

from asynctasq.monitoring import EventType, TaskEvent, WorkerEvent


@fixture
def sample_task_event() -> TaskEvent:
    """Create a sample task event for testing."""
    return TaskEvent(
        event_type=EventType.TASK_STARTED,
        task_id="test-task-123",
        task_name="TestTask",
        queue="default",
        worker_id="worker-abc123",
        timestamp=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        attempt=1,
    )


@fixture
def sample_worker_event() -> WorkerEvent:
    """Create a sample worker event for testing."""
    return WorkerEvent(
        event_type=EventType.WORKER_ONLINE,
        worker_id="worker-abc123",
        hostname="test-host",
        timestamp=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        queues=("default", "high-priority"),
        active=5,
        processed=100,
    )


@mark.unit
class TestEventType:
    """Test EventType enum."""

    def test_task_event_types_exist(self) -> None:
        """Test that all task event types are defined."""
        assert EventType.TASK_ENQUEUED == "task_enqueued"
        assert EventType.TASK_STARTED == "task_started"
        assert EventType.TASK_COMPLETED == "task_completed"
        assert EventType.TASK_FAILED == "task_failed"
        assert EventType.TASK_REENQUEUED == "task_reenqueued"
        assert EventType.TASK_CANCELLED == "task_cancelled"

    def test_worker_event_types_exist(self) -> None:
        """Test that all worker event types are defined."""
        assert EventType.WORKER_ONLINE == "worker_online"
        assert EventType.WORKER_HEARTBEAT == "worker_heartbeat"
        assert EventType.WORKER_OFFLINE == "worker_offline"


@mark.unit
class TestTaskEvent:
    """Test TaskEvent dataclass."""

    def test_task_event_creation(self, sample_task_event: TaskEvent) -> None:
        """Test that TaskEvent can be created with required fields."""
        assert sample_task_event.event_type == EventType.TASK_STARTED
        assert sample_task_event.task_id == "test-task-123"
        assert sample_task_event.task_name == "TestTask"
        assert sample_task_event.queue == "default"
        assert sample_task_event.worker_id == "worker-abc123"

    def test_task_event_is_frozen(self, sample_task_event: TaskEvent) -> None:
        """Test that TaskEvent is immutable."""
        try:
            sample_task_event.task_id = "new-id"  # type: ignore[misc]
            raise AssertionError("Should have raised FrozenInstanceError")
        except AttributeError:
            pass  # Expected

    def test_task_event_with_optional_fields(self) -> None:
        """Test TaskEvent with optional fields populated."""
        event = TaskEvent(
            event_type=EventType.TASK_COMPLETED,
            task_id="test-123",
            task_name="TestTask",
            queue="default",
            worker_id="worker-1",
            duration_ms=1500,
            result={"status": "success"},
        )
        assert event.duration_ms == 1500
        assert event.result == {"status": "success"}

    def test_task_event_with_error_fields(self) -> None:
        """Test TaskEvent with error fields populated."""
        event = TaskEvent(
            event_type=EventType.TASK_FAILED,
            task_id="test-123",
            task_name="TestTask",
            queue="default",
            worker_id="worker-1",
            error="ValueError: Invalid input",
            traceback="Traceback (most recent call last):\n...",
        )
        assert event.error == "ValueError: Invalid input"
        assert event.traceback is not None


@mark.unit
class TestWorkerEvent:
    """Test WorkerEvent dataclass."""

    def test_worker_event_creation(self, sample_worker_event: WorkerEvent) -> None:
        """Test that WorkerEvent can be created with required fields."""
        assert sample_worker_event.event_type == EventType.WORKER_ONLINE
        assert sample_worker_event.worker_id == "worker-abc123"
        assert sample_worker_event.hostname == "test-host"

    def test_worker_event_is_frozen(self, sample_worker_event: WorkerEvent) -> None:
        """Test that WorkerEvent is immutable."""
        try:
            sample_worker_event.worker_id = "new-id"  # type: ignore[misc]
            raise AssertionError("Should have raised FrozenInstanceError")
        except AttributeError:
            pass  # Expected

    def test_worker_event_defaults(self) -> None:
        """Test WorkerEvent default values."""
        event = WorkerEvent(
            event_type=EventType.WORKER_HEARTBEAT,
            worker_id="worker-1",
            hostname="host-1",
        )
        assert event.freq == 60.0
        assert event.active == 0
        assert event.processed == 0
        assert event.queues == ()
        assert event.sw_ident == "asynctasq"


if __name__ == "__main__":
    main([__file__, "-s", "-m", "unit"])
