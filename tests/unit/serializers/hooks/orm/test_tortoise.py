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

    def test_get_model_pk(self, hook: TortoiseOrmHook) -> None:
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

        result = await hook._fetch_model(model_class, 42)
        assert result == mock_model
        model_class.get.assert_called_once_with(pk=42)

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.tortoise.TORTOISE_AVAILABLE", True)
    async def test_fetch_model_with_exception(self) -> None:
        """Test _fetch_model propagates exceptions from Tortoise get()."""
        hook = TortoiseOrmHook()

        model_class = MagicMock()
        model_class.get = AsyncMock(side_effect=RuntimeError("Database error"))

        with raises(RuntimeError, match="Database error"):
            await hook._fetch_model(model_class, 42)

    @patch("asynctasq.serializers.hooks.orm.tortoise.TORTOISE_AVAILABLE", True)
    @patch("asynctasq.serializers.hooks.orm.tortoise.TortoiseModel", None)
    def test_can_encode_when_tortoise_model_is_none(self) -> None:
        """Test can_encode returns False when TortoiseModel is None."""
        hook = TortoiseOrmHook()
        obj = MockTortoiseModel()
        assert hook.can_encode(obj) is False
