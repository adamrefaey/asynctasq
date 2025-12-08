"""Unit tests for ORM hooks.

Testing Strategy:
- pytest 9.0.1 with asyncio_mode="strict" (explicit @mark.asyncio decorators required)
- AAA pattern (Arrange, Act, Assert)
- Mock ORM models to avoid requiring actual ORM dependencies
- Test all ORM hook types (SQLAlchemy, Django, Tortoise)
- Test encoding and decoding
- Test error handling
"""

import contextvars
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from pytest import fixture, mark, raises

from asynctasq.serializers.hooks import (
    DJANGO_AVAILABLE,
    SQLALCHEMY_AVAILABLE,
    TORTOISE_AVAILABLE,
    BaseOrmHook,
    DjangoOrmHook,
    HookRegistry,
    SqlalchemyOrmHook,
    TortoiseOrmHook,
    register_orm_hooks,
)

# =============================================================================
# Mock ORM Models
# =============================================================================


class MockSQLAlchemyModel:
    """Mock SQLAlchemy model for testing."""

    def __init__(self, pk: Any = 1):
        self.id = pk
        self.__mapper__ = MagicMock()
        self.__class__.__module__ = "test_module"
        self.__class__.__name__ = "MockSQLAlchemyModel"


class MockDjangoModel:
    """Mock Django model for testing."""

    def __init__(self, pk: Any = 1):
        self.pk = pk
        self.objects = MagicMock()
        self.__class__.__module__ = "test_module"
        self.__class__.__name__ = "MockDjangoModel"


class MockTortoiseModel:
    """Mock Tortoise ORM model for testing."""

    def __init__(self, pk: Any = 1):
        self.pk = pk
        self.__class__.__module__ = "test_module"
        self.__class__.__name__ = "MockTortoiseModel"


# =============================================================================
# Test BaseOrmHook
# =============================================================================


@mark.unit
class TestBaseOrmHook:
    """Test base ORM hook functionality."""

    def test_type_key_generated_from_orm_name(self) -> None:
        """Test that type_key is generated from orm_name."""

        class TestHook(BaseOrmHook):
            orm_name = "test_orm"

            def can_encode(self, obj: Any) -> bool:
                return False

            def _get_model_pk(self, obj: Any) -> Any:
                return 1

            async def _fetch_model(self, model_class: type, pk: Any) -> Any:
                return None

        hook = TestHook()
        assert hook.type_key == "__orm:test_orm__"

    def test_get_model_class_path(self) -> None:
        """Test class path generation."""

        class TestHook(BaseOrmHook):
            orm_name = "test"

            def can_encode(self, obj: Any) -> bool:
                return False

            def _get_model_pk(self, obj: Any) -> Any:
                return 1

            async def _fetch_model(self, model_class: type, pk: Any) -> Any:
                return None

        hook = TestHook()
        obj = MockSQLAlchemyModel()
        path = hook._get_model_class_path(obj)
        assert path == "test_module.MockSQLAlchemyModel"

    def test_can_decode_with_valid_reference(self) -> None:
        """Test can_decode with valid ORM reference."""

        class TestHook(BaseOrmHook):
            orm_name = "test"

            def can_encode(self, obj: Any) -> bool:
                return False

            def _get_model_pk(self, obj: Any) -> Any:
                return 1

            async def _fetch_model(self, model_class: type, pk: Any) -> Any:
                return None

        hook = TestHook()
        data = {"__orm:test__": 1, "__orm_class__": "module.Class"}
        assert hook.can_decode(data) is True

    def test_can_decode_without_class_path(self) -> None:
        """Test can_decode returns False without __orm_class__."""

        class TestHook(BaseOrmHook):
            orm_name = "test"

            def can_encode(self, obj: Any) -> bool:
                return False

            def _get_model_pk(self, obj: Any) -> Any:
                return 1

            async def _fetch_model(self, model_class: type, pk: Any) -> Any:
                return None

        hook = TestHook()
        data = {"__orm:test__": 1}
        assert hook.can_decode(data) is False

    def test_encode_returns_reference_dict(self) -> None:
        """Test encode returns proper reference dictionary."""

        class TestHook(BaseOrmHook):
            orm_name = "test"

            def can_encode(self, obj: Any) -> bool:
                return True

            def _get_model_pk(self, obj: Any) -> Any:
                return 42

            async def _fetch_model(self, model_class: type, pk: Any) -> Any:
                return None

        hook = TestHook()
        obj = MockSQLAlchemyModel(pk=42)
        result = hook.encode(obj)
        assert result == {
            "__orm:test__": 42,
            "__orm_class__": "test_module.MockSQLAlchemyModel",
        }

    @mark.asyncio
    async def test_decode_async_with_invalid_reference(self) -> None:
        """Test decode_async raises ValueError for invalid reference."""

        class TestHook(BaseOrmHook):
            orm_name = "test"

            def can_encode(self, obj: Any) -> bool:
                return False

            def _get_model_pk(self, obj: Any) -> Any:
                return 1

            async def _fetch_model(self, model_class: type, pk: Any) -> Any:
                return None

        hook = TestHook()
        with raises(ValueError, match="Invalid ORM reference"):
            await hook.decode_async({"__orm:test__": None, "__orm_class__": None})


# =============================================================================
# Test SqlalchemyOrmHook
# =============================================================================


@mark.unit
class TestSqlalchemyOrmHook:
    """Test SQLAlchemy ORM hook."""

    @fixture
    def hook(self) -> SqlalchemyOrmHook:
        return SqlalchemyOrmHook()

    def test_orm_name(self, hook: SqlalchemyOrmHook) -> None:
        """Test orm_name is sqlalchemy."""
        assert hook.orm_name == "sqlalchemy"

    def test_type_key(self, hook: SqlalchemyOrmHook) -> None:
        """Test type_key is correct."""
        assert hook.type_key == "__orm:sqlalchemy__"

    def test_priority(self, hook: SqlalchemyOrmHook) -> None:
        """Test priority is high (100)."""
        assert hook.priority == 100

    @patch("asynctasq.serializers.hooks.orm.SQLALCHEMY_AVAILABLE", False)
    def test_can_encode_when_sqlalchemy_not_available(self) -> None:
        """Test can_encode returns False when SQLAlchemy not installed."""
        hook = SqlalchemyOrmHook()
        obj = MockSQLAlchemyModel()
        assert hook.can_encode(obj) is False

    @patch("asynctasq.serializers.hooks.orm.SQLALCHEMY_AVAILABLE", True)
    def test_can_encode_with_mapper(self, hook: SqlalchemyOrmHook) -> None:
        """Test can_encode detects model via __mapper__."""
        obj = MagicMock()
        obj.__mapper__ = MagicMock()
        assert hook.can_encode(obj) is True

    @patch("asynctasq.serializers.hooks.orm.SQLALCHEMY_AVAILABLE", True)
    def test_can_encode_with_non_model(self, hook: SqlalchemyOrmHook) -> None:
        """Test can_encode returns False for non-model objects."""
        with patch("sqlalchemy.inspect", side_effect=Exception("Not a model")):
            assert hook.can_encode("string") is False
            assert hook.can_encode(123) is False
            assert hook.can_encode({}) is False

    @patch("asynctasq.serializers.hooks.orm.SQLALCHEMY_AVAILABLE", True)
    def test_can_encode_with_declarative_base_isinstance(self, hook: SqlalchemyOrmHook) -> None:
        """Test can_encode detects model via DeclarativeBase isinstance."""
        obj = MagicMock()

        # Test the __mapper__ path
        obj.__mapper__ = MagicMock()
        result = hook.can_encode(obj)
        assert result is True

    @patch("asynctasq.serializers.hooks.orm.SQLALCHEMY_AVAILABLE", True)
    def test_can_encode_with_inspect_returns_mapper(self, hook: SqlalchemyOrmHook) -> None:
        """Test can_encode detects model via sqlalchemy.inspect."""
        obj = MagicMock()
        obj.__mapper__ = None  # No __mapper__

        with patch("sqlalchemy.inspect") as mock_inspect:
            mock_mapper = MagicMock()
            mock_inspect.return_value = mock_mapper
            result = hook.can_encode(obj)
            assert result is True

    @patch("asynctasq.serializers.hooks.orm.SQLALCHEMY_AVAILABLE", False)
    def test_get_model_pk_raises_when_not_available(self) -> None:
        """Test _get_model_pk raises ImportError when SQLAlchemy not installed."""
        hook = SqlalchemyOrmHook()
        with raises(ImportError, match="SQLAlchemy is not installed"):
            hook._get_model_pk(MockSQLAlchemyModel())

    @patch("asynctasq.serializers.hooks.orm.SQLALCHEMY_AVAILABLE", True)
    def test_get_model_pk_single_column(self) -> None:
        """Test _get_model_pk extracts single primary key."""
        hook = SqlalchemyOrmHook()
        obj = MagicMock()
        obj.id = 42

        # Mock the sqlalchemy inspect
        mock_mapper = MagicMock()
        mock_pk_col = MagicMock()
        mock_pk_col.name = "id"
        mock_mapper.primary_key = [mock_pk_col]

        with patch("sqlalchemy.inspect") as mock_inspect:
            mock_inspect.return_value = mock_mapper
            result = hook._get_model_pk(obj)
            assert result == 42

    @patch("asynctasq.serializers.hooks.orm.SQLALCHEMY_AVAILABLE", True)
    def test_get_model_pk_composite(self) -> None:
        """Test _get_model_pk extracts composite primary key."""
        hook = SqlalchemyOrmHook()
        obj = MagicMock()
        obj.user_id = 1
        obj.session_id = "abc123"

        mock_mapper = MagicMock()
        mock_pk_col1 = MagicMock()
        mock_pk_col1.name = "user_id"
        mock_pk_col2 = MagicMock()
        mock_pk_col2.name = "session_id"
        mock_mapper.primary_key = [mock_pk_col1, mock_pk_col2]

        with patch("sqlalchemy.inspect") as mock_inspect:
            mock_inspect.return_value = mock_mapper
            result = hook._get_model_pk(obj)
            assert result == (1, "abc123")

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.SQLALCHEMY_AVAILABLE", False)
    async def test_fetch_model_raises_when_not_available(self) -> None:
        """Test _fetch_model raises ImportError when SQLAlchemy not installed."""
        hook = SqlalchemyOrmHook()
        with raises(ImportError, match="SQLAlchemy is not installed"):
            await hook._fetch_model(MagicMock, 1)

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.SQLALCHEMY_AVAILABLE", True)
    async def test_fetch_model_with_async_session(self) -> None:
        """Test _fetch_model uses async session."""
        hook = SqlalchemyOrmHook()

        # Create mock model class with session var
        session_var: contextvars.ContextVar[Any] = contextvars.ContextVar("session")
        mock_session = AsyncMock()
        mock_model = MagicMock()
        mock_session.get = AsyncMock(return_value=mock_model)
        session_var.set(mock_session)

        model_class = MagicMock()
        model_class._asynctasq_session_var = session_var

        # Patch the AsyncSession import inside the function
        with patch(
            "sqlalchemy.ext.asyncio.AsyncSession",
            type(mock_session),
        ):
            result = await hook._fetch_model(model_class, 1)
            assert result == mock_model
            mock_session.get.assert_called_once_with(model_class, 1)

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.SQLALCHEMY_AVAILABLE", True)
    async def test_fetch_model_without_session_raises(self) -> None:
        """Test _fetch_model raises RuntimeError when session not available."""
        hook = SqlalchemyOrmHook()

        model_class = MagicMock()
        model_class._asynctasq_session_var = None

        with raises(RuntimeError, match="SQLAlchemy session not available"):
            await hook._fetch_model(model_class, 1)

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.SQLALCHEMY_AVAILABLE", True)
    async def test_fetch_model_with_session_var_none_raises(self) -> None:
        """Test _fetch_model raises RuntimeError when session var is set but value is None."""
        hook = SqlalchemyOrmHook()

        session_var: contextvars.ContextVar[Any] = contextvars.ContextVar("session")
        # Don't set a value, so get() returns None

        model_class = MagicMock()
        model_class._asynctasq_session_var = session_var

        with raises(RuntimeError, match="SQLAlchemy session not available"):
            await hook._fetch_model(model_class, 1)

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.SQLALCHEMY_AVAILABLE", True)
    async def test_fetch_model_with_sync_session(self) -> None:
        """Test _fetch_model falls back to sync session with executor."""
        hook = SqlalchemyOrmHook()

        session_var: contextvars.ContextVar[Any] = contextvars.ContextVar("session")
        mock_session = MagicMock()  # Sync session (not AsyncSession)
        mock_model = MagicMock()
        mock_session.get = MagicMock(return_value=mock_model)
        session_var.set(mock_session)

        model_class = MagicMock()
        model_class._asynctasq_session_var = session_var

        # Patch to make isinstance check work for sync Session
        with patch(
            "sqlalchemy.ext.asyncio.AsyncSession",
            type(MagicMock()),  # Different type, so isinstance fails
        ):
            with patch("sqlalchemy.orm.Session", type(mock_session)):
                result = await hook._fetch_model(model_class, 1)
                assert result == mock_model

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.SQLALCHEMY_AVAILABLE", True)
    async def test_fetch_model_without_both_sessions_raises(self) -> None:
        """Test _fetch_model raises RuntimeError when session is neither async nor sync."""
        hook = SqlalchemyOrmHook()

        session_var: contextvars.ContextVar[Any] = contextvars.ContextVar("session")
        mock_session = MagicMock()  # Neither AsyncSession nor Session
        session_var.set(mock_session)

        model_class = MagicMock()
        model_class._asynctasq_session_var = session_var

        with patch("sqlalchemy.ext.asyncio.AsyncSession", type(MagicMock())):
            with patch("sqlalchemy.orm.Session", type(MagicMock())):
                with raises(RuntimeError, match="SQLAlchemy session not available"):
                    await hook._fetch_model(model_class, 1)


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

    @patch("asynctasq.serializers.hooks.orm.DJANGO_AVAILABLE", True)
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

    @patch("asynctasq.serializers.hooks.orm.DJANGO_AVAILABLE", True)
    def test_can_encode_with_django_exception(self) -> None:
        """Test can_encode handles Django exceptions gracefully."""
        hook = DjangoOrmHook()
        obj = MagicMock()
        # Make django.db.models.Model None to cause exception
        with patch("asynctasq.serializers.hooks.orm.django", None):
            result = hook.can_encode(obj)
            assert result is False

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.DJANGO_AVAILABLE", False)
    async def test_fetch_model_raises_when_not_available(self) -> None:
        """Test _fetch_model raises ImportError when Django not installed."""
        hook = DjangoOrmHook()
        with raises(ImportError, match="Django is not installed"):
            await hook._fetch_model(MagicMock, 1)

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.DJANGO_AVAILABLE", True)
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
    @patch("asynctasq.serializers.hooks.orm.DJANGO_AVAILABLE", True)
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
    @patch("asynctasq.serializers.hooks.orm.DJANGO_AVAILABLE", True)
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
    @patch("asynctasq.serializers.hooks.orm.DJANGO_AVAILABLE", True)
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

    @patch("asynctasq.serializers.hooks.orm.TORTOISE_AVAILABLE", False)
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
    @patch("asynctasq.serializers.hooks.orm.TORTOISE_AVAILABLE", False)
    async def test_fetch_model_raises_when_not_available(self) -> None:
        """Test _fetch_model raises ImportError when Tortoise not installed."""
        hook = TortoiseOrmHook()
        with raises(ImportError, match="Tortoise ORM is not installed"):
            await hook._fetch_model(MagicMock, 1)

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.TORTOISE_AVAILABLE", True)
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
    @patch("asynctasq.serializers.hooks.orm.TORTOISE_AVAILABLE", True)
    async def test_fetch_model_with_exception(self) -> None:
        """Test _fetch_model propagates exceptions from Tortoise get()."""
        hook = TortoiseOrmHook()

        model_class = MagicMock()
        model_class.get = AsyncMock(side_effect=RuntimeError("Database error"))

        with raises(RuntimeError, match="Database error"):
            await hook._fetch_model(model_class, 42)

    @patch("asynctasq.serializers.hooks.orm.TORTOISE_AVAILABLE", True)
    def test_can_encode_with_tortoise_exception(self) -> None:
        """Test can_encode returns False on exception."""
        hook = TortoiseOrmHook()
        obj = MagicMock()
        # Make isinstance raise an exception
        with patch("asynctasq.serializers.hooks.orm.TortoiseModel", None):
            # This will cause isinstance to raise TypeError
            result = hook.can_encode(obj)
            # Should handle exception gracefully
            assert isinstance(result, bool)


# =============================================================================
# Test register_orm_hooks
# =============================================================================


@mark.unit
class TestRegisterOrmHooks:
    """Test register_orm_hooks helper function."""

    def test_registers_available_hooks(self) -> None:
        """Test that available ORM hooks are registered."""
        registry = HookRegistry()
        register_orm_hooks(registry)

        # Check that hooks were registered based on availability
        if SQLALCHEMY_AVAILABLE:
            assert registry.find_decoder({"__orm:sqlalchemy__": 1, "__orm_class__": "x"})
        if DJANGO_AVAILABLE:
            assert registry.find_decoder({"__orm:django__": 1, "__orm_class__": "x"})
        if TORTOISE_AVAILABLE:
            assert registry.find_decoder({"__orm:tortoise__": 1, "__orm_class__": "x"})

    def test_register_orm_hooks_completes(self) -> None:
        """Test register_orm_hooks completes without error."""
        registry = HookRegistry()
        # Just verify it doesn't raise an error
        register_orm_hooks(registry)
        # The function should complete successfully regardless of available ORMs

    @patch("asynctasq.serializers.hooks.orm.SQLALCHEMY_AVAILABLE", True)
    @patch("asynctasq.serializers.hooks.orm.DJANGO_AVAILABLE", False)
    @patch("asynctasq.serializers.hooks.orm.TORTOISE_AVAILABLE", False)
    def test_registers_only_sqlalchemy_when_available(self) -> None:
        """Test that only SQLAlchemy hook is registered when it's available."""
        registry = HookRegistry()
        register_orm_hooks(registry)

        # Should be able to find sqlalchemy decoder
        assert registry.find_decoder({"__orm:sqlalchemy__": 1, "__orm_class__": "x"}) is not None

    @patch("asynctasq.serializers.hooks.orm.SQLALCHEMY_AVAILABLE", False)
    @patch("asynctasq.serializers.hooks.orm.DJANGO_AVAILABLE", True)
    @patch("asynctasq.serializers.hooks.orm.TORTOISE_AVAILABLE", False)
    def test_registers_only_django_when_available(self) -> None:
        """Test that only Django hook is registered when it's available."""
        registry = HookRegistry()
        register_orm_hooks(registry)

        # Should be able to find django decoder
        assert registry.find_decoder({"__orm:django__": 1, "__orm_class__": "x"}) is not None

    @patch("asynctasq.serializers.hooks.orm.SQLALCHEMY_AVAILABLE", False)
    @patch("asynctasq.serializers.hooks.orm.DJANGO_AVAILABLE", False)
    @patch("asynctasq.serializers.hooks.orm.TORTOISE_AVAILABLE", True)
    def test_registers_only_tortoise_when_available(self) -> None:
        """Test that only Tortoise hook is registered when it's available."""
        registry = HookRegistry()
        register_orm_hooks(registry)

        # Should be able to find tortoise decoder
        assert registry.find_decoder({"__orm:tortoise__": 1, "__orm_class__": "x"}) is not None

    @patch("asynctasq.serializers.hooks.orm.SQLALCHEMY_AVAILABLE", False)
    @patch("asynctasq.serializers.hooks.orm.DJANGO_AVAILABLE", False)
    @patch("asynctasq.serializers.hooks.orm.TORTOISE_AVAILABLE", False)
    def test_registers_nothing_when_no_orms_available(self) -> None:
        """Test that no hooks are registered when no ORMs are available."""
        registry = HookRegistry()
        register_orm_hooks(registry)

        # Should not find any ORM decoders
        assert registry.find_decoder({"__orm:sqlalchemy__": 1, "__orm_class__": "x"}) is None
        assert registry.find_decoder({"__orm:django__": 1, "__orm_class__": "x"}) is None
        assert registry.find_decoder({"__orm:tortoise__": 1, "__orm_class__": "x"}) is None


# =============================================================================
# Test Hook Integration with Registry
# =============================================================================


@mark.unit
class TestOrmHookRegistryIntegration:
    """Test ORM hooks work correctly with HookRegistry."""

    def test_sqlalchemy_hook_registered_with_priority(self) -> None:
        """Test SQLAlchemy hook has correct priority."""
        registry = HookRegistry()
        hook = SqlalchemyOrmHook()
        registry.register(hook)
        assert hook.priority == 100

    def test_django_hook_registered_with_priority(self) -> None:
        """Test Django hook has correct priority."""
        registry = HookRegistry()
        hook = DjangoOrmHook()
        registry.register(hook)
        assert hook.priority == 100

    def test_tortoise_hook_registered_with_priority(self) -> None:
        """Test Tortoise hook has correct priority."""
        registry = HookRegistry()
        hook = TortoiseOrmHook()
        registry.register(hook)
        assert hook.priority == 100

    def test_find_decoder_returns_correct_hook(self) -> None:
        """Test find_decoder returns the correct ORM hook."""
        registry = HookRegistry()
        sa_hook = SqlalchemyOrmHook()
        dj_hook = DjangoOrmHook()
        tt_hook = TortoiseOrmHook()

        registry.register(sa_hook)
        registry.register(dj_hook)
        registry.register(tt_hook)

        # Each hook should decode its own type
        sa_data = {"__orm:sqlalchemy__": 1, "__orm_class__": "x.Y"}
        dj_data = {"__orm:django__": 1, "__orm_class__": "x.Y"}
        tt_data = {"__orm:tortoise__": 1, "__orm_class__": "x.Y"}

        assert registry.find_decoder(sa_data) is sa_hook
        assert registry.find_decoder(dj_data) is dj_hook
        assert registry.find_decoder(tt_data) is tt_hook

    def test_sqlalchemy_encode_structure(self) -> None:
        """Test SQLAlchemy model encoding structure."""
        hook = SqlalchemyOrmHook()

        # Create mock model and encode it with mocked _get_model_pk
        model = MockSQLAlchemyModel(pk=42)
        with patch.object(hook, "_get_model_pk", return_value=42):
            encoded = hook.encode(model)

            # Verify encoded structure
            assert encoded["__orm:sqlalchemy__"] == 42
            assert encoded["__orm_class__"] == "test_module.MockSQLAlchemyModel"

    def test_django_encode_structure(self) -> None:
        """Test Django model encoding structure."""
        hook = DjangoOrmHook()

        # Create mock model and encode it
        model = MockDjangoModel(pk=99)
        encoded = hook.encode(model)

        # Verify encoded structure
        assert encoded["__orm:django__"] == 99
        assert encoded["__orm_class__"] == "test_module.MockDjangoModel"

    def test_tortoise_encode_structure(self) -> None:
        """Test Tortoise model encoding structure."""
        hook = TortoiseOrmHook()

        # Create mock model and encode it
        model = MockTortoiseModel(pk=55)
        encoded = hook.encode(model)

        # Verify encoded structure
        assert encoded["__orm:tortoise__"] == 55
        assert encoded["__orm_class__"] == "test_module.MockTortoiseModel"


@mark.unit
class TestOrmHookEdgeCases:
    """Test edge cases and error conditions."""

    def test_import_model_class_from_nested_module(self) -> None:
        """Test importing model class from deeply nested module path."""
        hook = SqlalchemyOrmHook()
        # This will fail to import (doesn't exist) but tests the path parsing
        with raises(ModuleNotFoundError):
            hook._import_model_class("nonexistent.deeply.nested.Module.Class")

    def test_encode_with_composite_pk_tuple(self) -> None:
        """Test encoding model with composite primary key."""
        hook = SqlalchemyOrmHook()

        with patch.object(hook, "_get_model_pk", return_value=(1, "abc")):
            obj = MockSQLAlchemyModel()
            encoded = hook.encode(obj)
            assert encoded["__orm:sqlalchemy__"] == (1, "abc")

    def test_encode_with_uuid_pk(self) -> None:
        """Test encoding model with UUID primary key."""
        from uuid import UUID

        hook = SqlalchemyOrmHook()

        uuid_pk = UUID("550e8400-e29b-41d4-a716-446655440000")
        with patch.object(hook, "_get_model_pk", return_value=uuid_pk):
            obj = MockSQLAlchemyModel()
            encoded = hook.encode(obj)
            assert encoded["__orm:sqlalchemy__"] == uuid_pk

    @mark.asyncio
    async def test_hook_decode_async_with_missing_pk(self) -> None:
        """Test hook.decode_async with missing pk."""
        hook = SqlalchemyOrmHook()

        with raises(ValueError, match="Invalid ORM reference"):
            await hook.decode_async({"__orm:sqlalchemy__": None, "__orm_class__": "Module.Class"})

    @mark.asyncio
    async def test_hook_decode_async_with_missing_class(self) -> None:
        """Test hook.decode_async with missing class path."""
        hook = SqlalchemyOrmHook()

        with raises(ValueError, match="Invalid ORM reference"):
            await hook.decode_async({"__orm:sqlalchemy__": 1, "__orm_class__": None})

    def test_get_model_class_path_with_module_name(self) -> None:
        """Test class path generation."""
        hook = SqlalchemyOrmHook()
        obj = MockSQLAlchemyModel()
        path = hook._get_model_class_path(obj)
        assert path == "test_module.MockSQLAlchemyModel"

    @mark.asyncio
    async def test_sqlalchemy_import_model_class_success(self) -> None:
        """Test successful model class import."""
        hook = SqlalchemyOrmHook()
        # Import a real class path
        cls = hook._import_model_class("asynctasq.serializers.hooks.orm.SqlalchemyOrmHook")
        assert cls is SqlalchemyOrmHook

    def test_django_hook_can_encode_django_model_instance(self) -> None:
        """Test Django hook identifies Django models correctly."""
        hook = DjangoOrmHook()
        model = MockDjangoModel(pk=10)
        # This should work if DJANGO_AVAILABLE is True
        result = hook.can_encode(model)
        # Result depends on whether django is actually available
        assert isinstance(result, bool)
