"""Tests for EventRegistry."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

from pytest import main, mark

from asynctasq.monitoring import EventRegistry, EventType, LoggingEventEmitter, TaskEvent


@mark.unit
class TestEventRegistry:
    """Test EventRegistry functionality."""

    def test_add_emitter(self) -> None:
        """Test adding an emitter to the registry."""
        # Initialize with empty registry
        EventRegistry.init()
        initial_count = len(EventRegistry.get_all())

        emitter = LoggingEventEmitter()
        EventRegistry.add(emitter)

        emitters = EventRegistry.get_all()
        assert emitter in emitters
        assert len(emitters) == initial_count + 1

    def test_get_all_emitters(self) -> None:
        """Test getting all emitters from the registry."""
        EventRegistry.init()

        initial_count = len(EventRegistry.get_all())
        emitter1 = LoggingEventEmitter()
        emitter2 = LoggingEventEmitter()

        EventRegistry.add(emitter1)
        EventRegistry.add(emitter2)

        emitters = EventRegistry.get_all()
        assert len(emitters) >= initial_count + 2  # May include default emitters
        assert emitter1 in emitters
        assert emitter2 in emitters

    @mark.asyncio
    async def test_emit_calls_all_emitters(self) -> None:
        """Test that emit calls all registered emitters."""
        EventRegistry.init()

        emitter1 = LoggingEventEmitter()
        emitter2 = LoggingEventEmitter()

        # Mock the emit methods
        emitter1.emit = AsyncMock()
        emitter2.emit = AsyncMock()

        EventRegistry.add(emitter1)
        EventRegistry.add(emitter2)

        # Create a proper TaskEvent
        event = TaskEvent(
            event_type=EventType.TASK_STARTED,
            task_id="test-task-123",
            task_name="TestTask",
            queue="default",
            worker_id="worker-abc123",
            timestamp=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            attempt=1,
        )

        await EventRegistry.emit(event)

        emitter1.emit.assert_called_once_with(event)
        emitter2.emit.assert_called_once_with(event)

    @mark.asyncio
    async def test_close_all_emitters(self) -> None:
        """Test closing all emitters."""
        EventRegistry.init()

        emitter1 = LoggingEventEmitter()
        emitter2 = LoggingEventEmitter()

        # Mock the close methods
        emitter1.close = AsyncMock()
        emitter2.close = AsyncMock()

        EventRegistry.add(emitter1)
        EventRegistry.add(emitter2)

        await EventRegistry.close_all()

        emitter1.close.assert_called_once()
        emitter2.close.assert_called_once()

    def test_init_clears_and_reinitializes(self) -> None:
        """Test that init clears existing emitters and reinitializes."""
        # Add some emitters
        emitter = LoggingEventEmitter()
        EventRegistry.add(emitter)

        # Init should clear and reinitialize
        EventRegistry.init()

        emitters = EventRegistry.get_all()
        # Should have at least the default logging emitter
        assert len(emitters) >= 1
        # The manually added emitter should be gone
        assert emitter not in emitters


if __name__ == "__main__":
    main([__file__, "-s", "-m", "unit"])
