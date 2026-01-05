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
        """Test that task events are logged with Rich formatting."""
        import logging

        with caplog.at_level(logging.INFO):
            emitter = LoggingEventEmitter()
            await emitter.emit(sample_task_event)

        # Verify Rich-formatted output
        assert "🚀" in caplog.text  # Task started icon
        assert "Task Started" in caplog.text  # Formatted event name
        assert "test-tas" in caplog.text  # Truncated task ID (first 8 chars)
        assert "TestTask" in caplog.text  # Task name
        assert "default" in caplog.text  # Queue name

    @mark.asyncio
    async def test_emit_worker_event_logs(self, sample_worker_event: WorkerEvent, caplog) -> None:
        """Test that worker events are logged with Rich formatting."""
        import logging

        with caplog.at_level(logging.INFO):
            emitter = LoggingEventEmitter()
            await emitter.emit(sample_worker_event)

        # Verify Rich-formatted output
        assert "🟢" in caplog.text  # Worker online icon
        assert "Worker Online" in caplog.text  # Formatted event name
        assert "worker-abc123" in caplog.text  # Worker ID
        assert "default" in caplog.text  # Queue names
        assert "test-host" in caplog.text  # Hostname

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


@mark.unit
class TestLoggingEventEmitterFormatting:
    """Test LoggingEventEmitter formatting methods."""

    def test_format_duration_fast(self) -> None:
        """Test _format_duration for fast tasks (<1s)."""
        emitter = LoggingEventEmitter()
        result = emitter._format_duration(500)  # 500ms
        assert "500ms" in result
        assert "⚡" in result  # Fast icon

    def test_format_duration_medium(self) -> None:
        """Test _format_duration for medium tasks (1-5s)."""
        emitter = LoggingEventEmitter()
        result = emitter._format_duration(3000)  # 3s
        assert "3.00s" in result
        assert "✨" in result

    def test_format_duration_slow(self) -> None:
        """Test _format_duration for slow tasks (5-30s)."""
        emitter = LoggingEventEmitter()
        result = emitter._format_duration(15000)  # 15s
        assert "15.00s" in result
        assert "⏱️" in result

    def test_format_duration_very_slow(self) -> None:
        """Test _format_duration for very slow tasks (>30s)."""
        emitter = LoggingEventEmitter()
        result = emitter._format_duration(45000)  # 45s
        assert "45.00s" in result
        assert "🐌" in result

    def test_format_duration_minutes(self) -> None:
        """Test _format_duration for tasks taking minutes."""
        emitter = LoggingEventEmitter()
        result = emitter._format_duration(125000)  # 125s = 2m 5s
        assert "2m" in result
        assert "5." in result  # 5.0s

    def test_format_duration_none(self) -> None:
        """Test _format_duration with None duration."""
        emitter = LoggingEventEmitter()
        result = emitter._format_duration(None)
        assert result == ""

    def test_format_task_event_completed(self) -> None:
        """Test _format_task_event for completed task."""
        emitter = LoggingEventEmitter()
        event = TaskEvent(
            event_type=EventType.TASK_COMPLETED,
            task_id="task-123",
            task_name="ProcessData",
            queue="default",
            worker_id="worker-1",
            timestamp=datetime.now(UTC),
            attempt=1,
            duration_ms=1500,
        )
        result = emitter._format_task_event(event)
        assert "✅" in result
        assert "Task Completed" in result
        assert "ProcessData" in result

    def test_format_task_event_failed_with_error(self) -> None:
        """Test _format_task_event for failed task with error message."""
        emitter = LoggingEventEmitter()
        event = TaskEvent(
            event_type=EventType.TASK_FAILED,
            task_id="task-456",
            task_name="FailTask",
            queue="default",
            worker_id="worker-1",
            timestamp=datetime.now(UTC),
            attempt=2,
            duration_ms=500,
            error="Connection timeout",
        )
        result = emitter._format_task_event(event)
        assert "❌" in result
        assert "Task Failed" in result
        assert "Connection timeout" in result

    def test_format_task_event_retrying(self) -> None:
        """Test _format_task_event for retrying task."""
        emitter = LoggingEventEmitter()
        event = TaskEvent(
            event_type=EventType.TASK_REENQUEUED,  # Use valid event type
            task_id="task-789",
            task_name="RetryTask",
            queue="default",
            worker_id="worker-1",
            timestamp=datetime.now(UTC),
            attempt=3,
        )
        result = emitter._format_task_event(event)
        assert "📤" in result  # Reenqueued icon
        assert "Task Reenqueued" in result
        assert "3" in result  # Attempt number

    def test_format_task_event_enqueued(self) -> None:
        """Test _format_task_event for enqueued task."""
        emitter = LoggingEventEmitter()
        event = TaskEvent(
            event_type=EventType.TASK_ENQUEUED,
            task_id="task-abc",
            task_name="NewTask",
            queue="high-priority",
            worker_id="worker-1",
            timestamp=datetime.now(UTC),
            attempt=1,
        )
        result = emitter._format_task_event(event)
        assert "📥" in result
        assert "Task Enqueued" in result
        assert "high-priority" in result

    def test_format_task_event_cancelled(self) -> None:
        """Test _format_task_event for cancelled task."""
        emitter = LoggingEventEmitter()
        event = TaskEvent(
            event_type=EventType.TASK_CANCELLED,
            task_id="task-xyz",
            task_name="CancelledTask",
            queue="default",
            worker_id="worker-1",
            timestamp=datetime.now(UTC),
            attempt=1,
        )
        result = emitter._format_task_event(event)
        assert "🚫" in result
        assert "Task Cancelled" in result

    def test_format_worker_event_offline(self) -> None:
        """Test _format_worker_event for offline worker."""
        emitter = LoggingEventEmitter()
        event = WorkerEvent(
            event_type=EventType.WORKER_OFFLINE,
            worker_id="worker-1",
            hostname="host1",
            timestamp=datetime.now(UTC),
            queues=("default",),
            active=0,
            processed=150,
            uptime_seconds=3600,
        )
        result = emitter._format_worker_event(event)
        assert "🔴" in result
        assert "Worker Offline" in result
        assert "150" in result  # Processed count
        assert "1h 0m 0s" in result  # Uptime

    def test_format_worker_event_heartbeat(self) -> None:
        """Test _format_worker_event for heartbeat."""
        emitter = LoggingEventEmitter()
        event = WorkerEvent(
            event_type=EventType.WORKER_HEARTBEAT,
            worker_id="worker-2",
            hostname="host2",
            timestamp=datetime.now(UTC),
            queues=("default", "high"),
            active=3,
            processed=75,
        )
        result = emitter._format_worker_event(event)
        assert "💓" in result
        assert "Worker Heartbeat" in result
        assert "3" in result  # Active tasks

    def test_format_worker_event_uptime_no_seconds(self) -> None:
        """Test worker offline formatting without uptime_seconds."""
        emitter = LoggingEventEmitter()
        event = WorkerEvent(
            event_type=EventType.WORKER_OFFLINE,
            worker_id="worker-3",
            hostname="host3",
            timestamp=datetime.now(UTC),
            queues=("default",),
            active=0,
            processed=50,
            uptime_seconds=None,
        )
        result = emitter._format_worker_event(event)
        assert "🔴" in result
        assert "Worker Offline" in result
        assert "uptime" not in result.lower() or "None" not in result


@mark.unit
class TestRedisEventEmitterSerialization:
    """Test Redis event emitter serialization edge cases."""

    def test_serialize_event_msgpack_none_handling(self) -> None:
        """Test _serialize_event when msgpack.encode returns None."""
        from unittest.mock import patch

        emitter = RedisEventEmitter()
        event = TaskEvent(
            event_type=EventType.TASK_STARTED,
            task_id="test-123",
            task_name="TestTask",
            queue="default",
            worker_id="worker-1",
            timestamp=datetime.now(UTC),
            attempt=1,
        )

        with patch("asynctasq.monitoring.emitters.msgpack.encode", return_value=None):
            with raises(ValueError, match="msgpack.packb returned None"):
                emitter._serialize_event(event)

    def test_serialize_event_preserves_all_fields(self) -> None:
        """Test _serialize_event preserves all event fields."""
        emitter = RedisEventEmitter()
        event = TaskEvent(
            event_type=EventType.TASK_COMPLETED,
            task_id="task-full",
            task_name="FullTask",
            queue="test-queue",
            worker_id="worker-full",
            timestamp=datetime.now(UTC),
            attempt=2,
            duration_ms=5000,
            error="Some error",
            result={"data": "result"},
        )

        serialized = emitter._serialize_event(event)

        import msgpack

        deserialized = msgpack.unpackb(serialized)

        assert deserialized["event_type"] == "task_completed"
        assert deserialized["task_id"] == "task-full"
        assert deserialized["task_name"] == "FullTask"
        assert deserialized["queue"] == "test-queue"
        assert deserialized["worker_id"] == "worker-full"
        assert deserialized["attempt"] == 2
        assert deserialized["duration_ms"] == 5000
        assert deserialized["error"] == "Some error"
        assert deserialized["result"]["data"] == "result"

    @mark.asyncio
    async def test_redis_emitter_emit_handles_serialization_exception(self) -> None:
        """Test emit handles exceptions during serialization."""
        from unittest.mock import patch

        emitter = RedisEventEmitter()
        emitter._client = AsyncMock()

        event = TaskEvent(
            event_type=EventType.TASK_STARTED,
            task_id="test-456",
            task_name="TestTask",
            queue="default",
            worker_id="worker-1",
            timestamp=datetime.now(UTC),
            attempt=1,
        )

        with patch.object(
            emitter, "_serialize_event", side_effect=Exception("Serialization error")
        ):
            # Should not raise
            await emitter.emit(event)


@mark.unit
class TestRedisEventEmitterConnection:
    """Test Redis event emitter connection management."""

    @mark.asyncio
    async def test_ensure_connected_creates_client_once(self) -> None:
        """Test _ensure_connected creates client only once."""
        emitter = RedisEventEmitter(redis_url="redis://test:6379")

        assert emitter._client is None

        with patch("redis.asyncio.Redis.from_url") as mock_from_url:
            mock_client = AsyncMock()
            mock_from_url.return_value = mock_client

            # First call
            await emitter._ensure_connected()
            assert emitter._client is mock_client
            assert mock_from_url.call_count == 1

            # Second call - should not create new client
            await emitter._ensure_connected()
            assert emitter._client is mock_client
            assert mock_from_url.call_count == 1  # Still 1

    @mark.asyncio
    async def test_emit_calls_ensure_connected(self) -> None:
        """Test emit calls _ensure_connected before publishing."""
        emitter = RedisEventEmitter()

        event = TaskEvent(
            event_type=EventType.TASK_STARTED,
            task_id="test-789",
            task_name="TestTask",
            queue="default",
            worker_id="worker-1",
            timestamp=datetime.now(UTC),
            attempt=1,
        )

        with patch.object(emitter, "_ensure_connected") as mock_ensure:
            mock_client = AsyncMock()
            emitter._client = mock_client

            await emitter.emit(event)

            mock_ensure.assert_called_once()

    @mark.asyncio
    async def test_close_sets_client_to_none(self) -> None:
        """Test close sets _client to None after closing."""
        emitter = RedisEventEmitter()
        mock_client = AsyncMock()
        emitter._client = mock_client

        await emitter.close()

        assert emitter._client is None


if __name__ == "__main__":
    main([__file__, "-s", "-m", "unit"])
