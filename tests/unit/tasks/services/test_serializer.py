"""Unit tests for TaskSerializer.

Testing Strategy:
- pytest 9.0.1 with asyncio_mode="auto"
- Test serialization/deserialization of BaseTask subclasses
- Test FunctionTask serialization with func metadata
- Test edge cases: __main__ modules, missing func metadata
- Test config restoration and metadata preservation
"""

from __future__ import annotations

from datetime import UTC, datetime

from pytest import main, mark, raises

from asynctasq.serializers.msgspec_serializer import MsgspecSerializer
from asynctasq.tasks import AsyncTask, SyncTask
from asynctasq.tasks.core.task_config import TaskConfig
from asynctasq.tasks.services.serializer import TaskSerializer
from asynctasq.tasks.types.function_task import FunctionTask


class SimpleAsyncTask(AsyncTask):
    """Simple async task for testing serialization."""

    config: TaskConfig = {"queue": "test-queue", "max_attempts": 5, "timeout": 60}

    def __init__(self, value: str, count: int = 1) -> None:
        super().__init__()
        self.value = value
        self.count = count

    async def execute(self) -> str:
        return f"{self.value}_{self.count}"


class SimpleSyncTask(SyncTask):
    """Simple sync task for testing serialization."""

    def __init__(self, x: int, y: int) -> None:
        super().__init__()
        self.x = x
        self.y = y

    def execute(self) -> int:
        return self.x + self.y


@mark.unit
class TestTaskSerializerSerialize:
    """Test TaskSerializer.serialize() method."""

    def test_serialize_async_task(self) -> None:
        # Arrange
        serializer = TaskSerializer(MsgspecSerializer())
        task = SimpleAsyncTask("hello", count=42)
        task._task_id = "task-123"
        task._current_attempt = 2
        task._dispatched_at = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        # Act
        result = serializer.serialize(task)

        # Assert
        assert isinstance(result, bytes)
        assert b"SimpleAsyncTask" in result
        assert b"task-123" in result
        assert b"hello" in result

    def test_serialize_sync_task(self) -> None:
        # Arrange
        serializer = TaskSerializer(MsgspecSerializer())
        task = SimpleSyncTask(x=10, y=20)
        task._task_id = "sync-task-456"

        # Act
        result = serializer.serialize(task)

        # Assert
        assert isinstance(result, bytes)
        assert b"SimpleSyncTask" in result
        assert b"sync-task-456" in result

    def test_serialize_function_task(self) -> None:
        # Arrange
        def my_function(a: int, b: str) -> str:
            return f"{a}_{b}"

        serializer = TaskSerializer(MsgspecSerializer())
        task = FunctionTask(my_function, 10, b="test")
        task._task_id = "func-task-789"

        # Act
        result = serializer.serialize(task)

        # Assert
        assert isinstance(result, bytes)
        assert b"FunctionTask" in result
        assert b"func-task-789" in result
        assert b"my_function" in result

    def test_serialize_preserves_config(self) -> None:
        # Arrange
        serializer = TaskSerializer(MsgspecSerializer())
        task = SimpleAsyncTask("test")
        task._task_id = "config-task"
        task.config["queue"] = "custom-queue"
        task.config["max_attempts"] = 10

        # Act
        result = serializer.serialize(task)

        # Assert
        assert b"custom-queue" in result

    def test_serialize_handles_none_dispatched_at(self) -> None:
        # Arrange
        serializer = TaskSerializer(MsgspecSerializer())
        task = SimpleAsyncTask("test")
        task._task_id = "no-dispatch"
        task._dispatched_at = None

        # Act
        result = serializer.serialize(task)

        # Assert
        assert isinstance(result, bytes)


@mark.unit
class TestTaskSerializerDeserialize:
    """Test TaskSerializer.deserialize() method."""

    @mark.asyncio
    async def test_deserialize_async_task(self) -> None:
        # Arrange
        serializer = TaskSerializer(MsgspecSerializer())
        original = SimpleAsyncTask("world", count=99)
        original._task_id = "deserialize-123"
        original._current_attempt = 3
        original._dispatched_at = datetime(2025, 6, 15, 8, 30, 0, tzinfo=UTC)

        serialized = serializer.serialize(original)

        # Act
        result = await serializer.deserialize(serialized)

        # Assert
        assert isinstance(result, SimpleAsyncTask)
        assert result._task_id == "deserialize-123"
        assert result._current_attempt == 3
        assert result.value == "world"
        assert result.count == 99
        assert result._dispatched_at == datetime(2025, 6, 15, 8, 30, 0, tzinfo=UTC)

    @mark.asyncio
    async def test_deserialize_sync_task(self) -> None:
        # Arrange
        serializer = TaskSerializer(MsgspecSerializer())
        original = SimpleSyncTask(x=5, y=7)
        original._task_id = "sync-deserialize"

        serialized = serializer.serialize(original)

        # Act
        result = await serializer.deserialize(serialized)

        # Assert
        assert isinstance(result, SimpleSyncTask)
        assert result.x == 5
        assert result.y == 7

    @mark.asyncio
    async def test_deserialize_function_task(self) -> None:
        # Arrange - use a module-level function that can be resolved
        # Local functions inside test methods cannot be deserialized
        # because they're not accessible at module level
        import os

        serializer = TaskSerializer(MsgspecSerializer())
        # Use os.path.exists which is a known module-level function
        original = FunctionTask(os.path.exists, "/tmp")
        original._task_id = "func-deserialize"

        serialized = serializer.serialize(original)

        # Act
        result = await serializer.deserialize(serialized)

        # Assert
        assert isinstance(result, FunctionTask)
        assert result._task_id == "func-deserialize"
        assert result.args == ("/tmp",)

    @mark.asyncio
    async def test_deserialize_restores_config(self) -> None:
        # Arrange
        serializer = TaskSerializer(MsgspecSerializer())
        original = SimpleAsyncTask("config-test")
        original._task_id = "config-deserialize"
        original.config["queue"] = "restored-queue"
        original.config["max_attempts"] = 7
        original.config["retry_delay"] = 30
        original.config["timeout"] = 120
        original.config["visibility_timeout"] = 7200

        serialized = serializer.serialize(original)

        # Act
        result = await serializer.deserialize(serialized)

        # Assert
        assert result.config.get("queue") == "restored-queue"
        assert result.config.get("max_attempts") == 7
        assert result.config.get("retry_delay") == 30
        assert result.config.get("timeout") == 120
        assert result.config.get("visibility_timeout") == 7200

    @mark.asyncio
    async def test_deserialize_handles_none_dispatched_at(self) -> None:
        # Arrange
        serializer = TaskSerializer(MsgspecSerializer())
        original = SimpleAsyncTask("no-dispatch")
        original._task_id = "no-dispatch-deserialize"
        original._dispatched_at = None

        serialized = serializer.serialize(original)

        # Act
        result = await serializer.deserialize(serialized)

        # Assert
        assert result._dispatched_at is None

    @mark.asyncio
    async def test_deserialize_handles_invalid_dispatched_at(self) -> None:
        # Arrange
        serializer = TaskSerializer(MsgspecSerializer())
        # Manually create task data with invalid dispatched_at
        task_data = {
            "class": f"{SimpleAsyncTask.__module__}.SimpleAsyncTask",
            "params": {"value": "test", "count": 1},
            "metadata": {
                "task_id": "invalid-date",
                "current_attempt": 0,
                "dispatched_at": "not-a-valid-date",
                "queue": "default",
                "max_attempts": 3,
                "retry_delay": 60,
                "timeout": None,
                "visibility_timeout": 3600,
            },
        }
        serialized = MsgspecSerializer().serialize(task_data)

        # Act
        result = await serializer.deserialize(serialized)

        # Assert
        assert result._dispatched_at is None


@mark.unit
class TestTaskSerializerRoundTrip:
    """Test full serialization/deserialization roundtrip."""

    @mark.asyncio
    async def test_roundtrip_preserves_all_attributes(self) -> None:
        # Arrange
        serializer = TaskSerializer(MsgspecSerializer())
        original = SimpleAsyncTask("roundtrip", count=123)
        original._task_id = "roundtrip-task"
        original._current_attempt = 5
        original._dispatched_at = datetime(2025, 12, 25, 0, 0, 0, tzinfo=UTC)
        original.config["queue"] = "special-queue"
        original.config["max_attempts"] = 10
        original.config["timeout"] = 300

        # Act
        serialized = serializer.serialize(original)
        restored = await serializer.deserialize(serialized)

        # Assert
        assert restored._task_id == original._task_id
        assert restored._current_attempt == original._current_attempt
        assert restored._dispatched_at == original._dispatched_at
        assert isinstance(restored, SimpleAsyncTask)
        assert restored.value == original.value
        assert restored.count == original.count
        assert restored.config.get("queue") == original.config.get("queue")
        assert restored.config.get("max_attempts") == original.config.get("max_attempts")
        assert restored.config.get("timeout") == original.config.get("timeout")

    @mark.asyncio
    async def test_roundtrip_function_task_with_kwargs(self) -> None:
        # Arrange - use a module-level function
        # Local functions inside test methods cannot be deserialized
        import json

        serializer = TaskSerializer(MsgspecSerializer())
        # Use json.dumps which accepts kwargs
        original = FunctionTask(json.dumps, {"key": "value"}, indent=2)
        original._task_id = "complex-func"

        # Act
        serialized = serializer.serialize(original)
        restored = await serializer.deserialize(serialized)

        # Assert
        assert isinstance(restored, FunctionTask)
        assert restored.args == ({"key": "value"},)
        assert restored.kwargs == {"indent": 2}


@mark.unit
class TestTaskSerializerEdgeCases:
    """Test edge cases and error conditions."""

    @mark.asyncio
    async def test_deserialize_function_task_missing_func_module_raises(self) -> None:
        # Arrange
        serializer = TaskSerializer(MsgspecSerializer())
        # Create task data without func_module
        task_data = {
            "class": f"{FunctionTask.__module__}.FunctionTask",
            "params": {"args": (), "kwargs": {}},
            "metadata": {
                "task_id": "bad-func",
                "current_attempt": 0,
                "dispatched_at": None,
                "queue": "default",
                "max_attempts": 3,
                "retry_delay": 60,
                "timeout": None,
                "visibility_timeout": 3600,
                # Missing func_module and func_name
            },
        }
        serialized = MsgspecSerializer().serialize(task_data)

        # Act & Assert
        with raises(ValueError, match="FunctionTask missing func_module or func_name"):
            await serializer.deserialize(serialized)

    @mark.asyncio
    async def test_to_task_info_delegates_to_converter(self) -> None:
        # Arrange
        serializer = TaskSerializer(MsgspecSerializer())
        task = SimpleAsyncTask("info-test")
        task._task_id = "info-task-id"
        task._dispatched_at = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)

        serialized = serializer.serialize(task)

        # Act
        result = await serializer.to_task_info(serialized, "info-queue", "pending")

        # Assert
        assert result.id == "info-task-id"
        assert result.name == "SimpleAsyncTask"
        # Queue from metadata takes precedence over passed queue_name
        assert result.queue == "test-queue"

    def test_serialize_filters_private_attributes(self) -> None:
        # Arrange
        serializer = TaskSerializer(MsgspecSerializer())
        task = SimpleAsyncTask("private-test")
        task._task_id = "private-task"
        task._some_internal_attr = "should-not-serialize"  # type: ignore[attr-defined]

        # Act
        result = serializer.serialize(task)

        # Assert
        # Private attributes starting with _ should not be in params
        assert b"_some_internal_attr" not in result

    def test_serialize_filters_callable_attributes(self) -> None:
        # Arrange
        serializer = TaskSerializer(MsgspecSerializer())
        task = SimpleAsyncTask("callable-test")
        task._task_id = "callable-task"

        # Add a method-like callable (shouldn't be serialized)
        task.custom_method = lambda: None  # type: ignore[attr-defined]

        # Act
        result = serializer.serialize(task)

        # Assert
        assert b"custom_method" not in result


@mark.unit
class TestTaskSerializerMainModule:
    """Test serialization with __main__ modules (normalized to __main__)."""

    @mark.asyncio
    async def test_serialize_normalizes_asynctasq_main_module(self) -> None:
        # Arrange
        serializer = TaskSerializer(MsgspecSerializer())
        task = SimpleAsyncTask("main-test")
        task._task_id = "main-task"

        # Simulate the task class coming from an __asynctasq_main_ module
        original_module = task.__class__.__module__

        # Act
        serialized = serializer.serialize(task)

        # Assert - module name should be preserved as-is (not __asynctasq_main_)
        # since SimpleAsyncTask is from the test module
        assert original_module.encode() in serialized

    @mark.asyncio
    async def test_serialize_task_from_asynctasq_main_module(self) -> None:
        """Test that __asynctasq_main_ prefix is normalized to __main__."""
        from unittest.mock import patch

        serializer = TaskSerializer(MsgspecSerializer())
        task = SimpleAsyncTask("asynctasq-main-test")
        task._task_id = "asynctasq-main-task"

        # Patch the module name to simulate __asynctasq_main_ module
        with patch.object(task.__class__, "__module__", "__asynctasq_main_12345__"):
            serialized = serializer.serialize(task)

        # Assert - module name should be normalized to __main__
        assert b"__main__.SimpleAsyncTask" in serialized
        assert b"__asynctasq_main_" not in serialized


if __name__ == "__main__":
    main([__file__, "-s", "-m", "unit"])
