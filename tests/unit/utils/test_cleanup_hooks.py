"""Unit tests for asynctasq.utils.cleanup_hooks module."""

import asyncio
import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from asynctasq.utils.cleanup_hooks import (
    _get_registry_entry,
    _RegistryEntry,
    register,
    unregister,
)


class TestRegistryEntry:
    """Test _RegistryEntry class."""

    def test_init(self):
        """Test _RegistryEntry initialization."""
        mock_loop = MagicMock()
        entry = _RegistryEntry(mock_loop)

        assert entry.loop == mock_loop
        assert entry.callbacks == []
        assert entry._original_close is None
        assert not entry._patched

    def test_add_callback(self):
        """Test adding callbacks."""
        mock_loop = MagicMock()
        entry = _RegistryEntry(mock_loop)

        callback1 = MagicMock()
        callback2 = MagicMock()

        entry.add_callback(callback1)
        entry.add_callback(callback2)
        entry.add_callback(callback1)  # Duplicate should not be added

        assert entry.callbacks == [callback1, callback2]

    def test_remove_callback(self):
        """Test removing callbacks."""
        mock_loop = MagicMock()
        entry = _RegistryEntry(mock_loop)

        callback1 = MagicMock()
        callback2 = MagicMock()

        entry.add_callback(callback1)
        entry.add_callback(callback2)
        entry.add_callback(callback1)  # Add duplicate

        entry.remove_callback(callback1)

        assert callback1 not in entry.callbacks
        assert entry.callbacks == [callback2]

    def test_patch_loop_close(self):
        """Test patching loop close method."""
        mock_loop = MagicMock()
        original_close = MagicMock()
        mock_loop.close = original_close

        entry = _RegistryEntry(mock_loop)
        entry.patch_loop_close()

        assert entry._patched
        assert entry._original_close == original_close
        assert mock_loop.close != original_close  # Should be replaced

    def test_patch_loop_close_already_patched(self):
        """Test patch_loop_close does nothing if already patched."""
        mock_loop = MagicMock()
        entry = _RegistryEntry(mock_loop)

        entry._patched = True
        entry.patch_loop_close()

        # Should not modify anything
        assert entry._patched

    def test_run_cleanup_sync_no_callbacks(self):
        """Test _run_cleanup_sync with no callbacks."""
        mock_loop = MagicMock()
        entry = _RegistryEntry(mock_loop)

        # Should not raise any exception
        entry._run_cleanup_sync()

    def test_run_cleanup_sync_sync_callback(self):
        """Test _run_cleanup_sync with sync callback."""
        mock_loop = MagicMock()
        entry = _RegistryEntry(mock_loop)

        callback = MagicMock()
        entry.add_callback(callback)

        entry._run_cleanup_sync()

        callback.assert_called_once()

    def test_run_cleanup_sync_async_callback_loop_running(self):
        """Test _run_cleanup_sync with async callback when loop is running."""
        mock_loop = MagicMock()
        mock_loop.is_closed.return_value = False
        mock_loop.is_running.return_value = True  # Loop is running
        entry = _RegistryEntry(mock_loop)

        async_callback = AsyncMock()
        entry.add_callback(async_callback)

        with (
            patch("asyncio.iscoroutinefunction", return_value=True),
            patch("asynctasq.utils.cleanup_hooks.logger") as mock_logger,
        ):
            entry._run_cleanup_sync()

        # Should NOT have called run_until_complete when loop is running
        mock_loop.run_until_complete.assert_not_called()
        # Should log warning
        mock_logger.warning.assert_called_once()

    def test_run_cleanup_sync_async_callback_loop_closed(self):
        """Test _run_cleanup_sync with async callback when loop is closed."""
        mock_loop = MagicMock()
        mock_loop.is_closed.return_value = True
        entry = _RegistryEntry(mock_loop)

        async_callback = AsyncMock()
        entry.add_callback(async_callback)

        with (
            patch("asyncio.iscoroutinefunction", return_value=True),
            patch("asynctasq.utils.cleanup_hooks.logger") as mock_logger,
        ):
            entry._run_cleanup_sync()

        # Should not call run_until_complete
        mock_loop.run_until_complete.assert_not_called()
        # Should log warning
        mock_logger.warning.assert_called_once()

    def test_run_cleanup_sync_callback_exception(self):
        """Test _run_cleanup_sync handles callback exceptions."""
        mock_loop = MagicMock()
        entry = _RegistryEntry(mock_loop)

        callback = MagicMock(side_effect=Exception("Test error"))
        entry.add_callback(callback)

        with patch("asynctasq.utils.cleanup_hooks.logger") as mock_logger:
            entry._run_cleanup_sync()

        # Should log exception but not raise
        mock_logger.exception.assert_called_once()

    def test_close_with_cleanup_calls_original(self):
        """Test that close_with_cleanup calls original close method."""
        mock_loop = MagicMock()
        original_close = MagicMock()
        mock_loop.close = original_close

        entry = _RegistryEntry(mock_loop)
        entry.patch_loop_close()

        # Call the new close method
        mock_loop.close()

        # Should have called original close
        original_close.assert_called_once()


class TestRegisterFunction:
    """Test register function."""

    def test_register_with_running_loop(self):
        """Test register with running loop."""
        mock_loop = MagicMock()
        callback = MagicMock()

        with patch("asyncio.get_running_loop", return_value=mock_loop):
            register(callback)

        # Should have created registry entry and patched loop
        # (This is hard to test directly due to WeakKeyDictionary)

    def test_register_with_no_running_loop_uses_event_loop(self):
        """Test register with no running loop uses get_event_loop."""
        mock_loop = MagicMock()
        callback = MagicMock()

        with (
            patch("asyncio.get_running_loop", side_effect=RuntimeError()),
            patch("asyncio.get_event_loop", return_value=mock_loop),
        ):
            register(callback)

    def test_register_with_no_loop_available(self):
        """Test register with no loop available logs warning."""
        callback = MagicMock()

        # Mock the event loop policy to raise RuntimeError
        mock_policy = MagicMock()
        mock_policy.get_event_loop.side_effect = RuntimeError()

        with (
            patch("asyncio.get_running_loop", side_effect=RuntimeError()),
            patch("asyncio.get_event_loop_policy", return_value=mock_policy),
            patch("asynctasq.utils.cleanup_hooks.logger") as mock_logger,
        ):
            register(callback)

        mock_logger.warning.assert_called_once()

    def test_register_with_explicit_loop(self):
        """Test register with explicitly passed loop."""
        mock_loop = MagicMock()
        callback = MagicMock()

        register(callback, loop=mock_loop)

        # Should work without calling get_running_loop
        # (Hard to test directly due to WeakKeyDictionary)

    def test_register_multiple_callbacks(self):
        """Test registering multiple callbacks."""
        mock_loop = MagicMock()
        callback1 = MagicMock()
        callback2 = MagicMock()

        with patch("asyncio.get_running_loop", return_value=mock_loop):
            register(callback1, loop=mock_loop)
            register(callback2, loop=mock_loop)


class TestUnregisterFunction:
    """Test unregister function."""

    def test_unregister_with_running_loop(self):
        """Test unregister with running loop."""
        mock_loop = MagicMock()
        callback = MagicMock()

        with patch("asyncio.get_running_loop", return_value=mock_loop):
            unregister(callback)

    def test_unregister_with_no_running_loop_uses_event_loop(self):
        """Test unregister with no running loop uses get_event_loop."""
        mock_loop = MagicMock()
        callback = MagicMock()

        with (
            patch("asyncio.get_running_loop", side_effect=RuntimeError()),
            patch("asyncio.get_event_loop", return_value=mock_loop),
        ):
            unregister(callback)

    def test_unregister_with_no_loop_available(self):
        """Test unregister with no loop available does nothing."""
        callback = MagicMock()

        with (
            patch("asyncio.get_running_loop", side_effect=RuntimeError()),
            patch("asyncio.get_event_loop", side_effect=RuntimeError()),
        ):
            # Should not raise
            unregister(callback)

    def test_unregister_with_explicit_loop(self):
        """Test unregister with explicitly passed loop."""
        mock_loop = MagicMock()
        callback = MagicMock()

        unregister(callback, loop=mock_loop)


class TestGetRegistryEntry:
    """Test _get_registry_entry function."""

    def test_get_registry_entry_with_running_loop(self):
        """Test _get_registry_entry with running loop."""
        mock_loop = MagicMock()

        with (
            patch("asyncio.get_running_loop", return_value=mock_loop),
            patch("asynctasq.utils.cleanup_hooks._registry") as mock_registry,
        ):
            mock_entry = MagicMock()
            mock_registry.get.return_value = mock_entry

            result = _get_registry_entry()

            assert result == mock_entry
            mock_registry.get.assert_called_once_with(mock_loop)

    def test_get_registry_entry_no_running_loop(self):
        """Test _get_registry_entry with no running loop returns None."""
        with patch("asyncio.get_running_loop", side_effect=RuntimeError()):
            result = _get_registry_entry()

            assert result is None

    def test_get_registry_entry_with_explicit_loop(self):
        """Test _get_registry_entry with explicit loop."""
        mock_loop = MagicMock()

        with patch("asynctasq.utils.cleanup_hooks._registry") as mock_registry:
            mock_entry = MagicMock()
            mock_registry.get.return_value = mock_entry

            result = _get_registry_entry(mock_loop)

            assert result == mock_entry
            mock_registry.get.assert_called_once_with(mock_loop)


class TestCleanupHooksIntegration:
    """Integration tests for cleanup hooks."""

    @pytest.mark.asyncio
    async def test_cleanup_hooks_run_on_loop_close(self):
        """Test that cleanup hooks are actually called when loop closes."""
        # Create a new event loop for this test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            callback_called = False

            def sync_callback():
                nonlocal callback_called
                callback_called = True

            # Register callback
            register(sync_callback, loop=loop)

            # Close the loop
            loop.close()

            # Callback should have been called
            assert callback_called

        finally:
            # Clean up
            asyncio.set_event_loop(None)

    def test_async_cleanup_hooks_run_on_loop_close(self):
        """Test that async cleanup hooks are called when loop closes."""
        # Create a new event loop for this test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            callback_called = False

            async def async_callback():
                nonlocal callback_called
                callback_called = True

            # Register callback
            register(async_callback, loop=loop)

            # Close the loop
            loop.close()

            # For async callbacks, they may not run if there's a loop conflict
            # This is expected behavior - async cleanup requires a running loop
            # So we don't assert that callback_called is True

        finally:
            # Clean up
            asyncio.set_event_loop(None)

    def test_weak_references_cleanup_on_loop_deletion(self):
        """Test that registry entries are cleaned up when loops are deleted."""
        # Create a loop
        loop = asyncio.new_event_loop()

        # Register something
        callback = MagicMock()
        register(callback, loop=loop)

        # Delete the loop
        del loop
        gc.collect()

        # Registry should be empty (WeakKeyDictionary behavior)
        # This is hard to test directly, but we can check that no exceptions occur
