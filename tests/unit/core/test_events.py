"""Tests for the event emission system."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from pytest import fixture, main, mark

from asynctasq.config import Config
from asynctasq.core.events import (
    EventType,
    LoggingEventEmitter,
    RedisEventEmitter,
    TaskEvent,
    WorkerEvent,
)


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


@mark.unit
class TestLoggingEventEmitter:
    """Test LoggingEventEmitter."""

    @mark.asyncio
    async def test_emit_task_event_logs(self, sample_task_event: TaskEvent, caplog) -> None:
        """Test that task events are logged."""
        import logging

        with caplog.at_level(logging.INFO):
            emitter = LoggingEventEmitter()
            await emitter.emit(sample_task_event)

        assert "TaskEvent" in caplog.text
        assert "task_started" in caplog.text
        assert "test-task-123" in caplog.text

    @mark.asyncio
    async def test_emit_worker_event_logs(self, sample_worker_event: WorkerEvent, caplog) -> None:
        """Test that worker events are logged."""
        import logging

        with caplog.at_level(logging.INFO):
            emitter = LoggingEventEmitter()
            await emitter.emit(sample_worker_event)

        assert "WorkerEvent" in caplog.text
        assert "worker_online" in caplog.text
        assert "worker-abc123" in caplog.text

    @mark.asyncio
    async def test_close_is_noop(self) -> None:
        """Test that close does nothing."""
        emitter = LoggingEventEmitter()
        await emitter.close()  # Should not raise


@mark.unit
class TestRedisEventEmitter:
    """Test RedisEventEmitter."""

    def test_init_uses_config_events_redis_url(self) -> None:
        """Test that events_redis_url from config is used first."""
        mock_config = Config(
            events_redis_url="redis://events:6379",
            redis_url="redis://queue:6379",
            events_channel="custom:events",
        )

        with patch("asynctasq.core.events.Config.get", return_value=mock_config):
            emitter = RedisEventEmitter()

        assert emitter.redis_url == "redis://events:6379"
        assert emitter.channel == "custom:events"

    def test_init_falls_back_to_redis_url(self) -> None:
        """Test fallback to redis_url when events_redis_url is None."""
        mock_config = Config(
            events_redis_url=None,
            redis_url="redis://queue:6379",
            events_channel="asynctasq:events",
        )

        with patch("asynctasq.core.events.Config.get", return_value=mock_config):
            emitter = RedisEventEmitter()

        assert emitter.redis_url == "redis://queue:6379"

    def test_init_with_explicit_params_overrides_config(self) -> None:
        """Test that explicit parameters override config values."""
        mock_config = Config(
            events_redis_url="redis://events:6379",
            redis_url="redis://queue:6379",
            events_channel="config:events",
        )

        with patch("asynctasq.core.events.Config.get", return_value=mock_config):
            emitter = RedisEventEmitter(
                redis_url="redis://explicit:6379", channel="explicit:channel"
            )

        assert emitter.redis_url == "redis://explicit:6379"
        assert emitter.channel == "explicit:channel"

    @mark.asyncio
    async def test_emit_task_event_publishes_to_redis(self, sample_task_event: TaskEvent) -> None:
        """Test that task events are published to Redis."""
        mock_config = Config(
            events_redis_url="redis://localhost:6379",
            events_channel="test:events",
        )

        with patch("asynctasq.core.events.Config.get", return_value=mock_config):
            emitter = RedisEventEmitter()

        # Mock the Redis client
        mock_client = AsyncMock()
        emitter._client = mock_client

        await emitter.emit(sample_task_event)

        mock_client.publish.assert_called_once()
        call_args = mock_client.publish.call_args
        assert call_args[0][0] == "test:events"
        assert isinstance(call_args[0][1], bytes)  # msgpack serialized

    @mark.asyncio
    async def test_emit_worker_event_publishes_to_redis(
        self, sample_worker_event: WorkerEvent
    ) -> None:
        """Test that worker events are published to Redis."""
        mock_config = Config(
            events_redis_url="redis://localhost:6379",
            events_channel="test:events",
        )

        with patch("asynctasq.core.events.Config.get", return_value=mock_config):
            emitter = RedisEventEmitter()

        mock_client = AsyncMock()
        emitter._client = mock_client

        await emitter.emit(sample_worker_event)

        mock_client.publish.assert_called_once()

    @mark.asyncio
    async def test_emit_handles_publish_error_gracefully(
        self, sample_task_event: TaskEvent, caplog
    ) -> None:
        """Test that publish errors are caught and logged."""
        mock_config = Config(
            events_redis_url="redis://localhost:6379",
            events_channel="test:events",
        )

        with patch("asynctasq.core.events.Config.get", return_value=mock_config):
            emitter = RedisEventEmitter()

        mock_client = AsyncMock()
        mock_client.publish.side_effect = Exception("Connection failed")
        emitter._client = mock_client

        # Should not raise
        await emitter.emit(sample_task_event)

        assert "Failed to publish task event" in caplog.text

    @mark.asyncio
    async def test_close_closes_client(self) -> None:
        """Test that close properly closes the Redis client."""
        mock_config = Config(
            events_redis_url="redis://localhost:6379",
            events_channel="test:events",
        )

        with patch("asynctasq.core.events.Config.get", return_value=mock_config):
            emitter = RedisEventEmitter()

        mock_client = AsyncMock()
        emitter._client = mock_client

        await emitter.close()

        mock_client.aclose.assert_called_once()
        assert emitter._client is None

    @mark.asyncio
    async def test_close_without_client_is_safe(self) -> None:
        """Test that close works even if client was never connected."""
        mock_config = Config(
            events_redis_url="redis://localhost:6379",
            events_channel="test:events",
        )

        with patch("asynctasq.core.events.Config.get", return_value=mock_config):
            emitter = RedisEventEmitter()

        await emitter.close()  # Should not raise

    def test_serialize_event_converts_types(self, sample_task_event: TaskEvent) -> None:
        """Test that event serialization handles type conversions."""
        mock_config = Config(
            events_redis_url="redis://localhost:6379",
            events_channel="test:events",
        )

        with patch("asynctasq.core.events.Config.get", return_value=mock_config):
            emitter = RedisEventEmitter()

        result = emitter._serialize_event(sample_task_event)

        assert isinstance(result, bytes)
        # Verify it's valid msgpack by deserializing
        import msgpack

        data = msgpack.unpackb(result)
        assert data["event_type"] == "task_started"
        assert data["task_id"] == "test-task-123"
        assert isinstance(data["timestamp"], str)  # ISO format string

    def test_serialize_worker_event_converts_queues_tuple(
        self, sample_worker_event: WorkerEvent
    ) -> None:
        """Test that queues tuple is converted to list for msgpack."""
        mock_config = Config(
            events_redis_url="redis://localhost:6379",
            events_channel="test:events",
        )

        with patch("asynctasq.core.events.Config.get", return_value=mock_config):
            emitter = RedisEventEmitter()

        result = emitter._serialize_event(sample_worker_event)

        import msgpack

        data = msgpack.unpackb(result)
        assert isinstance(data["queues"], list)
        assert data["queues"] == ["default", "high-priority"]


@mark.unit
class TestEventsRedisUrlConfig:
    """Test the events_redis_url configuration fallback behavior."""

    def test_events_redis_url_takes_priority(self) -> None:
        """Test that events_redis_url is used over redis_url."""
        mock_config = Config(
            events_redis_url="redis://events-server:6379",
            redis_url="redis://queue-server:6379",
            events_channel="custom:channel",
        )

        with patch("asynctasq.core.events.Config.get", return_value=mock_config):
            emitter = RedisEventEmitter()

        assert emitter.redis_url == "redis://events-server:6379"

    def test_falls_back_to_redis_url_when_events_url_none(self) -> None:
        """Test fallback to redis_url when events_redis_url is None."""
        mock_config = Config(
            events_redis_url=None,
            redis_url="redis://queue-server:6379",
            events_channel="asynctasq:events",
        )

        with patch("asynctasq.core.events.Config.get", return_value=mock_config):
            emitter = RedisEventEmitter()

        assert emitter.redis_url == "redis://queue-server:6379"

    def test_explicit_param_overrides_all_config(self) -> None:
        """Test that explicit redis_url param overrides both config values."""
        mock_config = Config(
            events_redis_url="redis://events-server:6379",
            redis_url="redis://queue-server:6379",
            events_channel="config:channel",
        )

        with patch("asynctasq.core.events.Config.get", return_value=mock_config):
            emitter = RedisEventEmitter(redis_url="redis://param:6379")

        assert emitter.redis_url == "redis://param:6379"

    def test_events_channel_from_config(self) -> None:
        """Test that events_channel is read from config."""
        mock_config = Config(
            events_redis_url="redis://localhost:6379",
            events_channel="my-app:events",
        )

        with patch("asynctasq.core.events.Config.get", return_value=mock_config):
            emitter = RedisEventEmitter()

        assert emitter.channel == "my-app:events"

    def test_channel_param_overrides_config(self) -> None:
        """Test that explicit channel param overrides config."""
        mock_config = Config(
            events_redis_url="redis://localhost:6379",
            events_channel="config:channel",
        )

        with patch("asynctasq.core.events.Config.get", return_value=mock_config):
            emitter = RedisEventEmitter(channel="param:channel")

        assert emitter.channel == "param:channel"


if __name__ == "__main__":
    main([__file__, "-s", "-m", "unit"])
