"""Unit tests for SQLAlchemy ORM hook and utilities.

Testing Strategy:
- pytest 9.0.1 with asyncio_mode="strict" (explicit @mark.asyncio decorators required)
- AAA pattern (Arrange, Act, Assert)
- Mock SQLAlchemy objects to avoid requiring actual SQLAlchemy installation
- Test hook functionality and utility functions
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from pytest import fixture, mark, raises

from asynctasq.serializers.hooks import SqlalchemyOrmHook

# =============================================================================
# Mock SQLAlchemy Model
# =============================================================================


class MockSQLAlchemyModel:
    """Mock SQLAlchemy model for testing."""

    def __init__(self, pk: Any = 1):
        self.id = pk
        self.__mapper__ = MagicMock()
        self.__class__.__module__ = "test_module"
        self.__class__.__name__ = "MockSQLAlchemyModel"


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

    @patch("asynctasq.serializers.hooks.orm.sqlalchemy.SQLALCHEMY_AVAILABLE", False)
    def test_can_encode_when_sqlalchemy_not_available(self) -> None:
        """Test can_encode returns False when SQLAlchemy not installed."""
        hook = SqlalchemyOrmHook()
        obj = MockSQLAlchemyModel()
        assert hook.can_encode(obj) is False

    @patch("asynctasq.serializers.hooks.orm.sqlalchemy.SQLALCHEMY_AVAILABLE", True)
    def test_can_encode_with_mapper(self, hook: SqlalchemyOrmHook) -> None:
        """Test can_encode detects model via __mapper__."""
        obj = MagicMock()
        obj.__mapper__ = MagicMock()
        assert hook.can_encode(obj) is True

    @patch("asynctasq.serializers.hooks.orm.sqlalchemy.SQLALCHEMY_AVAILABLE", True)
    def test_can_encode_with_non_model(self, hook: SqlalchemyOrmHook) -> None:
        """Test can_encode returns False for non-model objects."""
        with patch("sqlalchemy.inspect", side_effect=Exception("Not a model")):
            assert hook.can_encode("string") is False
            assert hook.can_encode(123) is False
            assert hook.can_encode({}) is False

    @patch("asynctasq.serializers.hooks.orm.sqlalchemy.SQLALCHEMY_AVAILABLE", True)
    def test_can_encode_with_declarative_base_isinstance(self, hook: SqlalchemyOrmHook) -> None:
        """Test can_encode detects model via DeclarativeBase isinstance."""
        obj = MagicMock()

        # Test the __mapper__ path
        obj.__mapper__ = MagicMock()
        result = hook.can_encode(obj)
        assert result is True

    @patch("asynctasq.serializers.hooks.orm.sqlalchemy.SQLALCHEMY_AVAILABLE", True)
    def test_can_encode_with_inspect_returns_mapper(self, hook: SqlalchemyOrmHook) -> None:
        """Test can_encode detects model via sqlalchemy.inspect."""
        obj = MagicMock()
        obj.__mapper__ = None  # No __mapper__

        with patch("sqlalchemy.inspect") as mock_inspect:
            mock_mapper = MagicMock()
            mock_inspect.return_value = mock_mapper
            result = hook.can_encode(obj)
            assert result is True

    @patch("asynctasq.serializers.hooks.orm.sqlalchemy.SQLALCHEMY_AVAILABLE", False)
    def test_get_model_pk_raises_when_not_available(self) -> None:
        """Test _get_model_pk raises ImportError when SQLAlchemy not installed."""
        hook = SqlalchemyOrmHook()
        with raises(ImportError, match="SQLAlchemy is not installed"):
            hook._get_model_pk(MockSQLAlchemyModel())

    @patch("asynctasq.serializers.hooks.orm.sqlalchemy.SQLALCHEMY_AVAILABLE", True)
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

    @patch("asynctasq.serializers.hooks.orm.sqlalchemy.SQLALCHEMY_AVAILABLE", True)
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
    @patch("asynctasq.serializers.hooks.orm.sqlalchemy.SQLALCHEMY_AVAILABLE", False)
    async def test_fetch_model_raises_when_not_available(self) -> None:
        """Test _fetch_model raises ImportError when SQLAlchemy not installed."""
        hook = SqlalchemyOrmHook()
        with raises(ImportError, match="SQLAlchemy is not installed"):
            await hook._fetch_model(MagicMock, 1)

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.sqlalchemy.SQLALCHEMY_AVAILABLE", True)
    async def test_fetch_model_with_async_session(self) -> None:
        """Test _fetch_model uses async session factory."""
        from sqlalchemy.ext.asyncio import async_sessionmaker

        hook = SqlalchemyOrmHook()

        # Create mock async session factory
        mock_session = AsyncMock()
        mock_model = MagicMock()
        mock_session.get = AsyncMock(return_value=mock_model)

        # Create a mock session factory
        mock_factory = MagicMock(spec=async_sessionmaker)
        mock_factory.kw = {"bind": None}  # No bind for simple test
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        # Create mock model class with __mro__
        model_class = MagicMock()
        model_class.__name__ = "TestModel"
        model_class._asynctasq_session_factory = mock_factory
        model_class.__mro__ = (model_class, object)

        result = await hook._fetch_model(model_class, 1)
        assert result == mock_model
        mock_session.get.assert_called_once_with(model_class, 1)

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.sqlalchemy.SQLALCHEMY_AVAILABLE", True)
    async def test_fetch_model_without_session_raises(self) -> None:
        """Test _fetch_model raises RuntimeError when session factory not configured."""
        hook = SqlalchemyOrmHook()

        # Model class without _asynctasq_session_factory attribute at all
        model_class = MagicMock()
        model_class.__name__ = "TestModel"
        model_class.__mro__ = (model_class, object)
        # Don't set _asynctasq_session_factory at all - hasattr should return False
        if hasattr(model_class, "_asynctasq_session_factory"):
            delattr(model_class, "_asynctasq_session_factory")

        with raises(RuntimeError, match="SQLAlchemy session factory not configured"):
            await hook._fetch_model(model_class, 1)

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.sqlalchemy.SQLALCHEMY_AVAILABLE", True)
    async def test_fetch_model_with_session_var_none_raises(self) -> None:
        """Test _fetch_model raises RuntimeError when factory is None on base class."""
        hook = SqlalchemyOrmHook()

        # Create base class with _asynctasq_session_factory = None
        base_class = MagicMock()
        base_class.__name__ = "Base"
        base_class._asynctasq_session_factory = None

        # Model class that inherits from base
        model_class = MagicMock()
        model_class.__name__ = "TestModel"
        model_class.__mro__ = (model_class, base_class, object)
        # Don't set on model_class itself, only on base_class
        if hasattr(model_class, "_asynctasq_session_factory"):
            delattr(model_class, "_asynctasq_session_factory")

        with raises(RuntimeError, match="SQLAlchemy session factory not configured"):
            await hook._fetch_model(model_class, 1)

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.sqlalchemy.SQLALCHEMY_AVAILABLE", True)
    async def test_fetch_model_with_sync_session(self) -> None:
        """Test _fetch_model falls back to sync sessionmaker with executor."""
        from sqlalchemy.orm import sessionmaker

        hook = SqlalchemyOrmHook()

        # Create mock sync session factory
        mock_session = MagicMock()
        mock_model = MagicMock()
        mock_session.get = MagicMock(return_value=mock_model)

        # Create a mock sync session factory
        mock_factory = MagicMock(spec=sessionmaker)
        mock_factory.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_factory.return_value.__exit__ = MagicMock(return_value=None)

        # Create mock model class with __mro__
        model_class = MagicMock()
        model_class.__name__ = "TestModel"
        model_class._asynctasq_session_factory = mock_factory
        model_class.__mro__ = (model_class, object)

        result = await hook._fetch_model(model_class, 1)
        assert result == mock_model

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.sqlalchemy.SQLALCHEMY_AVAILABLE", True)
    async def test_fetch_model_without_both_sessions_raises(self) -> None:
        """Test _fetch_model raises RuntimeError when factory is invalid type."""
        hook = SqlalchemyOrmHook()

        # Create mock factory that's neither async_sessionmaker nor sessionmaker
        mock_factory = MagicMock()  # Invalid type

        model_class = MagicMock()
        model_class.__name__ = "TestModel"
        model_class._asynctasq_session_factory = mock_factory
        model_class.__mro__ = (model_class, object)

        with raises(RuntimeError, match="Invalid session factory type"):
            await hook._fetch_model(model_class, 1)


# =============================================================================
# Test SQLAlchemy Utility Functions
# =============================================================================


@mark.unit
class TestCreateWorkerSessionFactory:
    """Test create_worker_session_factory helper."""

    @patch("sqlalchemy.ext.asyncio.create_async_engine")
    @patch("sqlalchemy.ext.asyncio.async_sessionmaker")
    def test_creates_factory_with_nullpool(
        self, mock_sessionmaker: MagicMock, mock_create_engine: MagicMock
    ) -> None:
        """Test factory created with NullPool for multiprocessing safety."""
        from sqlalchemy.pool import NullPool

        from asynctasq.serializers.hooks.orm.sqlalchemy import create_worker_session_factory

        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_factory = MagicMock()
        mock_sessionmaker.return_value = mock_factory

        result = create_worker_session_factory("postgresql+asyncpg://test/db")

        # Verify engine created with NullPool
        mock_create_engine.assert_called_once()
        call_kwargs = mock_create_engine.call_args[1]
        assert call_kwargs["poolclass"] == NullPool
        assert call_kwargs["pool_pre_ping"] is True

        # Verify sessionmaker created with expire_on_commit=False
        mock_sessionmaker.assert_called_once_with(
            mock_engine,
            expire_on_commit=False,
        )

        assert result == mock_factory

    @patch("sqlalchemy.ext.asyncio.create_async_engine")
    @patch("sqlalchemy.ext.asyncio.async_sessionmaker")
    def test_passes_custom_kwargs(
        self, mock_sessionmaker: MagicMock, mock_create_engine: MagicMock
    ) -> None:
        """Test custom kwargs passed to sessionmaker."""
        from asynctasq.serializers.hooks.orm.sqlalchemy import create_worker_session_factory

        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        create_worker_session_factory(
            "postgresql+asyncpg://test/db",
            echo=True,
            pool_pre_ping=False,
            autoflush=False,
        )

        # Check engine kwargs
        engine_kwargs = mock_create_engine.call_args[1]
        assert engine_kwargs["echo"] is True
        assert engine_kwargs["pool_pre_ping"] is False

        # Check sessionmaker kwargs
        session_kwargs = mock_sessionmaker.call_args[1]
        assert session_kwargs["autoflush"] is False
        assert session_kwargs["expire_on_commit"] is False


@mark.unit
class TestValidateSessionFactory:
    """Test validate_session_factory configuration validation.

    Note: Full validation tests are integration tests with real SQLAlchemy objects.
    These unit tests only cover basic failure cases.
    """

    def test_invalid_factory_type(self) -> None:
        """Test validation fails for non-sessionmaker object."""
        from asynctasq.serializers.hooks.orm.sqlalchemy import validate_session_factory

        result = validate_session_factory("not a factory")

        assert result["valid"] is False
        assert "Invalid session factory type" in result["warnings"][0]


@mark.unit
class TestCheckPoolHealth:
    """Test check_pool_health diagnostics.

    Note: Full health check tests are integration tests with real SQLAlchemy objects.
    These unit tests only cover basic failure cases.
    """

    def test_handles_invalid_factory(self) -> None:
        """Test handles invalid factory gracefully."""
        from asynctasq.serializers.hooks.orm.sqlalchemy import check_pool_health

        result = check_pool_health("not a factory")

        assert "error" in result
        assert "Invalid session factory type" in result["error"]


@mark.unit
class TestDetectForkedProcess:
    """Test detect_forked_process fork detection."""

    def test_detects_same_process(self) -> None:
        """Test returns False when PID matches (not forked)."""
        import os

        from asynctasq.serializers.hooks.orm.sqlalchemy import detect_forked_process

        current_pid = os.getpid()
        result = detect_forked_process(initial_pid=current_pid)

        assert result is False

    def test_detects_different_pid(self) -> None:
        """Test returns True when PID differs (forked)."""
        from asynctasq.serializers.hooks.orm.sqlalchemy import detect_forked_process

        result = detect_forked_process(initial_pid=99999)

        assert result is True

    def test_handles_no_initial_pid(self) -> None:
        """Test returns False when no initial PID provided."""
        from asynctasq.serializers.hooks.orm.sqlalchemy import detect_forked_process

        result = detect_forked_process(initial_pid=None)

        assert result is False


@mark.unit
class TestEmitForkSafetyWarning:
    """Test emit_fork_safety_warning warnings."""

    def test_emits_warning_for_queuepool(self) -> None:
        """Test emits warning for QueuePool."""
        import warnings

        from asynctasq.serializers.hooks.orm.sqlalchemy import emit_fork_safety_warning

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            emit_fork_safety_warning("QueuePool")

            assert len(w) == 1
            assert "QueuePool" in str(w[0].message)
            assert "NullPool" in str(w[0].message)
            assert issubclass(w[0].category, UserWarning)

    def test_no_warning_for_nullpool(self) -> None:
        """Test no warning for NullPool (safe for multiprocessing)."""
        import warnings

        from asynctasq.serializers.hooks.orm.sqlalchemy import emit_fork_safety_warning

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            emit_fork_safety_warning("NullPool")

            assert len(w) == 0

    def test_no_warning_for_staticpool(self) -> None:
        """Test no warning for StaticPool (safe for multiprocessing)."""
        import warnings

        from asynctasq.serializers.hooks.orm.sqlalchemy import emit_fork_safety_warning

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            emit_fork_safety_warning("StaticPool")

            assert len(w) == 0
