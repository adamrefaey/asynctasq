"""Tests for ProcessPoolManager."""

from __future__ import annotations

import pytest

from asynctasq.tasks.infrastructure.process_pool_manager import ProcessPoolManager


@pytest.fixture
def manager() -> ProcessPoolManager:
    """Create a ProcessPoolManager instance for testing."""
    return ProcessPoolManager()


@pytest.mark.unit
class TestProcessPoolManagerHealthMonitoring:
    """Test ProcessPoolManager health monitoring methods."""

    def test_is_initialized_returns_false_initially(self, manager: ProcessPoolManager) -> None:
        """Test is_initialized returns False before initialization."""
        assert not manager.is_initialized()

    def test_is_initialized_returns_true_after_init(self, manager: ProcessPoolManager) -> None:
        """Test is_initialized returns True after initialization."""
        manager.get_sync_pool()  # Trigger auto-initialization
        assert manager.is_initialized()

    def test_is_initialized_returns_false_after_shutdown(self, manager: ProcessPoolManager) -> None:
        """Test is_initialized returns False after shutdown."""
        manager.get_sync_pool()  # Trigger auto-initialization
        assert manager.is_initialized()

        import asyncio

        asyncio.run(manager.shutdown(wait=True))
        assert not manager.is_initialized()

    def test_get_stats_not_initialized(self, manager: ProcessPoolManager) -> None:
        """Test get_stats returns proper status when not initialized."""
        stats = manager.get_stats()

        assert stats["sync"]["status"] == "not_initialized"
        assert stats["async"]["status"] == "not_initialized"

    def test_get_stats_initialized(self, manager: ProcessPoolManager) -> None:
        """Test get_stats returns pool info when initialized."""
        # Create manager with specific config for this test
        test_manager = ProcessPoolManager(sync_max_workers=4)
        test_manager.get_sync_pool()  # Trigger initialization

        stats = test_manager.get_stats()

        assert stats["sync"]["status"] == "initialized"
        assert stats["sync"]["pool_size"] == 4
        assert stats["sync"]["max_tasks_per_child"] == 100

    def test_get_stats_without_max_tasks_per_child(self, manager: ProcessPoolManager) -> None:
        """Test get_stats when max_tasks_per_child is explicitly set."""
        # Create manager with specific config for this test
        test_manager = ProcessPoolManager(sync_max_workers=2, sync_max_tasks_per_child=100)
        test_manager.get_sync_pool()  # Trigger initialization

        stats = test_manager.get_stats()

        assert stats["sync"]["status"] == "initialized"
        assert stats["sync"]["pool_size"] == 2
        assert stats["sync"]["max_tasks_per_child"] == 100

    def test_is_initialized_thread_safe(self, manager: ProcessPoolManager) -> None:
        """Test that is_initialized is thread-safe."""
        import concurrent.futures
        import threading

        results = []
        lock = threading.Lock()

        def check_initialized() -> None:
            result = manager.is_initialized()
            with lock:
                results.append(result)

        # Initialize pool in one thread, check in others
        manager.get_sync_pool()  # Trigger initialization

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(check_initialized) for _ in range(10)]
            concurrent.futures.wait(futures)

        # All checks should return True
        assert all(results)
        assert len(results) == 10

    def test_get_stats_thread_safe(self, manager: ProcessPoolManager) -> None:
        """Test that get_stats is thread-safe."""
        import concurrent.futures
        import threading

        results = []
        lock = threading.Lock()

        # Create manager with specific config for this test
        test_manager = ProcessPoolManager(sync_max_workers=3, sync_max_tasks_per_child=50)
        test_manager.get_sync_pool()  # Trigger initialization

        def get_stats_check() -> None:
            stats = test_manager.get_stats()
            with lock:
                results.append(stats)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(get_stats_check) for _ in range(10)]
            concurrent.futures.wait(futures)

        # All checks should return consistent stats
        assert len(results) == 10
        for stats in results:
            assert stats["sync"]["status"] == "initialized"
            assert stats["sync"]["pool_size"] == 3
            assert stats["sync"]["max_tasks_per_child"] == 50


@pytest.mark.unit
class TestProcessPoolManagerValidation:
    """Test ProcessPoolManager input validation (Issue #16)."""

    def test_initialize_with_invalid_type_raises_type_error(
        self, manager: ProcessPoolManager
    ) -> None:
        """Test that non-integer max_workers raises TypeError when pool is created."""
        test_manager = ProcessPoolManager(sync_max_workers="invalid")  # type: ignore
        with pytest.raises(TypeError):
            test_manager.get_sync_pool()  # Error occurs here

    def test_initialize_with_float_raises_type_error(self, manager: ProcessPoolManager) -> None:
        """Test that float max_workers raises TypeError when pool is created."""
        test_manager = ProcessPoolManager(sync_max_workers=3.5)  # type: ignore
        with pytest.raises(TypeError):
            test_manager.get_sync_pool()  # Error occurs here

    def test_initialize_with_zero_raises_value_error(self, manager: ProcessPoolManager) -> None:
        """Test that max_workers=0 raises ValueError when pool is created."""
        test_manager = ProcessPoolManager(sync_max_workers=0)
        with pytest.raises(ValueError):
            test_manager.get_sync_pool()  # Error occurs here

    def test_initialize_with_negative_raises_value_error(self, manager: ProcessPoolManager) -> None:
        """Test that negative max_workers raises ValueError when pool is created."""
        test_manager = ProcessPoolManager(sync_max_workers=-5)
        with pytest.raises(ValueError):
            test_manager.get_sync_pool()  # Error occurs here

    def test_initialize_with_max_allowed_value_succeeds(self, manager: ProcessPoolManager) -> None:
        """Test that max_workers=1000 (large value) succeeds."""
        test_manager = ProcessPoolManager(sync_max_workers=1000)
        test_manager.get_sync_pool()  # Trigger initialization
        assert test_manager.is_initialized()
        stats = test_manager.get_stats()
        assert stats["sync"]["pool_size"] == 1000

    def test_initialize_with_valid_value_succeeds(self, manager: ProcessPoolManager) -> None:
        """Test that valid max_workers succeeds."""
        test_manager = ProcessPoolManager(sync_max_workers=4)
        test_manager.get_sync_pool()  # Trigger initialization
        assert test_manager.is_initialized()
        stats = test_manager.get_stats()
        assert stats["sync"]["pool_size"] == 4

    def test_initialize_with_none_uses_default(self, manager: ProcessPoolManager) -> None:
        """Test that max_workers=None uses CPU count default."""
        test_manager = ProcessPoolManager(sync_max_workers=None)
        test_manager.get_sync_pool()  # Trigger initialization
        assert test_manager.is_initialized()
        stats = test_manager.get_stats()
        # Should default to CPU count or 4
        assert stats["sync"]["pool_size"] is not None
        assert stats["sync"]["pool_size"] >= 1

    def test_initialize_with_boundary_value_one(self, manager: ProcessPoolManager) -> None:
        """Test that max_workers=1 (minimum) succeeds."""
        test_manager = ProcessPoolManager(sync_max_workers=1)
        test_manager.get_sync_pool()  # Trigger initialization
        assert test_manager.is_initialized()
        stats = test_manager.get_stats()
        assert stats["sync"]["pool_size"] == 1

    def test_error_message_includes_helpful_context(self, manager: ProcessPoolManager) -> None:
        """Test that error messages from ProcessPoolExecutor are clear."""
        test_manager = ProcessPoolManager(sync_max_workers=0)
        with pytest.raises(ValueError) as exc_info:
            test_manager.get_sync_pool()  # Error from ProcessPoolExecutor

        error_msg = str(exc_info.value)
        # ProcessPoolExecutor validation error
        assert "max_workers" in error_msg.lower()
