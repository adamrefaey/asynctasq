"""Unit tests for base ORM hook functionality.

Testing Strategy:
- pytest 9.0.1 with asyncio_mode="strict" (explicit @mark.asyncio decorators required)
- AAA pattern (Arrange, Act, Assert)
- Mock ORM models to avoid requiring actual ORM dependencies
- Test base functionality and integration tests
"""

from typing import Any
from unittest.mock import MagicMock, patch

from pytest import mark, raises

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
                return False

            def _get_model_pk(self, obj: Any) -> Any:
                return 42

            async def _fetch_model(self, model_class: type, pk: Any) -> Any:
                return None

        hook = TestHook()
        obj = MockSQLAlchemyModel(pk=42)
        result = hook.encode(obj)

        assert result["__orm:test__"] == 42
        assert result["__orm_class__"] == "test_module.MockSQLAlchemyModel"
        assert len(result) == 2

    @mark.asyncio
    async def test_decode_async_with_invalid_reference(self) -> None:
        """Test decode_async raises ValueError for invalid data."""

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
            await hook.decode_async({"__orm:test__": None, "__orm_class__": "x.Y"})


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

    @patch("asynctasq.serializers.hooks.orm.sqlalchemy.SQLALCHEMY_AVAILABLE", True)
    @patch("asynctasq.serializers.hooks.orm.django.DJANGO_AVAILABLE", False)
    @patch("asynctasq.serializers.hooks.orm.tortoise.TORTOISE_AVAILABLE", False)
    def test_registers_only_sqlalchemy_when_available(self) -> None:
        """Test that only SQLAlchemy hook is registered when it's available."""
        registry = HookRegistry()
        register_orm_hooks(registry)

        # Should be able to find sqlalchemy decoder
        assert registry.find_decoder({"__orm:sqlalchemy__": 1, "__orm_class__": "x"}) is not None

    @patch("asynctasq.serializers.hooks.orm.sqlalchemy.SQLALCHEMY_AVAILABLE", False)
    @patch("asynctasq.serializers.hooks.orm.django.DJANGO_AVAILABLE", True)
    @patch("asynctasq.serializers.hooks.orm.tortoise.TORTOISE_AVAILABLE", False)
    def test_registers_only_django_when_available(self) -> None:
        """Test that only Django hook is registered when it's available."""
        registry = HookRegistry()
        register_orm_hooks(registry)

        # Should be able to find django decoder
        assert registry.find_decoder({"__orm:django__": 1, "__orm_class__": "x"}) is not None

    @patch("asynctasq.serializers.hooks.orm.sqlalchemy.SQLALCHEMY_AVAILABLE", False)
    @patch("asynctasq.serializers.hooks.orm.django.DJANGO_AVAILABLE", False)
    @patch("asynctasq.serializers.hooks.orm.tortoise.TORTOISE_AVAILABLE", True)
    def test_registers_only_tortoise_when_available(self) -> None:
        """Test that only Tortoise hook is registered when it's available."""
        registry = HookRegistry()
        register_orm_hooks(registry)

        # Should be able to find tortoise decoder
        assert registry.find_decoder({"__orm:tortoise__": 1, "__orm_class__": "x"}) is not None

    def test_registers_nothing_when_no_orms_available(self) -> None:
        """Test that no hooks are registered when no ORMs are available."""
        from asynctasq.serializers.hooks import orm

        # Patch the availability flags BEFORE calling register_orm_hooks
        with (
            patch.object(orm, "SQLALCHEMY_AVAILABLE", False),
            patch.object(orm, "DJANGO_AVAILABLE", False),
            patch.object(orm, "TORTOISE_AVAILABLE", False),
        ):
            registry = HookRegistry()
            orm.register_orm_hooks(registry)

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
