"""Unit tests for Tortoise ORM hook.

Testing Strategy:
- pytest 9.0.1 with asyncio_mode="strict" (explicit @mark.asyncio decorators required)
- AAA pattern (Arrange, Act, Assert)
- Mock Tortoise models to avoid requiring actual Tortoise ORM installation
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from pytest import fixture, mark, raises

from asynctasq.serializers.hooks import TortoiseOrmHook

# =============================================================================
# Mock Tortoise Model
# =============================================================================


class MockTortoiseModel:
    """Mock Tortoise ORM model for testing."""

    def __init__(self, pk: Any = 1):
        self.pk = pk
        self.__class__.__module__ = "test_module"
        self.__class__.__name__ = "MockTortoiseModel"


# =============================================================================
# Test TortoiseOrmHook
# =============================================================================


@mark.unit
class TestTortoiseOrmHook:
    """Test Tortoise ORM hook."""

    @fixture
    def hook(self) -> TortoiseOrmHook:
        return TortoiseOrmHook()

    def test_orm_name(self, hook: TortoiseOrmHook) -> None:
        """Test orm_name is tortoise."""
        assert hook.orm_name == "tortoise"

    def test_type_key(self, hook: TortoiseOrmHook) -> None:
        """Test type_key is correct."""
        assert hook.type_key == "__orm:tortoise__"

    def test_priority(self, hook: TortoiseOrmHook) -> None:
        """Test priority is high (100)."""
        assert hook.priority == 100

    @patch("asynctasq.serializers.hooks.orm.tortoise.TORTOISE_AVAILABLE", False)
    def test_can_encode_when_tortoise_not_available(self) -> None:
        """Test can_encode returns False when Tortoise not installed."""
        hook = TortoiseOrmHook()
        obj = MockTortoiseModel()
        assert hook.can_encode(obj) is False

    @patch("asynctasq.serializers.hooks.orm.tortoise.TORTOISE_AVAILABLE", True)
    @patch("asynctasq.serializers.hooks.orm.tortoise.TortoiseModel", None)
    def test_can_encode_when_tortoise_model_is_none(self) -> None:
        """Test can_encode returns False when TortoiseModel is None."""
        hook = TortoiseOrmHook()
        obj = MockTortoiseModel()
        assert hook.can_encode(obj) is False

    @patch("asynctasq.serializers.hooks.orm.tortoise.TORTOISE_AVAILABLE", True)
    @patch("asynctasq.serializers.hooks.orm.tortoise.TortoiseModel")
    def test_can_encode_when_isinstance_raises_exception(self, mock_tortoise_model) -> None:
        """Test can_encode returns False when isinstance raises exception."""
        # Make isinstance raise an exception
        mock_tortoise_model.__class__.__instancecheck__ = MagicMock(
            side_effect=Exception("isinstance error")
        )
        hook = TortoiseOrmHook()
        obj = MockTortoiseModel()
        assert hook.can_encode(obj) is False
        """Test _get_model_pk extracts pk from Tortoise model."""
        obj = MockTortoiseModel(pk=42)
        result = hook._get_model_pk(obj)
        assert result == 42

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.tortoise.TORTOISE_AVAILABLE", False)
    async def test_fetch_model_raises_when_not_available(self) -> None:
        """Test _fetch_model raises ImportError when Tortoise not installed."""
        hook = TortoiseOrmHook()
        with raises(ImportError, match="Tortoise ORM is not installed"):
            await hook._fetch_model(MagicMock, 1)

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.tortoise.TORTOISE_AVAILABLE", True)
    async def test_fetch_model(self) -> None:
        """Test _fetch_model fetches Tortoise model."""
        hook = TortoiseOrmHook()

        mock_model = MagicMock()
        model_class = MagicMock()
        model_class.get = AsyncMock(return_value=mock_model)

        # Mock Tortoise._inited to True so we bypass the initialization check
        # Patch where it's imported (inside the function)
        with patch("tortoise.Tortoise") as mock_tortoise:
            mock_tortoise._inited = True
            result = await hook._fetch_model(model_class, 42)
            assert result == mock_model
            model_class.get.assert_called_once_with(pk=42)

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.tortoise.TORTOISE_AVAILABLE", True)
    async def test_fetch_model_not_initialized(self) -> None:
        """Test _fetch_model returns LazyOrmProxy when Tortoise not initialized."""
        from asynctasq.serializers.hooks.orm.lazy_proxy import LazyOrmProxy

        hook = TortoiseOrmHook()

        model_class = MagicMock()
        model_class.__name__ = "Product"

        # Mock Tortoise._inited to False - should return lazy proxy
        with patch("tortoise.Tortoise") as mock_tortoise:
            mock_tortoise._inited = False
            result = await hook._fetch_model(model_class, 42)

            # Should return a lazy proxy instead of raising
            assert isinstance(result, LazyOrmProxy)
            assert result._model_class == model_class
            assert result._pk == 42

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.tortoise.TORTOISE_AVAILABLE", True)
    async def test_fetch_model_with_exception(self) -> None:
        """Test _fetch_model propagates exceptions from Tortoise get()."""
        hook = TortoiseOrmHook()

        model_class = MagicMock()
        model_class.get = AsyncMock(side_effect=RuntimeError("Database error"))

        # Mock Tortoise as initialized
        with patch("tortoise.Tortoise") as mock_tortoise:
            mock_tortoise._inited = True
            with raises(RuntimeError, match="Database error"):
                await hook._fetch_model(model_class, 42)

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.tortoise.TORTOISE_AVAILABLE", True)
    async def test_fetch_model_immediate_not_initialized(self) -> None:
        """Test _fetch_model_immediate raises error when Tortoise still not initialized."""
        hook = TortoiseOrmHook()

        model_class = MagicMock()
        model_class.__name__ = "Product"

        # Mock Tortoise._inited to False
        with patch("tortoise.Tortoise") as mock_tortoise:
            mock_tortoise._inited = False
            with raises(
                RuntimeError,
                match="Tortoise ORM is not initialized. Cannot fetch Product instance",
            ):
                await hook._fetch_model_immediate(model_class, 42)

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.tortoise.TORTOISE_AVAILABLE", True)
    async def test_lazy_proxy_resolution(self) -> None:
        """Test that LazyOrmProxy resolves correctly when Tortoise is initialized."""
        from asynctasq.serializers.hooks.orm.lazy_proxy import LazyOrmProxy

        hook = TortoiseOrmHook()

        model_class = MagicMock()
        model_class.__name__ = "Product"
        mock_model = MagicMock()
        model_class.get = AsyncMock(return_value=mock_model)

        # First: Tortoise not initialized - should return lazy proxy
        with patch("tortoise.Tortoise") as mock_tortoise:
            mock_tortoise._inited = False
            proxy = await hook._fetch_model(model_class, 42)
            assert isinstance(proxy, LazyOrmProxy)

            # Second: Initialize Tortoise and resolve the proxy
            mock_tortoise._inited = True
            resolved = await proxy.await_resolve()
            assert resolved == mock_model
            model_class.get.assert_called_once_with(pk=42)

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.tortoise.TORTOISE_AVAILABLE", True)
    async def test_fetch_model_immediate_with_connection_error(self) -> None:
        """Test _fetch_model_immediate raises helpful error for connection issues."""
        hook = TortoiseOrmHook()

        model_class = MagicMock()
        model_class.__name__ = "Product"

        # Mock get() to raise connection error
        model_class.get = AsyncMock(side_effect=Exception("default_connection cannot be None"))

        # Mock Tortoise as initialized but with connection error
        with patch("tortoise.Tortoise") as mock_tortoise:
            mock_tortoise._inited = True
            with raises(
                RuntimeError,
                match="Tortoise ORM initialization error while fetching Product",
            ):
                await hook._fetch_model_immediate(model_class, 42)

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.tortoise.TORTOISE_AVAILABLE", True)
    async def test_fetch_model_immediate_with_generic_error(self) -> None:
        """Test _fetch_model_immediate propagates generic errors."""
        hook = TortoiseOrmHook()

        model_class = MagicMock()
        model_class.__name__ = "Product"

        # Mock get() to raise generic error
        model_class.get = AsyncMock(side_effect=ValueError("Some other error"))

        # Mock Tortoise as initialized
        with patch("tortoise.Tortoise") as mock_tortoise:
            mock_tortoise._inited = True
            with raises(ValueError, match="Some other error"):
                await hook._fetch_model_immediate(model_class, 42)

    def test_can_encode_returns_false_for_primitives(self) -> None:
        """Test can_encode returns False for primitive types."""
        hook = TortoiseOrmHook()

        assert hook.can_encode("string") is False
        assert hook.can_encode(123) is False
        assert hook.can_encode(45.67) is False
        assert hook.can_encode(True) is False
        assert hook.can_encode(None) is False
        assert hook.can_encode([]) is False
        assert hook.can_encode({}) is False

    def test_get_model_pk_with_various_pk_types(self) -> None:
        """Test _get_model_pk works with different primary key types."""
        hook = TortoiseOrmHook()

        # Integer pk
        obj1 = MockTortoiseModel(pk=42)
        assert hook._get_model_pk(obj1) == 42

        # String pk
        obj2 = MockTortoiseModel(pk="uuid-123")
        assert hook._get_model_pk(obj2) == "uuid-123"

        # None pk
        obj3 = MockTortoiseModel(pk=None)
        assert hook._get_model_pk(obj3) is None

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.tortoise.TORTOISE_AVAILABLE", True)
    async def test_fetch_model_with_none_pk(self) -> None:
        """Test _fetch_model works with None pk value."""
        hook = TortoiseOrmHook()

        model_class = MagicMock()
        model_class.__name__ = "Product"
        mock_model = MagicMock()
        model_class.get = AsyncMock(return_value=mock_model)

        with patch("tortoise.Tortoise") as mock_tortoise:
            mock_tortoise._inited = True
            result = await hook._fetch_model(model_class, None)
            assert result == mock_model
            model_class.get.assert_called_once_with(pk=None)


# =============================================================================
# Test Tortoise Hook with LazyOrmProxy auto-initialization
# =============================================================================


@mark.unit
class TestTortoiseHookWithLazyProxyAutoInit:
    """Test Tortoise hook auto-initialization via LazyOrmProxy."""

    @fixture
    def hook(self) -> TortoiseOrmHook:
        return TortoiseOrmHook()

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.tortoise.TORTOISE_AVAILABLE", True)
    async def test_lazy_proxy_auto_init_with_config(self) -> None:
        """Test LazyOrmProxy auto-initializes Tortoise when config is available."""
        from asynctasq.serializers.hooks.orm.lazy_proxy import LazyOrmProxy

        hook = TortoiseOrmHook()

        model_class = MagicMock()
        model_class.__name__ = "Product"
        mock_model = MagicMock()
        model_class.get = AsyncMock(return_value=mock_model)

        # First: Get lazy proxy when Tortoise not initialized
        with patch("tortoise.Tortoise") as mock_tortoise:
            mock_tortoise._inited = False
            proxy = await hook._fetch_model(model_class, 42)
            assert isinstance(proxy, LazyOrmProxy)

            # Mock config and Tortoise.init
            mock_tortoise.init = AsyncMock()
            mock_tortoise.generate_schemas = AsyncMock()

            with (
                patch("asynctasq.config.Config.get") as mock_get_config,
            ):
                mock_config = MagicMock()
                mock_config.tortoise_orm = {
                    "db_url": "sqlite://:memory:",
                    "modules": {"models": ["__main__"]},
                }
                mock_get_config.return_value = mock_config

                # Now try to resolve - should auto-init
                mock_tortoise._inited = True
                resolved = await proxy.await_resolve()

                assert resolved == mock_model
                model_class.get.assert_called_once_with(pk=42)

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.tortoise.TORTOISE_AVAILABLE", True)
    async def test_lazy_proxy_handles_config_access_error(self) -> None:
        """Test LazyOrmProxy handles config access errors gracefully."""
        from asynctasq.serializers.hooks.orm.lazy_proxy import LazyOrmProxy

        hook = TortoiseOrmHook()

        model_class = MagicMock()
        model_class.__name__ = "Product"

        # Get lazy proxy
        with patch("tortoise.Tortoise") as mock_tortoise:
            mock_tortoise._inited = False
            proxy = await hook._fetch_model(model_class, 42)
            assert isinstance(proxy, LazyOrmProxy)

            # Mock config access to raise exception
            with (
                patch("asynctasq.config.Config.get", side_effect=RuntimeError("Config error")),
            ):
                # Should not crash - just log warning and continue
                mock_tortoise._inited = True
                model_class.get = AsyncMock(return_value=MagicMock())

                # Should still work despite config error
                resolved = await proxy.await_resolve()
                assert resolved is not None
