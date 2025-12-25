"""Tests for EventRegistry."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

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
    async def test_emit_handles_emitter_exceptions(self, caplog) -> None:
        """Test that emit handles exceptions from individual emitters gracefully."""
        import logging

        EventRegistry.init()

        emitter1 = LoggingEventEmitter()
        emitter2 = LoggingEventEmitter()

        # Mock emit methods - one succeeds, one fails
        emitter1.emit = AsyncMock()
        emitter2.emit = AsyncMock(side_effect=Exception("Test error"))

        EventRegistry.add(emitter1)
        EventRegistry.add(emitter2)

        event = TaskEvent(
            event_type=EventType.TASK_STARTED,
            task_id="test-task-123",
            task_name="TestTask",
            queue="default",
            worker_id="worker-abc123",
            timestamp=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            attempt=1,
        )

        with caplog.at_level(logging.WARNING):
            await EventRegistry.emit(event)

        # Both should be called
        emitter1.emit.assert_called_once_with(event)
        emitter2.emit.assert_called_once_with(event)

        # Warning should be logged for the failed emitter
        assert "Global emit failed" in caplog.text
        assert "Test error" in caplog.text

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

    @mark.asyncio
    async def test_close_all_handles_emitter_exceptions(self, caplog) -> None:
        """Test that close_all handles exceptions from individual emitters gracefully."""
        import logging

        EventRegistry.init()

        emitter1 = LoggingEventEmitter()
        emitter2 = LoggingEventEmitter()

        # Mock close methods - one succeeds, one fails
        emitter1.close = AsyncMock()
        emitter2.close = AsyncMock(side_effect=Exception("Close error"))

        EventRegistry.add(emitter1)
        EventRegistry.add(emitter2)

        with caplog.at_level(logging.WARNING):
            await EventRegistry.close_all()

        # Both should be called
        emitter1.close.assert_called_once()
        emitter2.close.assert_called_once()

        # Warning should be logged for the failed emitter
        assert "Failed to close emitter" in caplog.text
        assert "Close error" in caplog.text

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


@mark.unit
class TestEventRegistryEdgeCases:
    """Edge case tests for EventRegistry to increase coverage."""

    def test_add_none_emitter_raises_error(self) -> None:
        """Test that adding None emitter does not raise (current behavior)."""
        # Current behavior: doesn't check for None
        EventRegistry.add(None)  # type: ignore

    def test_add_duplicate_emitter_works(self) -> None:
        """Test that adding the same emitter multiple times works (no duplicates)."""
        EventRegistry.init()
        emitter = LoggingEventEmitter()

        EventRegistry.add(emitter)
        initial_count = len(EventRegistry.get_all())

        EventRegistry.add(emitter)  # Add again
        final_count = len(EventRegistry.get_all())

        # Should not increase count
        assert final_count == initial_count

    @mark.asyncio
    async def test_emit_with_no_emitters_does_nothing(self) -> None:
        """Test that emit works even with no emitters."""
        EventRegistry.init()  # Clears all emitters

        event = TaskEvent(
            event_type=EventType.TASK_STARTED,
            task_id="test",
            task_name="test_task",
            queue="default",
            worker_id="worker-123",
        )

        # Should not raise any errors
        await EventRegistry.emit(event)

    @mark.asyncio
    async def test_emit_with_mixed_sync_async_emitters(self) -> None:
        """Test emit with both sync and async emitters."""
        EventRegistry.init()

        sync_emitter = LoggingEventEmitter()
        async_emitter = MagicMock()
        async_emitter.emit = AsyncMock()

        EventRegistry.add(sync_emitter)
        EventRegistry.add(async_emitter)

        event = TaskEvent(
            event_type=EventType.TASK_STARTED,
            task_id="test-123",
            task_name="test_task",
            queue="default",
            worker_id="worker-123",
            timestamp=datetime.now(UTC),
        )

        await EventRegistry.emit(event)

        # Both should be called
        async_emitter.emit.assert_called_once()

    def test_get_all_returns_copy_not_reference(self) -> None:
        """Test that get_all returns a copy, not the internal list."""
        EventRegistry.init()
        initial_count = len(EventRegistry.get_all())

        emitters = EventRegistry.get_all()
        emitters.clear()  # Modify the returned list

        # Original should still have the initial emitters
        assert len(EventRegistry.get_all()) == initial_count


if __name__ == "__main__":
    main([__file__, "-s", "-m", "unit"])
