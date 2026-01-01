"""Tests for LazyOrmProxyHook."""

from unittest.mock import MagicMock, patch

from pytest import mark

from asynctasq.serializers.hooks.orm.lazy_proxy import LazyOrmProxy
from asynctasq.serializers.hooks.orm.lazy_proxy_hook import LazyOrmProxyHook


@mark.unit
class TestLazyOrmProxyHook:
    """Tests for LazyOrmProxyHook class."""

    def test_type_key(self) -> None:
        """Test type_key is correct."""
        hook = LazyOrmProxyHook()
        assert hook.type_key == "__lazy_orm_proxy__"

    def test_priority(self) -> None:
        """Test priority is higher than ORM hooks."""
        hook = LazyOrmProxyHook()
        assert hook.priority == 150

    def test_can_encode_with_lazy_proxy(self) -> None:
        """Test can_encode returns True for LazyOrmProxy."""
        hook = LazyOrmProxyHook()
        model_class = MagicMock()
        proxy = LazyOrmProxy(model_class, 42, MagicMock())
        assert hook.can_encode(proxy) is True

    def test_can_encode_with_non_proxy(self) -> None:
        """Test can_encode returns False for non-proxy objects."""
        hook = LazyOrmProxyHook()
        assert hook.can_encode("string") is False
        assert hook.can_encode(123) is False
        assert hook.can_encode({}) is False
        assert hook.can_encode(None) is False

    def test_encode_extracts_model_class_and_pk(self) -> None:
        """Test encode extracts model class path and pk from proxy."""
        hook = LazyOrmProxyHook()

        model_class = MagicMock()
        model_class.__module__ = "myapp.models"
        model_class.__name__ = "Product"

        proxy = LazyOrmProxy(model_class, 42, MagicMock())

        result = hook.encode(proxy)

        assert result == {
            "__type__": "__lazy_orm_proxy__",
            "model_class": "myapp.models.Product",
            "pk": 42,
        }

    def test_encode_with_string_pk(self) -> None:
        """Test encode works with string primary key."""
        hook = LazyOrmProxyHook()

        model_class = MagicMock()
        model_class.__module__ = "myapp.models"
        model_class.__name__ = "User"

        proxy = LazyOrmProxy(model_class, "user-uuid-123", MagicMock())

        result = hook.encode(proxy)

        assert result["pk"] == "user-uuid-123"

    def test_encode_with_composite_pk(self) -> None:
        """Test encode works with composite primary key."""
        hook = LazyOrmProxyHook()

        model_class = MagicMock()
        model_class.__module__ = "myapp.models"
        model_class.__name__ = "UserSession"

        proxy = LazyOrmProxy(model_class, (1, "abc123"), MagicMock())

        result = hook.encode(proxy)

        assert result["pk"] == (1, "abc123")

    @mark.asyncio
    @patch.object(LazyOrmProxyHook, "_is_tortoise_model", return_value=True)
    async def test_decode_tortoise_model(self, mock_is_tortoise: MagicMock) -> None:
        """Test decode converts to Tortoise ORM reference."""
        hook = LazyOrmProxyHook()

        data = {
            "__type__": "__lazy_orm_proxy__",
            "model_class": "myapp.models.Product",
            "pk": 42,
        }

        result = await hook.decode(data)

        assert result == {
            "__type__": "__tortoise_orm__",
            "model_class": "myapp.models.Product",
            "pk": 42,
        }

    @mark.asyncio
    @patch.object(LazyOrmProxyHook, "_is_tortoise_model", return_value=False)
    @patch.object(LazyOrmProxyHook, "_is_django_model", return_value=True)
    async def test_decode_django_model(
        self, mock_is_django: MagicMock, mock_is_tortoise: MagicMock
    ) -> None:
        """Test decode converts to Django ORM reference."""
        hook = LazyOrmProxyHook()

        data = {
            "__type__": "__lazy_orm_proxy__",
            "model_class": "myapp.models.Article",
            "pk": 42,
        }

        result = await hook.decode(data)

        assert result == {
            "__type__": "__django_orm__",
            "model_class": "myapp.models.Article",
            "pk": 42,
        }

    @mark.asyncio
    @patch.object(LazyOrmProxyHook, "_is_tortoise_model", return_value=False)
    @patch.object(LazyOrmProxyHook, "_is_django_model", return_value=False)
    @patch.object(LazyOrmProxyHook, "_is_sqlalchemy_model", return_value=True)
    async def test_decode_sqlalchemy_model(
        self,
        mock_is_sqlalchemy: MagicMock,
        mock_is_django: MagicMock,
        mock_is_tortoise: MagicMock,
    ) -> None:
        """Test decode converts to SQLAlchemy ORM reference."""
        hook = LazyOrmProxyHook()

        data = {
            "__type__": "__lazy_orm_proxy__",
            "model_class": "myapp.models.User",
            "pk": 42,
        }

        result = await hook.decode(data)

        assert result == {
            "__type__": "__sqlalchemy_orm__",
            "model_class": "myapp.models.User",
            "pk": 42,
        }

    @mark.asyncio
    @patch.object(LazyOrmProxyHook, "_is_tortoise_model", return_value=False)
    @patch.object(LazyOrmProxyHook, "_is_django_model", return_value=False)
    @patch.object(LazyOrmProxyHook, "_is_sqlalchemy_model", return_value=False)
    async def test_decode_unknown_model(
        self,
        mock_is_sqlalchemy: MagicMock,
        mock_is_django: MagicMock,
        mock_is_tortoise: MagicMock,
    ) -> None:
        """Test decode returns data as-is for unknown model type."""
        hook = LazyOrmProxyHook()

        data = {
            "__type__": "__lazy_orm_proxy__",
            "model_class": "unknown.models.SomeModel",
            "pk": 42,
        }

        result = await hook.decode(data)

        assert result == data

    def test_is_tortoise_model_with_invalid_path(self) -> None:
        """Test _is_tortoise_model handles invalid class paths."""
        hook = LazyOrmProxyHook()

        # No dot in path
        result = hook._is_tortoise_model("Product")
        assert result is False

        # Module doesn't exist
        result = hook._is_tortoise_model("nonexistent.module.Model")
        assert result is False

        # ImportError should be caught
        with patch("builtins.__import__", side_effect=ImportError("No module")):
            result = hook._is_tortoise_model("myapp.models.Product")
            assert result is False

    def test_is_django_model_with_invalid_path(self) -> None:
        """Test _is_django_model handles invalid class paths."""
        hook = LazyOrmProxyHook()

        # No dot in path
        result = hook._is_django_model("Article")
        assert result is False

        # Module doesn't exist
        result = hook._is_django_model("nonexistent.module.Article")
        assert result is False

    def test_is_django_model_with_exception(self) -> None:
        """Test _is_django_model returns False when exception occurs."""
        hook = LazyOrmProxyHook()

        with patch("builtins.__import__", side_effect=AttributeError):
            result = hook._is_django_model("myapp.models.Article")
            assert result is False

    def test_is_sqlalchemy_model_with_invalid_path(self) -> None:
        """Test _is_sqlalchemy_model handles invalid class paths."""
        hook = LazyOrmProxyHook()

        # No dot in path
        result = hook._is_sqlalchemy_model("User")
        assert result is False

        # Module doesn't exist
        result = hook._is_sqlalchemy_model("nonexistent.module.User")
        assert result is False

    def test_is_sqlalchemy_model_with_exception(self) -> None:
        """Test _is_sqlalchemy_model returns False when exception occurs."""
        hook = LazyOrmProxyHook()

        with patch("builtins.__import__", side_effect=ModuleNotFoundError):
            result = hook._is_sqlalchemy_model("myapp.models.User")
            assert result is False

    def test_encode_with_none_pk(self) -> None:
        """Test encode handles None pk."""
        hook = LazyOrmProxyHook()

        model_class = MagicMock()
        model_class.__module__ = "myapp.models"
        model_class.__name__ = "Product"

        proxy = LazyOrmProxy(model_class, None, MagicMock())

        result = hook.encode(proxy)

        assert result["pk"] is None

    def test_is_tortoise_model_with_getattr_exception(self) -> None:
        """Test _is_tortoise_model handles getattr exceptions."""
        hook = LazyOrmProxyHook()

        with patch("builtins.__import__") as mock_import:
            mock_module = MagicMock()
            mock_import.return_value = mock_module
            # Make getattr raise exception
            mock_module.__getattribute__ = MagicMock(side_effect=AttributeError("No such attr"))

            result = hook._is_tortoise_model("myapp.models.Product")
            assert result is False

    def test_is_django_model_with_getattr_exception(self) -> None:
        """Test _is_django_model handles getattr exceptions."""
        hook = LazyOrmProxyHook()

        with patch("builtins.__import__") as mock_import:
            mock_module = MagicMock()
            mock_import.return_value = mock_module
            # Make getattr raise exception
            mock_module.__getattribute__ = MagicMock(side_effect=AttributeError("No such attr"))

            result = hook._is_django_model("myapp.models.Article")
            assert result is False

    def test_is_sqlalchemy_model_with_getattr_exception(self) -> None:
        """Test _is_sqlalchemy_model handles getattr exceptions."""
        hook = LazyOrmProxyHook()

        with patch("builtins.__import__") as mock_import:
            mock_module = MagicMock()
            mock_import.return_value = mock_module
            # Make getattr raise exception
            mock_module.__getattribute__ = MagicMock(side_effect=AttributeError("No such attr"))

            result = hook._is_sqlalchemy_model("myapp.models.User")
            assert result is False

    def test_is_tortoise_model_non_subclass(self) -> None:
        """Test _is_tortoise_model returns False for non-Tortoise models."""
        hook = LazyOrmProxyHook()

        with patch("builtins.__import__") as mock_import:
            mock_module = MagicMock()
            mock_class = MagicMock()
            mock_module.Product = mock_class
            mock_import.return_value = mock_module

            # Mock issubclass to return False
            with patch("builtins.issubclass", return_value=False):
                result = hook._is_tortoise_model("myapp.models.Product")
                assert result is False

    def test_is_django_model_non_subclass(self) -> None:
        """Test _is_django_model returns False for non-Django models."""
        hook = LazyOrmProxyHook()

        with patch("builtins.__import__") as mock_import:
            mock_module = MagicMock()
            mock_class = MagicMock()
            mock_module.Article = mock_class
            mock_import.return_value = mock_module

            # Mock issubclass to return False
            with patch("builtins.issubclass", return_value=False):
                result = hook._is_django_model("myapp.models.Article")
                assert result is False

    def test_is_sqlalchemy_model_non_subclass(self) -> None:
        """Test _is_sqlalchemy_model returns False for non-SQLAlchemy models."""
        hook = LazyOrmProxyHook()

        with patch("builtins.__import__") as mock_import:
            mock_module = MagicMock()
            mock_class = MagicMock()
            mock_module.User = mock_class
            mock_import.return_value = mock_module

            # Mock issubclass to return False
            with patch("builtins.issubclass", return_value=False):
                result = hook._is_sqlalchemy_model("myapp.models.User")
                assert result is False

    def test_is_tortoise_model_type_error(self) -> None:
        """Test _is_tortoise_model handles TypeError from issubclass."""
        hook = LazyOrmProxyHook()

        with patch("builtins.__import__") as mock_import:
            mock_module = MagicMock()
            mock_import.return_value = mock_module
            mock_module.Product = "not a class"

            result = hook._is_tortoise_model("myapp.models.Product")
            assert result is False

    def test_is_django_model_type_error(self) -> None:
        """Test _is_django_model handles TypeError from issubclass."""
        hook = LazyOrmProxyHook()

        with patch("builtins.__import__") as mock_import:
            mock_module = MagicMock()
            mock_import.return_value = mock_module
            mock_module.Article = "not a class"

            result = hook._is_django_model("myapp.models.Article")
            assert result is False

    def test_is_sqlalchemy_model_type_error(self) -> None:
        """Test _is_sqlalchemy_model handles TypeError from issubclass."""
        hook = LazyOrmProxyHook()

        with patch("builtins.__import__") as mock_import:
            mock_module = MagicMock()
            mock_import.return_value = mock_module
            mock_module.User = "not a class"

            result = hook._is_sqlalchemy_model("myapp.models.User")
            assert result is False
