"""Tests for ProcessPoolManager."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pytest import main

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

        from asynctasq.utils.loop import run

        run(manager.shutdown(wait=True))
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


@pytest.mark.unit
class TestProcessPoolManagerAdvanced:
    """Test ProcessPoolManager advanced features."""

    @pytest.mark.asyncio
    async def test_context_manager_async(self) -> None:
        """Test ProcessPoolManager as async context manager."""
        # Arrange & Act
        async with ProcessPoolManager(sync_max_workers=2) as manager:
            # Assert - should be initialized
            assert manager.is_initialized()
            pool = manager.get_sync_pool()
            assert pool is not None

        # Assert - should be shutdown after exit
        assert not manager.is_initialized()

    @pytest.mark.asyncio
    async def test_initialize_warm_event_loop(self) -> None:
        """Test initialize() sets up warm event loops."""
        from unittest.mock import patch

        # Arrange
        manager = ProcessPoolManager(async_max_workers=2)

        with patch("asynctasq.tasks.infrastructure.process_pool_manager.init_warm_event_loop"):
            # Act
            await manager.initialize()

            # Assert - warm loop initializer passed to pool
            assert manager.is_initialized()

    @pytest.mark.asyncio
    async def test_get_sync_pool_auto_initializes(self) -> None:
        """Test get_sync_pool() auto-initializes if not initialized."""
        # Arrange
        manager = ProcessPoolManager(sync_max_workers=3)

        # Act
        pool = manager.get_sync_pool()

        # Assert
        assert pool is not None
        assert manager.is_initialized()

    @pytest.mark.asyncio
    async def test_get_async_pool_auto_initializes(self) -> None:
        """Test get_async_pool() auto-initializes if not initialized."""
        # Arrange
        manager = ProcessPoolManager(async_max_workers=3)

        # Act
        pool = manager.get_async_pool()

        # Assert
        assert pool is not None
        assert manager.is_initialized()

    @pytest.mark.asyncio
    async def test_shutdown_with_cancel_futures(self) -> None:
        """Test shutdown(cancel_futures=True) cancels pending futures."""
        # Arrange
        manager = ProcessPoolManager(sync_max_workers=2)
        manager.get_sync_pool()

        # Act
        await manager.shutdown(wait=False, cancel_futures=True)

        # Assert
        assert not manager.is_initialized()

    @pytest.mark.asyncio
    async def test_shutdown_handles_sync_pool_exception(self) -> None:
        """Test shutdown handles exceptions from sync pool shutdown."""
        # Arrange
        manager = ProcessPoolManager(sync_max_workers=2)
        manager.get_sync_pool()

        # Mock the sync pool to raise exception during shutdown
        mock_pool = manager._sync_pool
        assert mock_pool is not None  # Pool should be initialized
        mock_pool.shutdown = MagicMock(side_effect=RuntimeError("Mock shutdown error"))

        # Act & Assert - should raise the exception
        with pytest.raises(RuntimeError, match="Mock shutdown error"):
            await manager.shutdown(wait=True)

    @pytest.mark.asyncio
    async def test_shutdown_handles_async_pool_exception(self) -> None:
        """Test shutdown handles exceptions from async pool shutdown."""
        # Arrange
        manager = ProcessPoolManager(async_max_workers=2)
        manager.get_async_pool()

        # Mock the async pool to raise exception during shutdown
        mock_pool = manager._async_pool
        assert mock_pool is not None  # Pool should be initialized
        mock_pool.shutdown = MagicMock(side_effect=RuntimeError("Mock async shutdown error"))

        # Act & Assert - should raise the exception
        with pytest.raises(RuntimeError, match="Mock async shutdown error"):
            await manager.shutdown(wait=True)

    @pytest.mark.asyncio
    async def test_shutdown_handles_multiple_exceptions(self) -> None:
        """Test shutdown handles multiple pool exceptions and raises ExceptionGroup."""
        # Arrange
        manager = ProcessPoolManager(sync_max_workers=2, async_max_workers=2)
        manager.get_sync_pool()
        manager.get_async_pool()

        # Mock both pools to raise exceptions
        assert manager._sync_pool is not None
        assert manager._async_pool is not None
        manager._sync_pool.shutdown = MagicMock(side_effect=RuntimeError("Sync error"))
        manager._async_pool.shutdown = MagicMock(side_effect=ValueError("Async error"))

        # Act & Assert
        with pytest.raises(ExceptionGroup) as exc_info:
            await manager.shutdown(wait=True)

        # Should contain both exceptions
        assert len(exc_info.value.exceptions) == 2
        assert isinstance(exc_info.value.exceptions[0], RuntimeError)
        assert isinstance(exc_info.value.exceptions[1], ValueError)

    @pytest.mark.asyncio
    async def test_fallback_count_functions(self) -> None:
        """Test get_fallback_count() and increment_fallback_count()."""
        from asynctasq.tasks.infrastructure.process_pool_manager import (
            get_fallback_count,
            increment_fallback_count,
        )

        # Arrange - get initial count
        initial = get_fallback_count()

        # Act
        count1 = increment_fallback_count()
        count2 = increment_fallback_count()
        final = get_fallback_count()

        # Assert
        assert count1 == initial + 1
        assert count2 == initial + 2
        assert final == initial + 2

    @pytest.mark.asyncio
    async def test_get_warm_event_loop_returns_none_outside_process(self) -> None:
        """Test get_warm_event_loop() returns None outside process pool."""
        from asynctasq.tasks.infrastructure.process_pool_manager import get_warm_event_loop

        # Act
        loop = get_warm_event_loop()

        # Assert (should be None in main process, not in subprocess)
        assert loop is None

    @pytest.mark.asyncio
    async def test_get_default_manager_returns_singleton(self) -> None:
        """Test get_default_manager() returns same instance."""
        from asynctasq.tasks.infrastructure.process_pool_manager import get_default_manager

        # Act
        manager1 = get_default_manager()
        manager2 = get_default_manager()

        # Assert
        assert manager1 is manager2

    @pytest.mark.asyncio
    async def test_set_default_manager_replaces_instance(self) -> None:
        """Test set_default_manager() replaces default instance."""
        from asynctasq.tasks.infrastructure.process_pool_manager import (
            get_default_manager,
            set_default_manager,
        )

        # Arrange
        original = get_default_manager()
        custom = ProcessPoolManager(sync_max_workers=8)

        # Act
        set_default_manager(custom)
        new_default = get_default_manager()

        # Assert
        assert new_default is custom
        assert new_default is not original

        # Cleanup - restore original
        set_default_manager(original)

    @pytest.mark.asyncio
    async def test_get_cpu_count_returns_positive_int(self) -> None:
        """Test _get_cpu_count() returns positive integer."""
        # Arrange
        manager = ProcessPoolManager()

        # Act
        cpu_count = manager._get_cpu_count()

        # Assert
        assert isinstance(cpu_count, int)
        assert cpu_count > 0

    @pytest.mark.asyncio
    async def test_manager_with_custom_mp_context(self) -> None:
        """Test ProcessPoolManager with custom multiprocessing context."""
        import multiprocessing as mp

        # Arrange
        ctx = mp.get_context("spawn")  # Force spawn method
        manager = ProcessPoolManager(sync_max_workers=2, mp_context=ctx)

        # Act
        pool = manager.get_sync_pool()

        # Assert
        assert pool is not None
        assert manager.is_initialized()

    @pytest.mark.asyncio
    async def test_async_pool_has_separate_config(self) -> None:
        """Test async pool has independent configuration from sync pool."""
        # Arrange
        manager = ProcessPoolManager(
            sync_max_workers=2,
            async_max_workers=4,
            sync_max_tasks_per_child=50,
            async_max_tasks_per_child=100,
        )

        # Act
        manager.get_sync_pool()
        manager.get_async_pool()

        # Assert
        stats = manager.get_stats()
        assert stats["sync"]["pool_size"] == 2
        assert stats["async"]["pool_size"] == 4
        assert stats["sync"]["max_tasks_per_child"] == 50
        assert stats["async"]["max_tasks_per_child"] == 100

    @pytest.mark.asyncio
    async def test_get_stats_with_both_pools_initialized(self) -> None:
        """Test get_stats() with both sync and async pools initialized."""
        # Arrange
        manager = ProcessPoolManager(sync_max_workers=3, async_max_workers=5)
        manager.get_sync_pool()
        manager.get_async_pool()

        # Act
        stats = manager.get_stats()

        # Assert
        assert stats["sync"]["status"] == "initialized"
        assert stats["sync"]["pool_size"] == 3
        assert stats["async"]["status"] == "initialized"
        assert stats["async"]["pool_size"] == 5


@pytest.mark.unit
class TestProcessPoolManagerWarmEventLoop:
    """Test warm event loop initialization and cleanup."""

    @pytest.mark.asyncio
    async def test_cleanup_warm_event_loop_stops_loop(self) -> None:
        """Test _cleanup_warm_event_loop stops the event loop."""
        from unittest.mock import MagicMock

        # Mock process loop
        import asynctasq.tasks.infrastructure.process_pool_manager as ppm
        from asynctasq.tasks.infrastructure.process_pool_manager import (
            _cleanup_warm_event_loop,
        )

        original_loop = ppm._process_loop

        try:
            mock_loop = MagicMock()
            mock_loop.is_running.return_value = True
            mock_loop.is_closed.return_value = False
            mock_thread = MagicMock()
            mock_thread.is_alive.return_value = True

            ppm._process_loop = mock_loop
            ppm._loop_thread = mock_thread

            _cleanup_warm_event_loop()

            mock_loop.call_soon_threadsafe.assert_called_once()
            mock_thread.join.assert_called_once()
            mock_loop.close.assert_called_once()
        finally:
            ppm._process_loop = original_loop

    @pytest.mark.asyncio
    async def test_setup_subprocess_io_configures_signals(self) -> None:
        """Test _setup_subprocess_io sets up signal handlers."""
        import signal
        from unittest.mock import patch

        from asynctasq.tasks.infrastructure.process_pool_manager import _setup_subprocess_io

        with patch("signal.signal") as mock_signal:
            _setup_subprocess_io()

            # Should set SIGINT and SIGTERM handlers
            assert mock_signal.call_count >= 2
            signal_calls = [call[0][0] for call in mock_signal.call_args_list]
            assert signal.SIGINT in signal_calls
            assert signal.SIGTERM in signal_calls

    @pytest.mark.asyncio
    async def test_get_safe_mp_context_returns_spawn(self) -> None:
        """Test _get_safe_mp_context returns spawn context."""
        import multiprocessing

        from asynctasq.tasks.infrastructure.process_pool_manager import _get_safe_mp_context

        ctx = _get_safe_mp_context()
        # Verify it's a spawn context by checking it matches spawn context
        assert ctx == multiprocessing.get_context("spawn")
        from asynctasq.tasks.infrastructure.process_pool_manager import DEFAULT_MAX_TASKS_PER_CHILD

        assert DEFAULT_MAX_TASKS_PER_CHILD == 100
        assert isinstance(DEFAULT_MAX_TASKS_PER_CHILD, int)


@pytest.mark.unit
class TestProcessPoolManagerContextManager:
    """Test ProcessPoolManager async context manager functionality."""

    @pytest.mark.asyncio
    async def test_aenter_initializes_pools(self) -> None:
        """Test __aenter__ initializes the pools."""
        manager = ProcessPoolManager(sync_max_workers=2)

        async with manager as ctx_manager:
            assert ctx_manager is manager
            assert manager.is_initialized()

        # After exit, should be shut down
        assert not manager.is_initialized()

    @pytest.mark.asyncio
    async def test_aexit_handles_exceptions(self) -> None:
        """Test __aexit__ handles exceptions properly."""
        manager = ProcessPoolManager(sync_max_workers=2)

        try:
            async with manager:
                manager.get_sync_pool()
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Should still shut down despite exception
        assert not manager.is_initialized()

    @pytest.mark.asyncio
    async def test_aexit_with_none_exception_info(self) -> None:
        """Test __aexit__ with no exception."""
        manager = ProcessPoolManager(sync_max_workers=2)

        async with manager:
            manager.get_sync_pool()

        assert not manager.is_initialized()


@pytest.mark.unit
class TestProcessPoolManagerEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_double_initialization_is_idempotent(self) -> None:
        """Test calling initialize twice doesn't create duplicate pools."""
        manager = ProcessPoolManager(sync_max_workers=2)

        await manager.initialize()
        first_pool = manager._sync_pool

        await manager.initialize()  # Second call
        second_pool = manager._sync_pool

        # Should be the same pool instance
        assert first_pool is second_pool

    @pytest.mark.asyncio
    async def test_get_cpu_count_fallback(self) -> None:
        """Test _get_cpu_count handles os.cpu_count returning None."""
        from unittest.mock import patch

        manager = ProcessPoolManager()

        with patch("os.cpu_count", return_value=None):
            cpu_count = manager._get_cpu_count()
            assert cpu_count == 4  # Fallback value

    @pytest.mark.asyncio
    async def test_get_stats_with_none_max_tasks_per_child(self) -> None:
        """Test get_stats when max_tasks_per_child is None."""
        manager = ProcessPoolManager(sync_max_workers=2, sync_max_tasks_per_child=None)
        manager.get_sync_pool()

        stats = manager.get_stats()
        # When None, it uses DEFAULT_MAX_TASKS_PER_CHILD
        assert stats["sync"]["max_tasks_per_child"] == 100

    @pytest.mark.asyncio
    async def test_shutdown_twice_is_safe(self) -> None:
        """Test calling shutdown twice doesn't cause errors."""
        manager = ProcessPoolManager(sync_max_workers=2)
        manager.get_sync_pool()

        await manager.shutdown(wait=True)
        await manager.shutdown(wait=True)  # Second call

        # Should not raise error
        assert not manager.is_initialized()

    @pytest.mark.asyncio
    async def test_initialize_with_custom_mp_context(self) -> None:
        """Test initialize with custom multiprocessing context."""
        import multiprocessing as mp

        custom_ctx = mp.get_context("spawn")
        manager = ProcessPoolManager(sync_max_workers=2, mp_context=custom_ctx)

        await manager.initialize()

        assert manager.is_initialized()

    @pytest.mark.asyncio
    async def test_get_pool_after_shutdown_auto_reinitializes(self) -> None:
        """Test get_sync_pool after shutdown auto-reinitializes."""
        manager = ProcessPoolManager(sync_max_workers=2)
        manager.get_sync_pool()

        await manager.shutdown(wait=True)
        assert not manager.is_initialized()

        # Get pool again should auto-initialize
        pool = manager.get_sync_pool()
        assert pool is not None
        assert manager.is_initialized()


if __name__ == "__main__":
    main([__file__, "-s", "-m", "unit"])
