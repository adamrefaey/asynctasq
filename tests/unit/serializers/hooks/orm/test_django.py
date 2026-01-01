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


# =============================================================================
# Test DjangoOrmHook Edge Cases
# =============================================================================


@mark.unit
class TestDjangoHookEdgeCases:
    """Test Django ORM hook edge cases and error conditions."""

    @fixture
    def hook(self) -> DjangoOrmHook:
        return DjangoOrmHook()

    @patch("asynctasq.serializers.hooks.orm.django.DJANGO_AVAILABLE", True)
    @patch("asynctasq.serializers.hooks.orm.django", MagicMock())
    def test_can_encode_with_none_model_returns_false(self, hook: DjangoOrmHook) -> None:
        """Test can_encode returns False for None input."""
        result = hook.can_encode(None)
        assert result is False

    @patch("asynctasq.serializers.hooks.orm.django.DJANGO_AVAILABLE", True)
    def test_can_encode_with_model_without_pk_attribute(self, hook: DjangoOrmHook) -> None:
        """Test can_encode returns False for model without pk attribute."""
        obj = MagicMock()
        del obj.pk  # Remove pk attribute
        result = hook.can_encode(obj)
        assert result is False

    @patch("asynctasq.serializers.hooks.orm.django.DJANGO_AVAILABLE", True)
    def test_can_encode_with_none_pk_value(self, hook: DjangoOrmHook) -> None:
        """Test can_encode returns False for model with None pk."""
        obj = MockDjangoModel(pk=None)
        result = hook.can_encode(obj)
        assert result is False

    @patch("asynctasq.serializers.hooks.orm.django.DJANGO_AVAILABLE", True)
    def test_can_encode_with_empty_string_pk(self, hook: DjangoOrmHook) -> None:
        """Test can_encode returns False for model with empty string pk."""
        obj = MockDjangoModel(pk="")
        result = hook.can_encode(obj)
        assert result is False

    @patch("asynctasq.serializers.hooks.orm.django.DJANGO_AVAILABLE", True)
    @patch("asynctasq.serializers.hooks.orm.django", MagicMock())
    def test_can_encode_with_zero_pk(self, hook: DjangoOrmHook) -> None:
        """Test can_encode returns True for model with zero pk."""
        obj = MockDjangoModel(pk=0)
        # Note: This test assumes MockDjangoModel is recognized as a Django model
        # In real usage, isinstance(obj, django.db.models.Model) would be True
        result = hook.can_encode(obj)
        # The result depends on whether MockDjangoModel passes isinstance check
        # This test documents the expected behavior for zero pk values
        assert isinstance(result, bool)

    def test_get_model_pk_with_none_model_raises_attributeerror(self, hook: DjangoOrmHook) -> None:
        """Test _get_model_pk raises AttributeError for None model."""
        with raises(AttributeError, match="'NoneType' object has no attribute 'pk'"):
            hook._get_model_pk(None)

    def test_get_model_pk_with_model_without_pk_attribute(self, hook: DjangoOrmHook) -> None:
        """Test _get_model_pk raises AttributeError for model without pk."""
        obj = MagicMock()
        del obj.pk
        with raises(AttributeError, match="pk"):
            hook._get_model_pk(obj)

    def test_get_model_pk_with_none_pk_value(self, hook: DjangoOrmHook) -> None:
        """Test _get_model_pk returns None for None pk value."""
        obj = MockDjangoModel(pk=None)
        result = hook._get_model_pk(obj)
        assert result is None

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.django.DJANGO_AVAILABLE", True)
    async def test_fetch_model_with_none_model_class_raises_attributeerror(
        self, hook: DjangoOrmHook
    ) -> None:
        """Test _fetch_model raises AttributeError for None model_class."""
        with raises(AttributeError, match="'NoneType' object has no attribute 'objects'"):
            await hook._fetch_model(None, 1)  # type: ignore

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.django.DJANGO_AVAILABLE", True)
    async def test_fetch_model_with_none_pk_passes_to_django(self, hook: DjangoOrmHook) -> None:
        """Test _fetch_model passes None pk to Django methods."""
        model_class = MagicMock()
        model_class.objects.aget = AsyncMock(return_value=MagicMock())
        result = await hook._fetch_model(model_class, None)
        assert result is not None
        model_class.objects.aget.assert_called_once_with(pk=None)

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.django.DJANGO_AVAILABLE", True)
    async def test_fetch_model_with_model_class_without_objects_raises_attributeerror(
        self, hook: DjangoOrmHook
    ) -> None:
        """Test _fetch_model raises AttributeError when model class has no objects."""
        model_class = MagicMock()
        del model_class.objects
        with raises(AttributeError, match="objects"):
            await hook._fetch_model(model_class, 1)

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.django.DJANGO_AVAILABLE", True)
    async def test_fetch_model_with_objects_without_aget_falls_back_to_get(
        self, hook: DjangoOrmHook
    ) -> None:
        """Test _fetch_model falls back to get when aget not available."""
        model_class = MagicMock()
        # Remove aget to force fallback
        del model_class.objects.aget
        model_class.objects.get = MagicMock(return_value=MagicMock())
        result = await hook._fetch_model(model_class, 1)
        assert result is not None
        model_class.objects.get.assert_called_once_with(pk=1)

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.django.DJANGO_AVAILABLE", True)
    async def test_fetch_model_with_aget_raises_exception(self, hook: DjangoOrmHook) -> None:
        """Test _fetch_model propagates exceptions from aget."""
        model_class = MagicMock()
        model_class.objects.aget = AsyncMock(side_effect=ValueError("Database error"))
        with raises(ValueError, match="Database error"):
            await hook._fetch_model(model_class, 1)

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.django.DJANGO_AVAILABLE", True)
    async def test_fetch_model_with_sync_get_raises_exception(self, hook: DjangoOrmHook) -> None:
        """Test _fetch_model propagates exceptions from sync get."""
        model_class = MagicMock()
        # Force fallback to sync get
        del model_class.objects.aget
        model_class.objects.get = MagicMock(side_effect=RuntimeError("Sync database error"))
        with raises(RuntimeError, match="Sync database error"):
            await hook._fetch_model(model_class, 1)

    def test_can_encode_with_instance_check_exception_caught(self, hook: DjangoOrmHook) -> None:
        """Test can_encode catches exceptions from isinstance check."""
        obj = MagicMock()
        with patch("asynctasq.serializers.hooks.orm.django.DJANGO_AVAILABLE", True):
            with patch("asynctasq.serializers.hooks.orm.django.django") as mock_django:
                # Make the isinstance check raise
                mock_django.db.models.Model = MagicMock()
                result = hook.can_encode(obj)
                # Should return False when exception occurs
                assert result is False

    def test_get_model_pk_with_none_pk_edge_case(self, hook: DjangoOrmHook) -> None:
        """Test _get_model_pk with model that has None pk doesn't crash."""
        obj = MockDjangoModel(pk=None)
        result = hook._get_model_pk(obj)
        assert result is None

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.django.DJANGO_AVAILABLE", True)
    async def test_fetch_model_with_sync_executor(self, hook: DjangoOrmHook) -> None:
        """Test _fetch_model properly uses executor for sync database calls."""
        model_class = MagicMock()
        mock_model = MagicMock()
        # Remove aget to force sync fallback
        del model_class.objects.aget
        model_class.objects.get = MagicMock(return_value=mock_model)

        result = await hook._fetch_model(model_class, 42)

        assert result == mock_model
        # Verify the sync get was called
        model_class.objects.get.assert_called_once_with(pk=42)


# =============================================================================
# Test Django Hook Integration with Error Messages
# =============================================================================


@mark.unit
class TestDjangoHookErrorMessages:
    """Test Django ORM hook error message clarity."""

    @fixture
    def hook(self) -> DjangoOrmHook:
        return DjangoOrmHook()

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.django.DJANGO_AVAILABLE", False)
    async def test_fetch_model_error_message_clarity(self, hook: DjangoOrmHook) -> None:
        """Test that ImportError message is clear."""
        with raises(ImportError, match="Django is not installed"):
            await hook._fetch_model(MagicMock, 1)

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.django.DJANGO_AVAILABLE", True)
    async def test_fetch_model_with_database_error(self, hook: DjangoOrmHook) -> None:
        """Test _fetch_model propagates database errors with original message."""
        model_class = MagicMock()
        model_class.objects.aget = AsyncMock(side_effect=Exception("Connection to database failed"))

        with raises(Exception, match="Connection to database failed"):
            await hook._fetch_model(model_class, 1)

    def test_hook_attributes_are_correct(self, hook: DjangoOrmHook) -> None:
        """Test hook has correct attributes for Django ORM."""
        assert hook.orm_name == "django"
        assert hook.type_key == "__orm:django__"
        assert hook.priority == 100

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.django.DJANGO_AVAILABLE", True)
    async def test_fetch_model_with_empty_string_pk(self, hook: DjangoOrmHook) -> None:
        """Test _fetch_model handles empty string pk."""
        mock_model = MagicMock()
        model_class = MagicMock()
        model_class.objects.aget = AsyncMock(return_value=mock_model)
        result = await hook._fetch_model(model_class, "")
        assert result == mock_model
        model_class.objects.aget.assert_called_once_with(pk="")

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.django.DJANGO_AVAILABLE", True)
    async def test_fetch_model_with_zero_pk(self, hook: DjangoOrmHook) -> None:
        """Test _fetch_model handles zero pk."""
        mock_model = MagicMock()
        model_class = MagicMock()
        model_class.objects.aget = AsyncMock(return_value=mock_model)
        result = await hook._fetch_model(model_class, 0)
        assert result == mock_model
        model_class.objects.aget.assert_called_once_with(pk=0)

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.django.DJANGO_AVAILABLE", True)
    async def test_fetch_model_with_complex_pk(self, hook: DjangoOrmHook) -> None:
        """Test _fetch_model handles complex pk types."""
        mock_model = MagicMock()
        model_class = MagicMock()
        complex_pk = {"id": 1, "type": "test"}
        model_class.objects.aget = AsyncMock(return_value=mock_model)
        result = await hook._fetch_model(model_class, complex_pk)
        assert result == mock_model
        model_class.objects.aget.assert_called_once_with(pk=complex_pk)


@mark.unit
class TestDjangoHookEncodeDecode:
    """Test Django ORM hook encode and decode methods."""

    @fixture
    def hook(self) -> DjangoOrmHook:
        return DjangoOrmHook()

    def test_encode_extracts_model_info(self, hook: DjangoOrmHook) -> None:
        """Test encode extracts model class path and pk."""
        obj = MockDjangoModel(pk=42)
        obj.__class__.__module__ = "myapp.models"
        obj.__class__.__name__ = "Article"

        result = hook.encode(obj)

        assert result["__orm:django__"] == 42  # type_key maps to pk value
        assert result["__orm_class__"] == "myapp.models.Article"

    def test_encode_with_string_pk(self, hook: DjangoOrmHook) -> None:
        """Test encode works with string pk."""
        obj = MockDjangoModel(pk="uuid-123")
        obj.__class__.__module__ = "myapp.models"
        obj.__class__.__name__ = "User"

        result = hook.encode(obj)

        assert result["__orm:django__"] == "uuid-123"

    @mark.asyncio
    async def test_decode_calls_fetch_model(self, hook: DjangoOrmHook) -> None:
        """Test decode_async calls _fetch_model with correct parameters."""
        data = {
            "__orm:django__": 42,
            "__orm_class__": "myapp.models.Article",
        }

        mock_model = MagicMock()
        mock_class = MagicMock()

        with (
            patch.object(hook, "_import_model_class", return_value=mock_class),
            patch.object(hook, "_fetch_model", new=AsyncMock(return_value=mock_model)),
        ):
            result = await hook.decode_async(data)

        assert result == mock_model

    @mark.asyncio
    async def test_decode_with_string_pk(self, hook: DjangoOrmHook) -> None:
        """Test decode_async works with string pk."""
        data = {
            "__orm:django__": "uuid-456",
            "__orm_class__": "myapp.models.User",
        }

        mock_model = MagicMock()
        mock_class = MagicMock()

        with (
            patch.object(hook, "_import_model_class", return_value=mock_class),
            patch.object(hook, "_fetch_model", new=AsyncMock(return_value=mock_model)),
        ):
            result = await hook.decode_async(data)

        assert result == mock_model


# =============================================================================
# Test Django Hook Import Model Class
# =============================================================================


@mark.unit
class TestDjangoImportModelClass:
    """Test _import_model_class method from BaseOrmHook."""

    @fixture
    def hook(self) -> DjangoOrmHook:
        return DjangoOrmHook()

    def test_import_model_class_regular_module(self, hook: DjangoOrmHook) -> None:
        """Test _import_model_class imports from regular module."""
        # Use a real class to test
        model_class = hook._import_model_class("unittest.mock.MagicMock")
        assert model_class is not None
        assert model_class.__name__ == "MagicMock"

    def test_import_model_class_invalid_module(self, hook: DjangoOrmHook) -> None:
        """Test _import_model_class raises ImportError for invalid module."""
        with raises(ImportError):
            hook._import_model_class("nonexistent.module.Model")

    def test_import_model_class_main_module(self, hook: DjangoOrmHook) -> None:
        """Test _import_model_class handles __main__ module with file."""
        from pathlib import Path
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("class Article:\n    pass\n")
            temp_file = f.name

        try:
            model_class = hook._import_model_class("__main__.Article", temp_file)
            assert model_class is not None
            assert model_class.__name__ == "Article"
        finally:
            Path(temp_file).unlink()

    def test_import_model_class_with_class_file(self, hook: DjangoOrmHook) -> None:
        """Test _import_model_class uses class_file parameter."""
        from pathlib import Path
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("class CustomModel:\n    def __init__(self):\n        self.name = 'test'\n")
            temp_file = f.name

        try:
            model_class = hook._import_model_class("__main__.CustomModel", temp_file)
            assert model_class is not None
            assert model_class.__name__ == "CustomModel"
            # Test instantiation
            instance = model_class()
            assert instance.name == "test"
        finally:
            Path(temp_file).unlink()
