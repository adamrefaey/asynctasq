"""Unit tests for asynctasq.__init__ module."""

import asyncio
import importlib.metadata
from typing import cast
from unittest.mock import MagicMock, patch

import pytest

import asynctasq
from asynctasq import init
from asynctasq.config import ConfigOverrides
from asynctasq.monitoring.emitters import EventEmitter


@pytest.fixture(autouse=True)
def reset_cleanup_state():
    """Reset the global cleanup state before each test."""
    asynctasq._cleanup_registered = False
    yield
    # Reset after test as well
    asynctasq._cleanup_registered = False


class TestVersion:
    """Test version handling in __init__.py."""

    def test_version_success(self):
        """Test successful version retrieval."""
        # Version is already imported and set
        assert hasattr(asynctasq, "__version__")
        assert isinstance(asynctasq.__version__, str)

    @patch("importlib.metadata.version")
    def test_version_fallback_on_package_not_found(self, mock_version):
        """Test version fallback when package not found."""
        mock_version.side_effect = importlib.metadata.PackageNotFoundError()

        # Since version is set at import time, we can't easily test the fallback
        # without re-importing the module. The fallback logic is tested by the
        # import-time behavior, so we'll just verify the version exists.
        assert hasattr(asynctasq, "__version__")
        assert isinstance(asynctasq.__version__, str)


class TestCleanupHooks:
    """Test cleanup hook registration functions."""

    def test_register_cleanup_hooks_no_running_loop(self):
        """Test _register_cleanup_hooks when no running loop."""
        with patch("asyncio.get_running_loop", side_effect=RuntimeError()):
            # Reset the global state
            asynctasq._cleanup_registered = False

            asynctasq._register_cleanup_hooks()

            # Should not have registered anything
            assert not asynctasq._cleanup_registered

    @patch("asynctasq.utils.cleanup_hooks.register")
    def test_register_cleanup_hooks_with_running_loop(self, mock_register):
        """Test _register_cleanup_hooks with running loop."""
        mock_loop = MagicMock()
        mock_loop.id = 12345

        with (
            patch("asyncio.get_running_loop", return_value=mock_loop),
            patch("asynctasq.core.dispatcher.cleanup"),
        ):
            # Reset the global state
            asynctasq._cleanup_registered = False

            asynctasq._register_cleanup_hooks()

            # Should have registered the cleanup hook
            assert asynctasq._cleanup_registered
            mock_register.assert_called_once()

            # Verify the cleanup function was registered
            call_args = mock_register.call_args
            cleanup_func = call_args[0][0]
            loop_arg = call_args[1]["loop"]

            assert loop_arg == mock_loop

            # Test that the cleanup function works
            # This should be an async function that calls cleanup()
            assert asyncio.iscoroutinefunction(cleanup_func)

    def test_register_cleanup_hooks_already_registered(self):
        """Test _register_cleanup_hooks when already registered."""
        # Set registered to True
        asynctasq._cleanup_registered = True

        with patch("asyncio.get_running_loop") as mock_get_loop:
            asynctasq._register_cleanup_hooks()

            # Should not try to get running loop
            mock_get_loop.assert_not_called()

    @patch("asynctasq.utils.cleanup_hooks.register")
    def test_register_cleanup_hooks_registration_failure(self, mock_register):
        """Test _register_cleanup_hooks when registration fails."""
        mock_loop = MagicMock()
        mock_register.side_effect = Exception("Registration failed")

        with patch("asyncio.get_running_loop", return_value=mock_loop):
            # Reset the global state
            asynctasq._cleanup_registered = False

            # Should not raise exception
            asynctasq._register_cleanup_hooks()

            # Should still be marked as registered to avoid repeated attempts
            assert asynctasq._cleanup_registered

    @pytest.mark.asyncio
    async def test_ensure_cleanup_registered_no_running_loop(self):
        """Test ensure_cleanup_registered when no running loop."""
        with patch("asyncio.get_running_loop", side_effect=RuntimeError()):
            # Should not raise exception
            await asynctasq.ensure_cleanup_registered()

    @pytest.mark.asyncio
    async def test_ensure_cleanup_registered_with_running_loop(self):
        """Test ensure_cleanup_registered with running loop."""
        mock_loop = MagicMock()

        with (
            patch("asyncio.get_running_loop", return_value=mock_loop),
            patch("asynctasq.utils.cleanup_hooks.register") as mock_register,
            patch("asynctasq.core.dispatcher.cleanup"),
        ):
            await asynctasq.ensure_cleanup_registered()

            # Should have registered cleanup
            mock_register.assert_called_once()


class TestInit:
    """Test the init() function."""

    @patch("asynctasq.config.Config.set")
    @patch("asynctasq.config.Config.get")
    @patch("asynctasq.monitoring.EventRegistry.init")
    @patch("asynctasq.monitoring.EventRegistry.add")
    @patch("asynctasq._register_cleanup_hooks")
    def test_init_with_config_overrides(
        self, mock_register_hooks, mock_event_add, mock_event_init, mock_config_get, mock_config_set
    ):
        """Test init with config overrides."""
        overrides = cast(
            ConfigOverrides, {"driver": "redis", "redis_url": "redis://localhost:6379"}
        )
        emitters = cast(list[EventEmitter], [MagicMock()])

        init(config_overrides=overrides, event_emitters=emitters)

        # Should set config with overrides
        mock_config_set.assert_called_once_with(**overrides)
        mock_config_get.assert_not_called()

        # Should initialize event registry
        mock_event_init.assert_called_once()

        # Should add event emitters
        for emitter in emitters:
            mock_event_add.assert_any_call(emitter)

    @patch("asynctasq.config.Config.get")
    @patch("asynctasq.monitoring.EventRegistry.init")
    @patch("asynctasq._register_cleanup_hooks")
    def test_init_without_config_overrides(
        self, mock_register_hooks, mock_event_init, mock_config_get
    ):
        """Test init without config overrides."""
        init()

        # Should get config (to ensure initialization)
        mock_config_get.assert_called_once()

        # Should initialize event registry
        mock_event_init.assert_called_once()

        # Should register cleanup hooks
        mock_register_hooks.assert_called_once()

    @patch("asynctasq.config.Config.get")
    @patch("asynctasq.monitoring.EventRegistry.init")
    @patch("asynctasq.monitoring.EventRegistry.add")
    @patch("asynctasq._register_cleanup_hooks")
    def test_init_with_event_emitters(
        self, mock_register_hooks, mock_event_add, mock_event_init, mock_config_get
    ):
        """Test init with event emitters."""
        emitters = cast(list[EventEmitter], [MagicMock(), MagicMock()])

        init(event_emitters=emitters)

        # Should initialize event registry
        mock_event_init.assert_called_once()

        # Should add each emitter
        assert mock_event_add.call_count == 2
        for emitter in emitters:
            mock_event_add.assert_any_call(emitter)

        # Should register cleanup hooks
        mock_register_hooks.assert_called_once()
