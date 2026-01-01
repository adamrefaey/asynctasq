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
