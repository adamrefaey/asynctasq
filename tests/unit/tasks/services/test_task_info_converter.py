"""Unit tests for TaskInfoConverter.

Testing Strategy:
- pytest 9.0.1 with asyncio_mode="auto"
- Test conversion from raw bytes to TaskInfo
- Test nested format (class/params/metadata) and flat format
- Test datetime parsing from various formats
- Test error handling for deserialization failures
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

from pytest import main, mark

from asynctasq.tasks.services.task_info_converter import TaskInfoConverter


@mark.unit
class TestTaskInfoConverter:
    """Test TaskInfoConverter class."""

    @mark.asyncio
    async def test_convert_nested_format(self) -> None:
        # Arrange
        serializer = AsyncMock()
        serializer.deserialize.return_value = {
            "class": "asynctasq.tasks.SampleTask",
            "params": {"x": 42, "y": "test"},
            "metadata": {
                "task_id": "task-123",
                "queue": "default",
                "dispatched_at": "2025-12-12T10:00:00+00:00",
                "current_attempt": 1,
                "max_attempts": 3,
                "timeout": 60,
            },
        }

        converter = TaskInfoConverter(serializer)

        # Act
        result = await converter.convert(b"raw_bytes", "default", "pending")

        # Assert
        assert result.id == "task-123"
        assert result.name == "SampleTask"
        assert result.queue == "default"
        assert result.status == "pending"
        assert result.attempt == 1
        assert result.max_attempts == 3
        assert result.timeout_seconds == 60

    @mark.asyncio
    async def test_convert_flat_format(self) -> None:
        # Arrange
        serializer = AsyncMock()
        serializer.deserialize.return_value = {
            "task_id": "flat-task-456",
            "task_name": "ProcessData",
            "queue": "priority",
            "status": "running",
            "enqueued_at": "2025-12-12T11:00:00+00:00",
            "attempt": 2,
            "max_attempts": 5,
        }

        converter = TaskInfoConverter(serializer)

        # Act
        result = await converter.convert(b"raw_bytes", None, None)

        # Assert
        assert result.id == "flat-task-456"
        assert result.name == "ProcessData"
        assert result.queue == "priority"
        assert result.status == "running"
        assert result.attempt == 2
        assert result.max_attempts == 5

    @mark.asyncio
    async def test_convert_handles_deserialization_error(self) -> None:
        # Arrange
        serializer = AsyncMock()
        serializer.deserialize.side_effect = Exception("Invalid bytes")

        converter = TaskInfoConverter(serializer)

        # Act
        result = await converter.convert(b"corrupt_bytes", "error-queue", "failed")

        # Assert (returns minimal TaskInfo on error)
        assert result.id == "unknown"
        assert result.name == "unknown"
        assert result.queue == "error-queue"
        assert result.status == "failed"
        assert isinstance(result.enqueued_at, datetime)

    @mark.asyncio
    async def test_convert_with_optional_datetime_fields(self) -> None:
        # Arrange
        serializer = AsyncMock()
        serializer.deserialize.return_value = {
            "task_id": "task-789",
            "task_name": "AsyncTask",
            "queue": "async",
            "status": "completed",
            "enqueued_at": "2025-12-12T09:00:00+00:00",
            "started_at": "2025-12-12T09:01:00+00:00",
            "completed_at": "2025-12-12T09:02:00+00:00",
            "duration_ms": 60000,
        }

        converter = TaskInfoConverter(serializer)

        # Act
        result = await converter.convert(b"raw_bytes", "async", "completed")

        # Assert
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.duration_ms == 60000

    @mark.asyncio
    async def test_parse_datetime_from_string(self) -> None:
        # Arrange
        converter = TaskInfoConverter(AsyncMock())

        # Act
        result = converter._parse_datetime("2025-12-12T12:00:00+00:00")

        # Assert
        assert result is not None
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 12
        assert result.day == 12

    @mark.asyncio
    async def test_parse_datetime_from_timestamp_int(self) -> None:
        # Arrange
        converter = TaskInfoConverter(AsyncMock())
        timestamp = 1702368000  # 2023-12-12 08:00:00 UTC

        # Act
        result = converter._parse_datetime(timestamp)

        # Assert
        assert result is not None
        assert isinstance(result, datetime)
        assert result.tzinfo == UTC

    @mark.asyncio
    async def test_parse_datetime_from_timestamp_float(self) -> None:
        # Arrange
        converter = TaskInfoConverter(AsyncMock())
        timestamp = 1702368000.5

        # Act
        result = converter._parse_datetime(timestamp)

        # Assert
        assert result is not None
        assert isinstance(result, datetime)

    @mark.asyncio
    async def test_parse_datetime_from_datetime_object(self) -> None:
        # Arrange
        converter = TaskInfoConverter(AsyncMock())
        dt = datetime(2025, 12, 12, 10, 0, 0, tzinfo=UTC)

        # Act
        result = converter._parse_datetime(dt)

        # Assert
        assert result == dt

    @mark.asyncio
    async def test_parse_datetime_from_none(self) -> None:
        # Arrange
        converter = TaskInfoConverter(AsyncMock())

        # Act
        result = converter._parse_datetime(None)

        # Assert
        assert result is None

    @mark.asyncio
    async def test_parse_datetime_from_invalid_string(self) -> None:
        # Arrange
        converter = TaskInfoConverter(AsyncMock())

        # Act
        result = converter._parse_datetime("invalid-date")

        # Assert
        assert result is None

    @mark.asyncio
    async def test_parse_datetime_from_invalid_timestamp(self) -> None:
        # Arrange
        converter = TaskInfoConverter(AsyncMock())
        invalid_timestamp = 999999999999999  # Out of range

        # Act
        result = converter._parse_datetime(invalid_timestamp)

        # Assert
        assert result is None

    @mark.asyncio
    async def test_parse_datetime_from_unsupported_type(self) -> None:
        # Arrange
        converter = TaskInfoConverter(AsyncMock())

        # Act
        result = converter._parse_datetime({"date": "2025-12-12"})  # type: ignore[arg-type]

        # Assert
        assert result is None

    @mark.asyncio
    async def test_convert_with_all_optional_fields(self) -> None:
        # Arrange
        serializer = AsyncMock()
        serializer.deserialize.return_value = {
            "task_id": "full-task",
            "task_name": "FullTask",
            "queue": "full",
            "status": "completed",
            "enqueued_at": "2025-12-12T10:00:00+00:00",
            "started_at": "2025-12-12T10:01:00+00:00",
            "completed_at": "2025-12-12T10:02:00+00:00",
            "duration_ms": 60000,
            "worker_id": "worker-1",
            "attempt": 1,
            "max_attempts": 3,
            "args": [1, 2, 3],
            "kwargs": {"key": "value"},
            "result": "success",
            "exception": None,
            "traceback": None,
            "priority": 5,
            "timeout_seconds": 120,
            "tags": ["urgent", "production"],
        }

        converter = TaskInfoConverter(serializer)

        # Act
        result = await converter.convert(b"raw_bytes", "full", "completed")

        # Assert
        assert result.worker_id == "worker-1"
        assert result.args == [1, 2, 3]
        assert result.kwargs == {"key": "value"}
        assert result.result == "success"
        assert result.priority == 5
        assert result.timeout_seconds == 120
        assert result.tags == ["urgent", "production"]

    @mark.asyncio
    async def test_convert_uses_queue_name_fallback(self) -> None:
        # Arrange
        serializer = AsyncMock()
        serializer.deserialize.return_value = {
            "task_id": "no-queue-task",
            "task_name": "NoQueueTask",
            # No queue field in dict
            "status": "pending",
            "enqueued_at": "2025-12-12T10:00:00+00:00",
        }

        converter = TaskInfoConverter(serializer)

        # Act
        result = await converter.convert(b"raw_bytes", "fallback-queue", "pending")

        # Assert
        assert result.queue == "fallback-queue"

    @mark.asyncio
    async def test_convert_nested_format_class_name_extraction(self) -> None:
        # Arrange
        serializer = AsyncMock()
        serializer.deserialize.return_value = {
            "class": "my_module.tasks.ComplexTask",  # Full module path
            "params": {},
            "metadata": {
                "task_id": "complex-123",
                "queue": "default",
                "dispatched_at": "2025-12-12T10:00:00+00:00",
            },
        }

        converter = TaskInfoConverter(serializer)

        # Act
        result = await converter.convert(b"raw_bytes", "default", "pending")

        # Assert (extracts last part of class path)
        assert result.name == "ComplexTask"

    @mark.asyncio
    async def test_convert_nested_format_without_dot_in_class(self) -> None:
        # Arrange
        serializer = AsyncMock()
        serializer.deserialize.return_value = {
            "class": "SimpleTask",  # No module path
            "params": {},
            "metadata": {
                "task_id": "simple-456",
                "queue": "default",
                "dispatched_at": "2025-12-12T10:00:00+00:00",
            },
        }

        converter = TaskInfoConverter(serializer)

        # Act
        result = await converter.convert(b"raw_bytes", "default", "pending")

        # Assert
        assert result.name == "SimpleTask"


if __name__ == "__main__":
    main([__file__, "-s", "-m", "unit"])
