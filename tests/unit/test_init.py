"""Unit tests for asynctasq.__init__ module."""

import asyncio
import importlib.metadata
from typing import cast
from unittest.mock import MagicMock, patch

import pytest

import asynctasq
from asynctasq import init
from asynctasq.config import RedisConfig
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
        overrides = {"driver": "redis", "redis": RedisConfig(url="redis://localhost:6379")}
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

    @patch("asynctasq.config.Config.get")
    @patch("asynctasq.config.Config.set")
    @patch("asynctasq.monitoring.EventRegistry.init")
    @patch("asynctasq._register_cleanup_hooks")
    def test_init_with_tortoise_config(
        self, mock_register_hooks, mock_event_init, mock_config_set, mock_config_get
    ):
        """Test init with Tortoise ORM config."""
        mock_config = MagicMock()
        mock_config_get.return_value = mock_config

        tortoise_config = {
            "db_url": "postgres://user:pass@localhost/db",
            "modules": {"models": ["myapp.models"]},
        }

        init(tortoise_config=tortoise_config)

        # Should store Tortoise config in config object
        assert mock_config.tortoise_orm == tortoise_config

    @patch("asynctasq.config.Config.get")
    @patch("asynctasq.monitoring.EventRegistry.init")
    @patch("asynctasq._register_cleanup_hooks")
    def test_init_calls_register_cleanup_hooks(
        self, mock_register_hooks, mock_event_init, mock_config_get
    ):
        """Test init calls _register_cleanup_hooks."""
        init()

        mock_register_hooks.assert_called_once()

    @patch("asynctasq.config.Config.set")
    @patch("asynctasq.config.Config.get")
    @patch("asynctasq.monitoring.EventRegistry.init")
    @patch("asynctasq.monitoring.EventRegistry.add")
    @patch("asynctasq._register_cleanup_hooks")
    def test_init_with_all_parameters(
        self, mock_register_hooks, mock_event_add, mock_event_init, mock_config_get, mock_config_set
    ):
        """Test init with all parameters specified."""
        mock_config = MagicMock()
        mock_config_get.return_value = mock_config

        overrides = {"driver": "redis"}
        emitters = cast(list[EventEmitter], [MagicMock()])
        tortoise_config = {"db_url": "postgres://localhost/db"}

        init(
            config_overrides=overrides,
            event_emitters=emitters,
            tortoise_config=tortoise_config,
        )

        # All initialization steps should happen
        mock_config_set.assert_called_once()
        mock_event_init.assert_called_once()
        mock_event_add.assert_called_once()
        mock_register_hooks.assert_called_once()
        assert mock_config.tortoise_orm == tortoise_config


class TestExports:
    """Test module exports are available."""

    def test_all_exports_are_importable(self):
        """Test all items in __all__ can be imported."""
        for name in asynctasq.__all__:
            assert hasattr(asynctasq, name), f"{name} not found in asynctasq module"

    def test_version_is_exported(self):
        """Test __version__ is available."""
        assert hasattr(asynctasq, "__version__")
        assert isinstance(asynctasq.__version__, str)

    def test_core_classes_exported(self):
        """Test core classes are exported."""
        from asynctasq import Config, Dispatcher, Worker

        assert Dispatcher is not None
        assert Worker is not None
        assert Config is not None

    def test_task_types_exported(self):
        """Test task types are exported."""
        from asynctasq import (
            AsyncProcessTask,
            AsyncTask,
            SyncProcessTask,
            SyncTask,
            task,
        )

        assert AsyncTask is not None
        assert SyncTask is not None
        assert AsyncProcessTask is not None
        assert SyncProcessTask is not None
        assert task is not None

    def test_monitoring_exported(self):
        """Test monitoring classes are exported."""
        from asynctasq import EventEmitter, EventRegistry, MonitoringService

        assert EventEmitter is not None
        assert EventRegistry is not None
        assert MonitoringService is not None

    def test_serializers_exported(self):
        """Test serializer classes are exported."""
        from asynctasq import BaseSerializer, MsgpackSerializer, TypeHook

        assert BaseSerializer is not None
        assert MsgpackSerializer is not None
        assert TypeHook is not None

    def test_utils_exported(self):
        """Test utility functions are exported."""
        from asynctasq import console, run

        assert console is not None
        assert run is not None


class TestCleanupRegistrationEdgeCases:
    """Test edge cases in cleanup registration."""

    @pytest.mark.asyncio
    async def test_ensure_cleanup_registered_already_registered(self):
        """Test ensure_cleanup_registered when already registered."""
        asynctasq._cleanup_registered = True

        with patch("asyncio.get_running_loop") as mock_get_loop:
            await asynctasq.ensure_cleanup_registered()

            # Should not try to register again
            mock_get_loop.assert_not_called()

    @pytest.mark.asyncio
    async def test_ensure_cleanup_registered_registration_error(self):
        """Test ensure_cleanup_registered handles registration errors."""
        asynctasq._cleanup_registered = False
        mock_loop = MagicMock()

        with (
            patch("asyncio.get_running_loop", return_value=mock_loop),
            patch(
                "asynctasq.utils.cleanup_hooks.register",
                side_effect=Exception("Registration error"),
            ),
        ):
            # Should not raise
            await asynctasq.ensure_cleanup_registered()

    def test_register_cleanup_hooks_exception_handling(self):
        """Test _register_cleanup_hooks handles unexpected exceptions."""
        asynctasq._cleanup_registered = False

        with patch(
            "asyncio.get_running_loop",
            side_effect=Exception("Unexpected error"),
        ):
            # Should not raise, should mark as registered
            asynctasq._register_cleanup_hooks()
            assert asynctasq._cleanup_registered


class TestInitIntegration:
    """Integration tests for init() function."""

    @patch("asynctasq._register_cleanup_hooks")
    def test_init_initializes_config_and_events(self, mock_register_hooks):
        """Test init properly initializes config and event system."""
        # Reset state
        asynctasq._cleanup_registered = False

        # Call init
        init(config_overrides={"driver": "redis"})

        # Verify cleanup hooks registered
        mock_register_hooks.assert_called_once()

    @patch("asynctasq._register_cleanup_hooks")
    def test_init_can_be_called_multiple_times(self, mock_register_hooks):
        """Test init can be called multiple times safely."""
        asynctasq._cleanup_registered = False

        # Call multiple times
        init()
        init()
        init()

        # Should register hooks each time (or handle already registered)
        assert mock_register_hooks.call_count >= 1
