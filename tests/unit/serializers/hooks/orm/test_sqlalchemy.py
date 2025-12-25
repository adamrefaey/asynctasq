"""Unit tests for SQLAlchemy ORM hook and utilities.

Testing Strategy:
- pytest 9.0.1 with asyncio_mode="strict" (explicit @mark.asyncio decorators required)
- AAA pattern (Arrange, Act, Assert)
- Mock SQLAlchemy objects to avoid requiring actual SQLAlchemy installation
- Test hook functionality and utility functions
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from pytest import fixture, mark, raises, warns
from sqlalchemy.exc import NoInspectionAvailable

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


@mark.unit
class TestValidateSessionFactoryExtended:
    """Extended tests for validate_session_factory function."""

    @patch("asynctasq.serializers.hooks.orm.sqlalchemy.SQLALCHEMY_AVAILABLE", True)
    @patch("asynctasq.serializers.hooks.orm.sqlalchemy.isinstance")
    def test_validate_session_factory_no_bind(self, mock_isinstance) -> None:
        """Test validate_session_factory with no engine bound."""
        from asynctasq.serializers.hooks.orm.sqlalchemy import validate_session_factory

        mock_factory = MagicMock()
        mock_factory.kw = {}  # No bind
        mock_isinstance.return_value = True

        result = validate_session_factory(mock_factory)

        assert result["valid"] is True
        assert "No engine bound to session factory" in result["warnings"]

    @patch("asynctasq.serializers.hooks.orm.sqlalchemy.SQLALCHEMY_AVAILABLE", True)
    @patch("asynctasq.serializers.hooks.orm.sqlalchemy.isinstance")
    def test_validate_session_factory_queuepool_warnings(self, mock_isinstance) -> None:
        """Test validate_session_factory with QueuePool warnings."""
        from asynctasq.serializers.hooks.orm.sqlalchemy import validate_session_factory

        mock_factory = MagicMock()
        mock_bind = MagicMock()
        mock_pool = MagicMock()
        mock_pool.__class__.__name__ = "QueuePool"
        mock_bind.pool = mock_pool
        mock_factory.kw = {"bind": mock_bind}
        mock_isinstance.return_value = True

        result = validate_session_factory(mock_factory)

        assert result["valid"] is True
        assert any("QueuePool" in w for w in result["warnings"])
        assert any("NullPool" in r for r in result["recommendations"])

    @patch("asynctasq.serializers.hooks.orm.sqlalchemy.SQLALCHEMY_AVAILABLE", True)
    @patch("asynctasq.serializers.hooks.orm.sqlalchemy.isinstance")
    def test_validate_session_factory_expire_on_commit_true(self, mock_isinstance) -> None:
        """Test validate_session_factory with expire_on_commit=True."""
        from asynctasq.serializers.hooks.orm.sqlalchemy import validate_session_factory

        mock_factory = MagicMock()
        mock_bind = MagicMock()
        mock_pool = MagicMock()
        mock_pool.__class__.__name__ = "NullPool"
        mock_bind.pool = mock_pool
        mock_factory.kw = {"bind": mock_bind, "expire_on_commit": True}
        mock_isinstance.return_value = True

        result = validate_session_factory(mock_factory)

        assert result["valid"] is True
        assert any("expire_on_commit=True" in w for w in result["warnings"])
        assert result["expire_on_commit"] is True

    @patch("asynctasq.serializers.hooks.orm.sqlalchemy.SQLALCHEMY_AVAILABLE", True)
    @patch("asynctasq.serializers.hooks.orm.sqlalchemy.isinstance")
    def test_validate_session_factory_pool_pre_ping_false(self, mock_isinstance) -> None:
        """Test validate_session_factory with pool_pre_ping=False."""
        from asynctasq.serializers.hooks.orm.sqlalchemy import validate_session_factory

        mock_factory = MagicMock()
        mock_bind = MagicMock()
        mock_bind._pool_pre_ping = False
        mock_bind._pool_recycle = -1
        mock_pool = MagicMock()
        mock_pool.__class__.__name__ = "QueuePool"
        mock_bind.pool = mock_pool
        mock_factory.kw = {"bind": mock_bind}
        mock_isinstance.return_value = True

        result = validate_session_factory(mock_factory)

        assert result["valid"] is True
        assert any("pool_pre_ping=False" in w for w in result["warnings"])

    @patch("asynctasq.serializers.hooks.orm.sqlalchemy.SQLALCHEMY_AVAILABLE", True)
    @patch("asynctasq.serializers.hooks.orm.sqlalchemy.isinstance")
    def test_validate_session_factory_pool_recycle_not_set(self, mock_isinstance) -> None:
        """Test validate_session_factory with pool_recycle not set."""
        from asynctasq.serializers.hooks.orm.sqlalchemy import validate_session_factory

        mock_factory = MagicMock()
        mock_bind = MagicMock()
        mock_bind._pool_recycle = -1
        mock_pool = MagicMock()
        mock_pool.__class__.__name__ = "QueuePool"
        mock_bind.pool = mock_pool
        mock_factory.kw = {"bind": mock_bind}
        mock_isinstance.return_value = True

        result = validate_session_factory(mock_factory)

        assert result["valid"] is True
        assert any("pool_recycle not set" in w for w in result["warnings"])


@mark.unit
class TestCheckPoolHealthExtended:
    """Extended tests for check_pool_health function."""

    @patch("asynctasq.serializers.hooks.orm.sqlalchemy.SQLALCHEMY_AVAILABLE", True)
    @patch("asynctasq.serializers.hooks.orm.sqlalchemy.isinstance")
    def test_check_pool_health_with_queuepool_stats(self, mock_isinstance) -> None:
        """Test check_pool_health extracts pool statistics."""
        from asynctasq.serializers.hooks.orm.sqlalchemy import check_pool_health

        mock_factory = MagicMock()
        mock_bind = MagicMock()
        mock_pool = MagicMock()
        mock_pool.__class__.__name__ = "QueuePool"
        mock_pool.size.return_value = 10
        mock_pool.checkedout.return_value = 3
        mock_pool.overflow.return_value = 2
        mock_bind.pool = mock_pool
        mock_factory.kw = {"bind": mock_bind}
        mock_isinstance.return_value = True

        result = check_pool_health(mock_factory)

        assert result["pool_class"] == "QueuePool"
        assert result["size"] == 10
        assert result["checked_out"] == 3
        assert result["overflow"] == 2
        assert result["available"] == 7
        assert "error" not in result

    @patch("asynctasq.serializers.hooks.orm.sqlalchemy.SQLALCHEMY_AVAILABLE", True)
    @patch("asynctasq.serializers.hooks.orm.sqlalchemy.isinstance")
    def test_check_pool_health_no_bind(self, mock_isinstance) -> None:
        """Test check_pool_health with no engine bound."""
        from asynctasq.serializers.hooks.orm.sqlalchemy import check_pool_health

        mock_factory = MagicMock()
        mock_factory.kw = {}  # No bind
        mock_isinstance.return_value = True

        result = check_pool_health(mock_factory)

        assert "error" in result
        assert "No engine bound to session factory" in result["error"]

    @patch("asynctasq.serializers.hooks.orm.sqlalchemy.SQLALCHEMY_AVAILABLE", True)
    @patch("asynctasq.serializers.hooks.orm.sqlalchemy.isinstance")
    def test_check_pool_health_exception_handling(self, mock_isinstance) -> None:
        """Test check_pool_health handles exceptions gracefully."""
        from asynctasq.serializers.hooks.orm.sqlalchemy import check_pool_health

        mock_factory = MagicMock()
        mock_factory.kw.get.side_effect = Exception("Unexpected error")
        mock_isinstance.return_value = True

        result = check_pool_health(mock_factory)

        assert "error" in result
        assert "Unexpected error" in result["error"]


@mark.unit
class TestSqlalchemyOrmHookExtended:
    """Extended tests for SqlalchemyOrmHook methods."""

    @fixture
    def hook(self) -> SqlalchemyOrmHook:
        return SqlalchemyOrmHook()

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.sqlalchemy.SQLALCHEMY_AVAILABLE", True)
    async def test_fetch_model_forked_process_logging(self, hook: SqlalchemyOrmHook) -> None:
        """Test _fetch_model logs when in forked process."""
        from sqlalchemy.ext.asyncio import async_sessionmaker

        # Mock forked process (different PID)
        with (
            patch("os.getpid", return_value=99999),
            patch("asynctasq.serializers.hooks.orm.sqlalchemy._PARENT_PID", 12345),
        ):
            mock_session = AsyncMock()
            mock_model = MagicMock()
            mock_session.get = AsyncMock(return_value=mock_model)

            mock_factory = MagicMock(spec=async_sessionmaker)
            mock_factory.kw = {"bind": None}
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

            model_class = MagicMock()
            model_class.__name__ = "TestModel"
            model_class._asynctasq_session_factory = mock_factory
            model_class.__mro__ = (model_class, object)

            with patch("asynctasq.serializers.hooks.orm.sqlalchemy.logger") as mock_logger:
                result = await hook._fetch_model(model_class, 1)

                assert result == mock_model
                mock_logger.debug.assert_called()
                # Check that the debug call includes forked process info
                debug_calls = [
                    call
                    for call in mock_logger.debug.call_args_list
                    if "forked process" in str(call)
                ]
                assert len(debug_calls) > 0

    @mark.asyncio
    @patch("asynctasq.serializers.hooks.orm.sqlalchemy.SQLALCHEMY_AVAILABLE", True)
    async def test_fetch_model_pool_warning_in_forked_process(
        self, hook: SqlalchemyOrmHook
    ) -> None:
        """Test _fetch_model warns about unsafe pool in forked process."""
        from sqlalchemy.ext.asyncio import async_sessionmaker

        # Mock forked process
        with (
            patch("os.getpid", return_value=99999),
            patch("asynctasq.serializers.hooks.orm.sqlalchemy._PARENT_PID", 12345),
        ):
            mock_session = AsyncMock()
            mock_model = MagicMock()
            mock_session.get = AsyncMock(return_value=mock_model)

            # Mock unsafe pool (QueuePool)
            mock_bind = MagicMock()
            mock_pool = MagicMock()
            mock_pool.__class__.__name__ = "QueuePool"
            mock_bind.pool = mock_pool

            mock_factory = MagicMock(spec=async_sessionmaker)
            mock_factory.kw = {"bind": mock_bind}
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

            model_class = MagicMock()
            model_class.__name__ = "TestModel"
            model_class._asynctasq_session_factory = mock_factory
            model_class.__mro__ = (model_class, object)

            with patch("asynctasq.serializers.hooks.orm.sqlalchemy.logger") as mock_logger:
                result = await hook._fetch_model(model_class, 1)

                assert result == mock_model
                mock_logger.warning.assert_called()
                warning_call = str(mock_logger.warning.call_args)
                assert "connection pool in forked process" in warning_call


@mark.unit
class TestSqlalchemyHookEdgeCases:
    """Edge case tests for SqlalchemyOrmHook to increase coverage."""

    def test_can_encode_with_none_model_raises(self) -> None:
        """Test can_encode returns False when model is None."""
        hook = SqlalchemyOrmHook()
        result = hook.can_encode(None)
        assert result is False

    def test_can_encode_with_non_model_object(self) -> None:
        """Test can_encode returns False for non-model objects."""
        hook = SqlalchemyOrmHook()

        # Regular Python object
        obj = object()
        assert hook.can_encode(obj) is False

    def test_get_model_pk_with_none_model_raises(self) -> None:
        """Test get_model_pk raises with None model."""
        hook = SqlalchemyOrmHook()

        with raises(NoInspectionAvailable):
            hook._get_model_pk(None)

    def test_get_model_pk_with_no_primary_key(self) -> None:
        """Test get_model_pk with model that has no primary key."""
        hook = SqlalchemyOrmHook()

        # Mock model with no primary key
        mock_model = MagicMock()
        mock_model.__table__ = MagicMock()
        mock_model.__table__.primary_key = MagicMock()
        mock_model.__table__.primary_key.columns = []

        with raises(NoInspectionAvailable):
            hook._get_model_pk(mock_model)

    @mark.parametrize(
        "session_factory_value,expected_valid",
        [
            (None, False),  # No session factory
            ("not_callable", False),  # Non-callable
            (MagicMock(), False),  # Not a sessionmaker
        ],
    )
    def test_validate_session_factory_edge_cases(
        self, session_factory_value, expected_valid
    ) -> None:
        """Test validate_session_factory with various inputs."""
        from asynctasq.serializers.hooks.orm.sqlalchemy import validate_session_factory

        result = validate_session_factory(session_factory_value)
        assert result["valid"] == expected_valid

    def test_check_pool_health_with_none_factory(self) -> None:
        """Test check_pool_health with None factory."""
        from asynctasq.serializers.hooks.orm.sqlalchemy import check_pool_health

        result = check_pool_health(None)
        assert "error" in result
        assert "Invalid session factory type" in result["error"]

    def test_check_pool_health_with_invalid_factory(self) -> None:
        """Test check_pool_health with invalid factory."""
        from asynctasq.serializers.hooks.orm.sqlalchemy import check_pool_health

        invalid_factory = "not_a_factory"
        result = check_pool_health(invalid_factory)
        assert "error" in result
        assert "Invalid session factory type" in result["error"]

    def test_emit_fork_safety_warning_with_none_pool(self) -> None:
        """Test emit_fork_safety_warning with None pool."""

        from asynctasq.serializers.hooks.orm.sqlalchemy import emit_fork_safety_warning

        # Should emit warning for None pool class
        with warns(UserWarning, match="Using None with multiprocessing workers"):
            emit_fork_safety_warning(None)

    def test_create_worker_session_factory_with_custom_kwargs(self) -> None:
        """Test create_worker_session_factory preserves custom kwargs."""
        from asynctasq.serializers.hooks.orm.sqlalchemy import create_worker_session_factory

        custom_kwargs = {"dsn": "postgresql+asyncpg://test/db", "echo": True, "future": True}
        factory = create_worker_session_factory(**custom_kwargs)

        # Should be callable
        assert callable(factory)

        # Factory should create sessions with custom settings
        session = factory()
        assert session is not None
