"""Unit tests for FastAPI integration.

Testing Strategy:
- Mock FastAPI and async context manager behavior
- Test lifespan context manager startup/shutdown
- Test dependency injection methods
- Test configuration options
"""

from unittest.mock import AsyncMock, MagicMock, patch

from pytest import fixture, mark, raises

from asynctasq.config import Config
from asynctasq.core.dispatcher import Dispatcher
from asynctasq.drivers.base_driver import BaseDriver
from asynctasq.drivers.redis_driver import RedisDriver
from asynctasq.integrations.fastapi import AsyncTasQIntegration


@fixture
def mock_driver() -> BaseDriver:
    """Create a mock driver for testing."""
    driver = MagicMock(spec=BaseDriver)
    driver.connect = AsyncMock()
    driver.disconnect = AsyncMock()
    return driver


@fixture
def mock_fastapi_app():
    """Create a mock FastAPI app for testing."""
    app = MagicMock()
    return app


class TestAsyncTasQIntegration:
    """Test AsyncTasQIntegration class."""

    @mark.asyncio
    async def test_init_with_config(self, mock_driver):
        """Test initialization with explicit config."""
        config = Config(driver="redis")
        integration = AsyncTasQIntegration(config=config)

        assert integration._config == config
        assert integration._driver is None
        assert integration._dispatcher is None
        assert not integration._initialized

    @mark.asyncio
    async def test_init_with_driver(self, mock_driver):
        """Test initialization with explicit driver."""
        integration = AsyncTasQIntegration(driver=mock_driver)

        assert integration._config is None
        assert integration._driver == mock_driver
        assert integration._dispatcher is None
        assert not integration._initialized

    @mark.asyncio
    async def test_init_without_args(self):
        """Test initialization without arguments (uses global config)."""
        integration = AsyncTasQIntegration()

        assert integration._config is None
        assert integration._driver is None
        assert integration._dispatcher is None
        assert not integration._initialized

    @mark.asyncio
    async def test_lifespan_startup_and_shutdown(self, mock_driver, mock_fastapi_app):
        """Test lifespan context manager startup and shutdown."""
        integration = AsyncTasQIntegration(driver=mock_driver)

        # Enter lifespan context (startup)
        async with integration.lifespan(mock_fastapi_app):
            # Verify startup
            assert integration._initialized
            assert integration._dispatcher is not None
            assert integration._dispatcher.driver == mock_driver
            mock_driver.connect.assert_called_once()

        # Verify shutdown
        assert not integration._initialized
        assert integration._dispatcher is None
        mock_driver.disconnect.assert_called_once()

    @mark.asyncio
    async def test_lifespan_with_config(self, mock_fastapi_app):
        """Test lifespan with config (creates driver from config)."""
        config = Config(driver="redis")
        integration = AsyncTasQIntegration(config=config)

        with patch("asynctasq.integrations.fastapi.DriverFactory.create") as mock_factory:
            mock_driver = RedisDriver()
            mock_factory.return_value = mock_driver

            async with integration.lifespan(mock_fastapi_app):
                assert integration._initialized
                assert integration._dispatcher is not None
                mock_factory.assert_called_once_with("redis", config)

    @mark.asyncio
    async def test_lifespan_without_config(self, mock_fastapi_app):
        """Test lifespan without config (uses global config)."""
        integration = AsyncTasQIntegration()

        with (
            patch("asynctasq.integrations.fastapi.Config.get") as mock_get_config,
            patch("asynctasq.integrations.fastapi.DriverFactory.create") as mock_factory,
        ):
            config = Config(driver="redis")
            mock_get_config.return_value = config
            mock_driver = RedisDriver()
            mock_factory.return_value = mock_driver

            async with integration.lifespan(mock_fastapi_app):
                assert integration._initialized
                # Config.get() may be called multiple times (lifespan + serializer creation)
                assert mock_get_config.call_count >= 1
                mock_factory.assert_called_once_with("redis", config)

    @mark.asyncio
    async def test_get_dispatcher_success(self, mock_driver, mock_fastapi_app):
        """Test get_dispatcher returns dispatcher after initialization."""
        integration = AsyncTasQIntegration(driver=mock_driver)

        async with integration.lifespan(mock_fastapi_app):
            dispatcher = integration.get_dispatcher()
            assert isinstance(dispatcher, Dispatcher)
            assert dispatcher.driver == mock_driver

    @mark.asyncio
    async def test_get_dispatcher_before_init(self):
        """Test get_dispatcher raises error before initialization."""
        integration = AsyncTasQIntegration()

        with raises(RuntimeError, match="not initialized"):
            integration.get_dispatcher()

    @mark.asyncio
    async def test_get_driver_success(self, mock_driver, mock_fastapi_app):
        """Test get_driver returns driver after initialization."""
        integration = AsyncTasQIntegration(driver=mock_driver)

        async with integration.lifespan(mock_fastapi_app):
            driver = integration.get_driver()
            assert driver == mock_driver

    @mark.asyncio
    async def test_get_driver_before_init(self):
        """Test get_driver raises error before initialization."""
        integration = AsyncTasQIntegration()

        with raises(RuntimeError, match="not initialized"):
            integration.get_driver()

    @mark.asyncio
    async def test_lifespan_idempotent_startup(self, mock_driver, mock_fastapi_app):
        """Test that startup is idempotent (can be called multiple times safely)."""
        integration = AsyncTasQIntegration(driver=mock_driver)

        async with integration.lifespan(mock_fastapi_app):
            # Call startup again (should be no-op)
            await integration._startup()
            await integration._startup()

            # Should only connect once
            assert mock_driver.connect.call_count == 1

    @mark.asyncio
    async def test_lifespan_idempotent_shutdown(self, mock_driver, mock_fastapi_app):
        """Test that shutdown is idempotent (can be called multiple times safely)."""
        integration = AsyncTasQIntegration(driver=mock_driver)

        async with integration.lifespan(mock_fastapi_app):
            pass

        # Call shutdown again (should be no-op)
        await integration._shutdown()
        await integration._shutdown()

        # Should only disconnect once
        assert mock_driver.disconnect.call_count == 1

    @mark.asyncio
    async def test_lifespan_exception_handling(self, mock_driver, mock_fastapi_app):
        """Test that shutdown is called even if exception occurs in lifespan."""
        integration = AsyncTasQIntegration(driver=mock_driver)

        with raises(ValueError):
            async with integration.lifespan(mock_fastapi_app):
                raise ValueError("Test exception")

        # Shutdown should still be called
        mock_driver.disconnect.assert_called_once()

    @mark.asyncio
    async def test_startup_failure_propagates_exception(self, mock_driver, mock_fastapi_app):
        """Test that startup failures propagate exceptions."""
        mock_driver.connect.side_effect = ConnectionError("Connection failed")
        integration = AsyncTasQIntegration(driver=mock_driver)

        with raises(ConnectionError, match="Connection failed"):
            async with integration.lifespan(mock_fastapi_app):
                pass

    @mark.asyncio
    async def test_shutdown_error_logged_not_raised(self, mock_driver, mock_fastapi_app):
        """Test that shutdown errors are logged but not raised."""
        mock_driver.disconnect.side_effect = Exception("Disconnect error")
        integration = AsyncTasQIntegration(driver=mock_driver)

        # Should not raise exception
        async with integration.lifespan(mock_fastapi_app):
            pass

        # Disconnect should have been called
        mock_driver.disconnect.assert_called_once()

    @mark.asyncio
    async def test_lifespan_driver_priority_over_config(self, mock_driver, mock_fastapi_app):
        """Test that provided driver takes precedence over config."""
        config = Config(driver="redis")
        integration = AsyncTasQIntegration(config=config, driver=mock_driver)

        with patch("asynctasq.integrations.fastapi.DriverFactory.create") as mock_factory:
            async with integration.lifespan(mock_fastapi_app):
                # Factory should not be called since driver was provided
                mock_factory.assert_not_called()
                assert integration._dispatcher is not None
                assert integration._dispatcher.driver == mock_driver

    @mark.asyncio
    async def test_get_dispatcher_type_hint(self, mock_driver, mock_fastapi_app):
        """Test get_dispatcher returns correct type."""
        integration = AsyncTasQIntegration(driver=mock_driver)

        async with integration.lifespan(mock_fastapi_app):
            dispatcher = integration.get_dispatcher()
            # Type check
            assert isinstance(dispatcher, Dispatcher)

    @mark.asyncio
    async def test_get_driver_type_hint(self, mock_driver, mock_fastapi_app):
        """Test get_driver returns correct type."""
        integration = AsyncTasQIntegration(driver=mock_driver)

        async with integration.lifespan(mock_fastapi_app):
            driver = integration.get_driver()
            # Type check
            assert isinstance(driver, BaseDriver)

    @mark.asyncio
    async def test_multiple_lifespan_contexts_sequential(self, mock_driver, mock_fastapi_app):
        """Test using lifespan multiple times sequentially."""
        integration = AsyncTasQIntegration(driver=mock_driver)

        # First lifespan
        async with integration.lifespan(mock_fastapi_app):
            assert integration._initialized
            dispatcher1 = integration.get_dispatcher()

        assert not integration._initialized

        # Reset mock call counts
        mock_driver.connect.reset_mock()
        mock_driver.disconnect.reset_mock()

        # Second lifespan - should work again
        async with integration.lifespan(mock_fastapi_app):
            assert integration._initialized
            dispatcher2 = integration.get_dispatcher()
            # Should be different instances
            assert dispatcher2 is not dispatcher1

        mock_driver.connect.assert_called_once()
        mock_driver.disconnect.assert_called_once()

    @mark.asyncio
    async def test_integration_with_custom_driver_instance(self, mock_fastapi_app):
        """Test integration with custom driver instance."""
        custom_driver = MagicMock(spec=BaseDriver)
        custom_driver.connect = AsyncMock()
        custom_driver.disconnect = AsyncMock()

        integration = AsyncTasQIntegration(driver=custom_driver)

        async with integration.lifespan(mock_fastapi_app):
            assert integration._dispatcher is not None
            assert integration._dispatcher.driver == custom_driver

        custom_driver.connect.assert_called_once()
        custom_driver.disconnect.assert_called_once()

    @mark.asyncio
    async def test_lifespan_logging(self, mock_driver, mock_fastapi_app):
        """Test that lifespan logs startup and shutdown."""
        integration = AsyncTasQIntegration(driver=mock_driver)

        with patch("asynctasq.integrations.fastapi.logger") as mock_logger:
            async with integration.lifespan(mock_fastapi_app):
                pass

            # Check that info logs were called
            assert mock_logger.info.call_count >= 2

    @mark.asyncio
    async def test_get_dispatcher_error_message_clarity(self):
        """Test get_dispatcher error message is helpful."""
        integration = AsyncTasQIntegration()

        with raises(RuntimeError) as exc_info:
            integration.get_dispatcher()

        assert "not initialized" in str(exc_info.value)
        assert "lifespan" in str(exc_info.value).lower()

    @mark.asyncio
    async def test_get_driver_error_message_clarity(self):
        """Test get_driver error message is helpful."""
        integration = AsyncTasQIntegration()

        with raises(RuntimeError) as exc_info:
            integration.get_driver()

        assert "not initialized" in str(exc_info.value)
        assert "lifespan" in str(exc_info.value).lower()

    @mark.asyncio
    async def test_config_factory_interaction(self, mock_fastapi_app):
        """Test config is properly passed to DriverFactory."""
        config = Config(driver="redis")
        integration = AsyncTasQIntegration(config=config)

        with patch("asynctasq.integrations.fastapi.DriverFactory.create") as mock_factory:
            mock_driver = MagicMock(spec=BaseDriver)
            mock_driver.connect = AsyncMock()
            mock_driver.disconnect = AsyncMock()
            mock_factory.return_value = mock_driver

            async with integration.lifespan(mock_fastapi_app):
                # Verify factory was called with correct config
                mock_factory.assert_called_once_with("redis", config)

    @mark.asyncio
    async def test_shutdown_with_none_dispatcher(self):
        """Test shutdown handles None dispatcher gracefully."""
        integration = AsyncTasQIntegration()

        # Call shutdown directly without initialization
        await integration._shutdown()

        # Should not raise exception
        assert not integration._initialized
