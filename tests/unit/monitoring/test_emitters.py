"""Tests for event emitters."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from pytest import fixture, main, mark, raises

from asynctasq.config import Config, EventsConfig, RedisConfig
from asynctasq.monitoring import (
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
            events=EventsConfig(
                redis_url="redis://events:6379",
                channel="custom:events",
            ),
            redis=RedisConfig(
                url="redis://queue:6379",
            ),
        )

        with patch("asynctasq.monitoring.emitters.Config.get", return_value=mock_config):
            emitter = RedisEventEmitter()

        assert emitter.redis_url == "redis://events:6379"
        assert emitter.channel == "custom:events"

    def test_init_falls_back_to_redis_url(self) -> None:
        """Test fallback to redis_url when events_redis_url is None."""
        mock_config = Config(
            events=EventsConfig(
                redis_url=None,
                channel="asynctasq:events",
            ),
            redis=RedisConfig(
                url="redis://queue:6379",
            ),
        )

        with patch("asynctasq.monitoring.emitters.Config.get", return_value=mock_config):
            emitter = RedisEventEmitter()

        assert emitter.redis_url == "redis://queue:6379"

    def test_init_with_explicit_params_overrides_config(self) -> None:
        """Test that explicit parameters override config values."""
        mock_config = Config(
            events=EventsConfig(
                redis_url="redis://events:6379",
                channel="config:events",
            ),
            redis=RedisConfig(
                url="redis://queue:6379",
            ),
        )

        with patch("asynctasq.monitoring.emitters.Config.get", return_value=mock_config):
            emitter = RedisEventEmitter(
                redis_url="redis://explicit:6379", channel="explicit:channel"
            )

        assert emitter.redis_url == "redis://explicit:6379"
        assert emitter.channel == "explicit:channel"

    @mark.asyncio
    async def test_emit_task_event_publishes_to_redis(self, sample_task_event: TaskEvent) -> None:
        """Test that task events are published to Redis."""
        mock_config = Config(
            events=EventsConfig(
                redis_url="redis://localhost:6379",
                channel="test:events",
            ),
        )

        with patch("asynctasq.monitoring.emitters.Config.get", return_value=mock_config):
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
            events=EventsConfig(
                redis_url="redis://localhost:6379",
                channel="test:events",
            ),
        )

        with patch("asynctasq.monitoring.emitters.Config.get", return_value=mock_config):
            emitter = RedisEventEmitter()

        mock_client = AsyncMock()
        emitter._client = mock_client

        await emitter.emit(sample_worker_event)

        mock_client.publish.assert_called_once()

    @mark.asyncio
    async def test_emit_initializes_connection_lazy(self, sample_task_event: TaskEvent) -> None:
        """Test that emit lazily initializes Redis connection."""
        mock_config = Config(
            events=EventsConfig(
                redis_url="redis://localhost:6379",
                channel="test:events",
            ),
        )

        with patch("asynctasq.monitoring.emitters.Config.get", return_value=mock_config):
            emitter = RedisEventEmitter()

        # _client should be None initially
        assert emitter._client is None

        # Mock Redis.from_url
        with patch("redis.asyncio.Redis.from_url") as mock_redis_from_url:
            mock_client = AsyncMock()
            mock_redis_from_url.return_value = mock_client

            await emitter.emit(sample_task_event)

            # Should initialize connection
            mock_redis_from_url.assert_called_once_with(
                "redis://localhost:6379", decode_responses=False
            )
            assert emitter._client == mock_client
            mock_client.publish.assert_called_once()

    @mark.asyncio
    async def test_emit_handles_publish_error_gracefully(
        self, sample_task_event: TaskEvent, caplog
    ) -> None:
        """Test that publish errors are caught and logged."""
        mock_config = Config(
            events=EventsConfig(
                redis_url="redis://localhost:6379",
                channel="test:events",
            ),
        )

        with patch("asynctasq.monitoring.emitters.Config.get", return_value=mock_config):
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
            events=EventsConfig(
                redis_url="redis://localhost:6379",
                channel="test:events",
            ),
        )

        with patch("asynctasq.monitoring.emitters.Config.get", return_value=mock_config):
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
            events=EventsConfig(
                redis_url="redis://localhost:6379",
                channel="test:events",
            ),
        )

        with patch("asynctasq.monitoring.emitters.Config.get", return_value=mock_config):
            emitter = RedisEventEmitter()

        await emitter.close()  # Should not raise

    def test_serialize_event_converts_types(self, sample_task_event: TaskEvent) -> None:
        """Test that event serialization handles type conversions."""
        mock_config = Config(
            events=EventsConfig(
                redis_url="redis://localhost:6379",
                channel="test:events",
            ),
        )

        with patch("asynctasq.monitoring.emitters.Config.get", return_value=mock_config):
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
            events=EventsConfig(
                redis_url="redis://localhost:6379",
                channel="test:events",
            ),
        )

        with patch("asynctasq.monitoring.emitters.Config.get", return_value=mock_config):
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
            events=EventsConfig(
                redis_url="redis://events-server:6379",
                channel="custom:channel",
            ),
            redis=RedisConfig(
                url="redis://queue-server:6379",
            ),
        )

        with patch("asynctasq.monitoring.emitters.Config.get", return_value=mock_config):
            emitter = RedisEventEmitter()

        assert emitter.redis_url == "redis://events-server:6379"

    def test_falls_back_to_redis_url_when_events_url_none(self) -> None:
        """Test fallback to redis_url when events_redis_url is None."""
        mock_config = Config(
            events=EventsConfig(
                redis_url=None,
                channel="asynctasq:events",
            ),
            redis=RedisConfig(
                url="redis://queue-server:6379",
            ),
        )

        with patch("asynctasq.monitoring.emitters.Config.get", return_value=mock_config):
            emitter = RedisEventEmitter()

        assert emitter.redis_url == "redis://queue-server:6379"

    def test_explicit_param_overrides_all_config(self) -> None:
        """Test that explicit redis_url param overrides both config values."""
        mock_config = Config(
            events=EventsConfig(
                redis_url="redis://events-server:6379",
                channel="config:channel",
            ),
            redis=RedisConfig(
                url="redis://queue-server:6379",
            ),
        )

        with patch("asynctasq.monitoring.emitters.Config.get", return_value=mock_config):
            emitter = RedisEventEmitter(redis_url="redis://param:6379")

        assert emitter.redis_url == "redis://param:6379"

    def test_events_channel_from_config(self) -> None:
        """Test that events_channel is read from config."""
        mock_config = Config(
            events=EventsConfig(
                redis_url="redis://localhost:6379",
                channel="my-app:events",
            ),
        )

        with patch("asynctasq.monitoring.emitters.Config.get", return_value=mock_config):
            emitter = RedisEventEmitter()

        assert emitter.channel == "my-app:events"

    def test_channel_param_overrides_config(self) -> None:
        """Test that explicit channel param overrides config."""
        mock_config = Config(
            events=EventsConfig(
                redis_url="redis://localhost:6379",
                channel="config:channel",
            ),
        )

        with patch("asynctasq.monitoring.emitters.Config.get", return_value=mock_config):
            emitter = RedisEventEmitter(channel="param:channel")

        assert emitter.channel == "param:channel"


@mark.unit
class TestEmitterEdgeCases:
    """Edge case tests for emitters to increase coverage."""

    @mark.asyncio
    async def test_logging_emitter_close_is_idempotent(self) -> None:
        """Test LoggingEventEmitter.close is idempotent (can be called multiple times)."""
        emitter = LoggingEventEmitter()

        # Should not raise errors
        await emitter.close()
        await emitter.close()
        await emitter.close()

    @mark.asyncio
    async def test_redis_emitter_close_handles_none_client(self) -> None:
        """Test RedisEventEmitter.close handles None client gracefully."""
        emitter = RedisEventEmitter()

        # _client is None initially
        assert emitter._client is None

        # Should not raise error
        await emitter.close()

    @mark.asyncio
    async def test_redis_emitter_close_handles_client_exception(self) -> None:
        """Test RedisEventEmitter.close raises exception when client close fails."""
        emitter = RedisEventEmitter()
        mock_client = AsyncMock()
        mock_client.aclose.side_effect = Exception("Close error")
        emitter._client = mock_client

        # Should raise the exception
        with raises(Exception, match="Close error"):
            await emitter.close()

    @mark.asyncio
    async def test_redis_emitter_emit_handles_connection_error(self) -> None:
        """Test RedisEventEmitter.emit handles connection errors during publish."""
        emitter = RedisEventEmitter()
        mock_client = AsyncMock()
        mock_client.publish.side_effect = ConnectionError("Connection failed")
        emitter._client = mock_client

        event = TaskEvent(
            event_type=EventType.TASK_STARTED,
            task_id="test-123",
            task_name="test_task",
            queue="default",
            worker_id="worker-123",
            timestamp=datetime.now(UTC),
        )

        # Should not raise error
        await emitter.emit(event)

    @mark.asyncio
    async def test_redis_emitter_emit_handles_json_error(self) -> None:
        """Test RedisEventEmitter.emit handles JSON serialization errors."""
        emitter = RedisEventEmitter()
        mock_client = AsyncMock()
        emitter._client = mock_client

        # Create an event with non-serializable data
        event = TaskEvent(
            event_type=EventType.TASK_STARTED,
            task_id="test-123",
            task_name="test_task",
            queue="default",
            worker_id="worker-123",
            timestamp=datetime.now(UTC),
            error=set(),  # sets are not JSON serializable  # type: ignore
        )

        # Should not raise error
        await emitter.emit(event)

    def test_redis_emitter_serialize_event_with_complex_data(self) -> None:
        """Test RedisEventEmitter.serialize_event with various data types."""
        emitter = RedisEventEmitter()

        event = TaskEvent(
            event_type=EventType.TASK_STARTED,
            task_id="test-123",
            task_name="test_task",
            queue="default",
            worker_id="worker-123",
            timestamp=datetime.now(UTC),
            result={"key": "value", "number": 42, "list": [1, 2, 3]},
        )

        result = emitter._serialize_event(event)

        # Should be valid msgpack
        import msgpack

        parsed = msgpack.unpackb(result)
        assert parsed["event_type"] == "task_started"
        assert parsed["task_id"] == "test-123"
        assert parsed["result"]["key"] == "value"


if __name__ == "__main__":
    main([__file__, "-s", "-m", "unit"])
