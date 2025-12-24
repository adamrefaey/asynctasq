"""Unit tests for Django ORM hook.

Testing Strategy:
- pytest 9.0.1 with asyncio_mode="strict" (explicit @mark.asyncio decorators required)
- AAA pattern (Arrange, Act, Assert)
- Mock Django models to avoid requiring actual Django installation
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from pytest import fixture, mark, raises

from asynctasq.serializers.hooks import DjangoOrmHook

# =============================================================================
# Mock Django Model
# =============================================================================


class MockDjangoModel:
    """Mock Django model for testing."""

    def __init__(self, pk: Any = 1):
        self.pk = pk
        self.objects = MagicMock()
        self.__class__.__module__ = "test_module"
        self.__class__.__name__ = "MockDjangoModel"


# =============================================================================
# Test DjangoOrmHook
# =============================================================================


@mark.unit
class TestDjangoOrmHook:
    """Test Django ORM hook."""

    @fixture
    def hook(self) -> DjangoOrmHook:
        return DjangoOrmHook()

    def test_orm_name(self, hook: DjangoOrmHook) -> None:
        """Test orm_name is django."""
        assert hook.orm_name == "django"

    def test_type_key(self, hook: DjangoOrmHook) -> None:
        """Test type_key is correct."""
        assert hook.type_key == "__orm:django__"

    def test_priority(self, hook: DjangoOrmHook) -> None:
        """Test priority is high (100)."""
        assert hook.priority == 100

    @patch("asynctasq.serializers.hooks.orm.django.DJANGO_AVAILABLE", True)
    def test_can_encode_when_django_not_available(self) -> None:
        """Test can_encode returns False when Django not installed."""
        hook = DjangoOrmHook()
        obj = MockDjangoModel()
        assert hook.can_encode(obj) is False

    def test_get_model_pk(self, hook: DjangoOrmHook) -> None:
        """Test _get_model_pk extracts pk from Django model."""
        obj = MockDjangoModel(pk=42)
        result = hook._get_model_pk(obj)
        assert result == 42

    @patch("asynctasq.serializers.hooks.orm.django.DJANGO_AVAILABLE", True)
    @patch("asynctasq.serializers.hooks.orm.django", MagicMock())
    def test_can_encode_with_django_exception(self) -> None:
        """Test can_encode handles Django exceptions gracefully."""
        hook = DjangoOrmHook()
        obj = MagicMock()
        # Make isinstance raise an exception
        with patch(
            "builtins.isinstance",
            side_effect=Exception("Test exception"),
        ):
            result = hook.can_encode(obj)
            assert result is False

    @patch("asynctasq.serializers.hooks.orm.django.DJANGO_AVAILABLE", False)
    def test_can_encode_returns_false_when_django_not_available(self) -> None:
        """Test can_encode returns False when DJANGO_AVAILABLE is False."""
        hook = DjangoOrmHook()
        obj = MockDjangoModel()
        result = hook.can_encode(obj)
        assert result is False

    @patch("asynctasq.serializers.hooks.orm.django.DJANGO_AVAILABLE", True)
    @patch("asynctasq.serializers.hooks.orm.django", None)
    def test_can_encode_returns_false_when_django_is_none(self) -> None:
        """Test can_encode returns False when django is None."""
        hook = DjangoOrmHook()
        obj = MockDjangoModel()
        result = hook.can_encode(obj)
        assert result is False

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.django.DJANGO_AVAILABLE", False)
    async def test_fetch_model_raises_when_not_available(self) -> None:
        """Test _fetch_model raises ImportError when Django not installed."""
        hook = DjangoOrmHook()
        with raises(ImportError, match="Django is not installed"):
            await hook._fetch_model(MagicMock, 1)

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.django.DJANGO_AVAILABLE", True)
    async def test_fetch_model_with_async_aget(self) -> None:
        """Test _fetch_model uses async aget when available."""
        hook = DjangoOrmHook()

        mock_model = MagicMock()
        model_class = MagicMock()
        model_class.objects.aget = AsyncMock(return_value=mock_model)

        result = await hook._fetch_model(model_class, 42)
        assert result == mock_model
        model_class.objects.aget.assert_called_once_with(pk=42)

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.django.DJANGO_AVAILABLE", True)
    async def test_fetch_model_fallback_to_sync(self) -> None:
        """Test _fetch_model falls back to sync get when aget not available."""
        hook = DjangoOrmHook()

        mock_model = MagicMock()
        model_class = MagicMock()
        # Remove aget to force fallback
        del model_class.objects.aget
        model_class.objects.get = MagicMock(return_value=mock_model)

        result = await hook._fetch_model(model_class, 42)
        assert result == mock_model

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.django.DJANGO_AVAILABLE", True)
    async def test_fetch_model_with_aget_attributeerror_fallback(self) -> None:
        """Test _fetch_model catches AttributeError from aget and falls back to sync."""
        hook = DjangoOrmHook()

        mock_model = MagicMock()
        model_class = MagicMock()
        # Make aget raise AttributeError
        model_class.objects.aget = AsyncMock(side_effect=AttributeError("No async support"))
        model_class.objects.get = MagicMock(return_value=mock_model)

        result = await hook._fetch_model(model_class, 42)
        assert result == mock_model
        model_class.objects.get.assert_called_once_with(pk=42)

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.django.DJANGO_AVAILABLE", True)
    async def test_fetch_model_with_sync_database_connection(self) -> None:
        """Test _fetch_model uses executor for sync database access."""
        hook = DjangoOrmHook()

        mock_model = MagicMock()
        model_class = MagicMock()
        # Make sure aget raises AttributeError to trigger fallback
        model_class.objects.aget = MagicMock(side_effect=AttributeError("No aget"))
        model_class.objects.get = MagicMock(return_value=mock_model)

        result = await hook._fetch_model(model_class, 42)
        assert result == mock_model
        model_class.objects.get.assert_called_once_with(pk=42)
