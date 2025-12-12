"""SQLAlchemy ORM hook implementation with utilities."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any
import warnings

from .base import BaseOrmHook

# Setup library logger with NullHandler (best practice for libraries)
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Store parent PID for fork detection
_PARENT_PID = os.getpid()

# =============================================================================
# SQLAlchemy Availability Detection
# =============================================================================

try:
    from sqlalchemy.orm import DeclarativeBase

    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    DeclarativeBase = None  # type: ignore[assignment, misc]


# =============================================================================
# SQLAlchemy Hook
# =============================================================================


class SqlalchemyOrmHook(BaseOrmHook):
    """Hook for SQLAlchemy model serialization.

    Supports both async and sync SQLAlchemy sessions.
    Session factory must be configured on the model class or base class.

    Example:
        >>> from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
        >>> from sqlalchemy.pool import NullPool
        >>>
        >>> # For async workers with multiprocessing:
        >>> engine = create_async_engine("postgresql+asyncpg://...", poolclass=NullPool)
        >>> session_factory = async_sessionmaker(engine, expire_on_commit=False)
        >>> Base._asynctasq_session_factory = session_factory
        >>>
        >>> # Or use the helper function:
        >>> from asynctasq.serializers.hooks.orm.sqlalchemy import create_worker_session_factory
        >>> Base._asynctasq_session_factory = create_worker_session_factory(
        ...     "postgresql+asyncpg://..."
        ... )
    """

    orm_name = "sqlalchemy"
    priority = 100  # High priority for ORM detection

    def can_encode(self, obj: Any) -> bool:
        """Check if object is a SQLAlchemy model."""
        if not SQLALCHEMY_AVAILABLE:
            return False
        try:
            from sqlalchemy import inspect as sqlalchemy_inspect

            return (
                hasattr(obj, "__mapper__")
                or (DeclarativeBase is not None and isinstance(obj, DeclarativeBase))
                or sqlalchemy_inspect(obj, raiseerr=False) is not None
            )
        except Exception:
            return False

    def _get_model_pk(self, obj: Any) -> Any:
        """Extract primary key from SQLAlchemy model."""
        if not SQLALCHEMY_AVAILABLE:
            raise ImportError("SQLAlchemy is not installed")

        from sqlalchemy import inspect as sqlalchemy_inspect

        mapper = sqlalchemy_inspect(obj.__class__)
        pk_columns = mapper.primary_key

        if len(pk_columns) == 1:
            return getattr(obj, pk_columns[0].name)
        else:
            # Composite primary key - return tuple
            return tuple(getattr(obj, col.name) for col in pk_columns)

    async def _fetch_model(self, model_class: type, pk: Any) -> Any:
        """Fetch SQLAlchemy model from database using session factory.

        Walks model's MRO to find _asynctasq_session_factory on any base class.

        Important: For multiprocessing workers, use NullPool to avoid connection pool
        sharing across forked processes:

            from asynctasq.serializers.hooks import create_worker_session_factory
            Base._asynctasq_session_factory = create_worker_session_factory(dsn)

        See: https://docs.sqlalchemy.org/en/20/core/pooling.html#using-connection-pools-with-multiprocessing
        """
        if not SQLALCHEMY_AVAILABLE:
            raise ImportError("SQLAlchemy is not installed")

        # Detect if we're in a forked process (worker)
        current_pid = os.getpid()
        if current_pid != _PARENT_PID:
            logger.debug(
                "Fetching model in forked process",
                extra={
                    "model_class": getattr(model_class, "__name__", repr(model_class)),
                    "parent_pid": _PARENT_PID,
                    "current_pid": current_pid,
                },
            )

        # Check model class and all base classes for session factory
        session_factory = None
        for cls in model_class.__mro__:
            if hasattr(cls, "_asynctasq_session_factory"):
                factory = cls._asynctasq_session_factory
                if factory is not None:  # Skip None values
                    session_factory = factory
                    logger.debug(
                        "Found session factory",
                        extra={
                            "model_class": getattr(model_class, "__name__", repr(model_class)),
                            "factory_class": cls.__name__,
                        },
                    )
                    break

        if session_factory is None:
            raise RuntimeError(
                f"SQLAlchemy session factory not configured for {model_class.__name__}.\n\n"
                "Setup required:\n"
                "  from asynctasq.serializers.hooks.orm.sqlalchemy import create_worker_session_factory\n"
                "  Base._asynctasq_session_factory = create_worker_session_factory(\n"
                "      'postgresql+asyncpg://user:pass@localhost/db'\n"
                "  )\n\n"
                "Or manually:\n"
                "  from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine\n"
                "  from sqlalchemy.pool import NullPool\n"
                "  engine = create_async_engine(dsn, poolclass=NullPool, pool_pre_ping=True)\n"
                "  Base._asynctasq_session_factory = async_sessionmaker(engine, expire_on_commit=False)\n\n"
                "See: https://docs.sqlalchemy.org/en/20/core/pooling.html#using-connection-pools-with-multiprocessing"
            )

        # Try async session factory
        try:
            from sqlalchemy.ext.asyncio import async_sessionmaker

            if isinstance(session_factory, async_sessionmaker):
                # Check pool configuration and emit warning if needed
                bind = session_factory.kw.get("bind")
                if bind and current_pid != _PARENT_PID:
                    pool_class_name = bind.pool.__class__.__name__
                    if pool_class_name not in ("NullPool", "StaticPool"):
                        logger.warning(
                            "Using connection pool in forked process - may cause issues",
                            extra={
                                "model_class": getattr(model_class, "__name__", repr(model_class)),
                                "pool_class": pool_class_name,
                                "parent_pid": _PARENT_PID,
                                "current_pid": current_pid,
                            },
                        )

                async with session_factory() as session:
                    result = await session.get(model_class, pk)
                    if result is None:
                        logger.warning(
                            "Model not found",
                            extra={
                                "model_class": getattr(model_class, "__name__", repr(model_class)),
                                "pk": pk,
                            },
                        )
                    return result
        except ImportError:
            pass

        # Try sync session factory
        try:
            from sqlalchemy.orm import sessionmaker

            if isinstance(session_factory, sessionmaker):
                logger.debug(
                    "Using sync session factory",
                    extra={"model_class": getattr(model_class, "__name__", repr(model_class))},
                )

                # Sync session factory - run in executor
                loop = asyncio.get_running_loop()

                def _fetch_sync() -> Any:
                    with session_factory() as session:
                        return session.get(model_class, pk)

                result = await loop.run_in_executor(None, _fetch_sync)
                if result is None:
                    logger.warning(
                        "Model not found",
                        extra={
                            "model_class": getattr(model_class, "__name__", repr(model_class)),
                            "pk": pk,
                        },
                    )
                return result
        except ImportError:
            pass

        raise RuntimeError(
            f"Invalid session factory type for {model_class.__name__}: {type(session_factory).__name__}\n"
            "Expected async_sessionmaker or sessionmaker from SQLAlchemy 2.0+"
        )


# =============================================================================
# SQLAlchemy Utility Functions
# =============================================================================


def create_worker_session_factory(
    dsn: str,
    *,
    echo: bool = False,
    pool_pre_ping: bool = True,
    **kwargs: Any,
) -> Any:
    """Create a worker-safe async session factory with NullPool.

    This helper automatically configures SQLAlchemy with NullPool to avoid
    connection pool sharing across forked worker processes. Recommended for
    production deployments with multiprocessing workers (Celery, Gunicorn, etc.).

    Args:
        dsn: Database connection string
        echo: Enable SQL statement logging (default: False)
        pool_pre_ping: Verify connections before checkout (default: True)
        **kwargs: Additional arguments passed to async_sessionmaker

    Returns:
        async_sessionmaker configured with NullPool for multiprocessing safety

    Example:
        >>> from asynctasq.serializers.hooks.orm.sqlalchemy import create_worker_session_factory
        >>> from sqlalchemy.orm import DeclarativeBase
        >>>
        >>> class Base(DeclarativeBase):
        ...     pass
        >>>
        >>> # Auto-configured for workers - no pool sharing
        >>> Base._asynctasq_session_factory = create_worker_session_factory(
        ...     'postgresql+asyncpg://user:pass@localhost/db'
        ... )

    See: https://docs.sqlalchemy.org/en/20/core/pooling.html#using-connection-pools-with-multiprocessing
    """
    try:
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
        from sqlalchemy.pool import NullPool
    except ImportError as e:
        raise ImportError(
            "SQLAlchemy async support required. Install: pip install 'asynctasq[sqlalchemy]'"
        ) from e

    logger.info(
        "Creating worker-safe session factory with NullPool",
        extra={"dsn": dsn, "pool_pre_ping": pool_pre_ping},
    )

    engine = create_async_engine(
        dsn,
        poolclass=NullPool,  # No pooling - safe for multiprocessing
        pool_pre_ping=pool_pre_ping,
        echo=echo,
    )

    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,  # Prevent lazy-load queries after commit
        **kwargs,
    )

    return session_factory


def validate_session_factory(session_factory: Any, *, warn_only: bool = True) -> dict[str, Any]:
    """Validate SQLAlchemy session factory configuration for production use.

    Checks for common configuration issues that can cause problems in production:
    - Non-NullPool with multiprocessing
    - expire_on_commit=True (causes extra queries)
    - Missing pool_pre_ping (stale connections)
    - No pool recycling configured

    Args:
        session_factory: SQLAlchemy session factory (async_sessionmaker or sessionmaker)
        warn_only: Emit warnings instead of raising errors (default: True)

    Returns:
        dict with validation results and recommendations

    Example:
        >>> from asynctasq.serializers.hooks.orm.sqlalchemy import validate_session_factory
        >>> validation = validate_session_factory(Base._asynctasq_session_factory)
        >>> if validation['warnings']:
        ...     print(f"Configuration warnings: {validation['warnings']}")
    """
    results: dict[str, Any] = {
        "valid": True,
        "warnings": [],
        "recommendations": [],
        "pool_class": None,
        "expire_on_commit": None,
        "pool_pre_ping": None,
    }

    try:
        from sqlalchemy.ext.asyncio import async_sessionmaker
        from sqlalchemy.orm import sessionmaker

        # Check session factory type
        if not isinstance(session_factory, (async_sessionmaker, sessionmaker)):
            results["valid"] = False
            results["warnings"].append(
                f"Invalid session factory type: {type(session_factory).__name__}"
            )
            return results

        # Get bind (engine)
        bind = session_factory.kw.get("bind")
        if bind is None:
            results["warnings"].append("No engine bound to session factory")
            return results

        # Check pool class
        pool = bind.pool
        pool_class_name = pool.__class__.__name__
        results["pool_class"] = pool_class_name

        if pool_class_name not in ("NullPool", "StaticPool"):
            results["warnings"].append(
                f"Using {pool_class_name} - may cause issues with multiprocessing. "
                "Consider NullPool for workers."
            )
            results["recommendations"].append(
                "For multiprocessing workers: engine = create_async_engine(dsn, poolclass=NullPool)"
            )

        # Check expire_on_commit
        expire_on_commit = session_factory.kw.get("expire_on_commit", True)
        results["expire_on_commit"] = expire_on_commit

        if expire_on_commit:
            results["warnings"].append(
                "expire_on_commit=True causes lazy-load queries after commit. "
                "Set to False for better performance."
            )
            results["recommendations"].append("async_sessionmaker(engine, expire_on_commit=False)")

        # Check pool_pre_ping
        pool_pre_ping = getattr(bind, "_pool_pre_ping", None)
        results["pool_pre_ping"] = pool_pre_ping

        if not pool_pre_ping and pool_class_name == "QueuePool":
            results["warnings"].append(
                "pool_pre_ping=False - stale connections may cause errors. Enable for production."
            )
            results["recommendations"].append("create_async_engine(dsn, pool_pre_ping=True)")

        # Check pool recycle
        if pool_class_name == "QueuePool":
            pool_recycle = getattr(bind, "_pool_recycle", -1)
            if pool_recycle < 0:
                results["warnings"].append(
                    "pool_recycle not set - connections never recycled. "
                    "Set to 3600 (1 hour) for production."
                )
                results["recommendations"].append("create_async_engine(dsn, pool_recycle=3600)")

        if results["warnings"] and warn_only:
            for warning in results["warnings"]:
                logger.warning(f"Session factory validation: {warning}")

    except ImportError:
        results["valid"] = False
        results["warnings"].append("SQLAlchemy not installed")

    return results


def detect_forked_process(*, initial_pid: int | None = None) -> bool:
    """Detect if current process is a forked child process.

    Useful for detecting when a worker process has been forked from a parent,
    which can cause issues with shared connection pools.

    Args:
        initial_pid: PID of parent process (stored at initialization)

    Returns:
        True if current PID differs from initial_pid (process was forked)

    Example:
        >>> # Store parent PID at module load
        >>> _parent_pid = os.getpid()
        >>>
        >>> # Later, check if we're in a forked worker
        >>> if detect_forked_process(initial_pid=_parent_pid):
        ...     logger.warning("Forked process detected - reinitialize resources")
    """
    if initial_pid is None:
        # No initial PID provided - can't detect fork
        return False

    current_pid = os.getpid()
    is_forked = current_pid != initial_pid

    if is_forked:
        logger.debug(
            "Fork detected",
            extra={"parent_pid": initial_pid, "current_pid": current_pid},
        )

    return is_forked


def check_pool_health(session_factory: Any) -> dict[str, Any]:
    """Check connection pool health and return diagnostic information.

    Provides insights into pool state for monitoring and debugging.

    Args:
        session_factory: SQLAlchemy session factory

    Returns:
        dict with pool health metrics (size, checked_out, overflow, etc.)

    Example:
        >>> from asynctasq.serializers.hooks.orm.sqlalchemy import check_pool_health
        >>> health = check_pool_health(Base._asynctasq_session_factory)
        >>> if health.get('overflow_count', 0) > 0:
        ...     logger.warning(f"Pool overflow detected: {health}")
    """
    health: dict[str, Any] = {
        "pool_class": None,
        "size": None,
        "checked_out": None,
        "overflow": None,
        "available": None,
    }

    try:
        from sqlalchemy.ext.asyncio import async_sessionmaker
        from sqlalchemy.orm import sessionmaker

        if not isinstance(session_factory, (async_sessionmaker, sessionmaker)):
            health["error"] = f"Invalid session factory type: {type(session_factory)}"
            return health

        bind = session_factory.kw.get("bind")
        if bind is None:
            health["error"] = "No engine bound to session factory"
            return health

        pool = bind.pool
        health["pool_class"] = pool.__class__.__name__

        # Get pool stats (if QueuePool)
        if hasattr(pool, "size"):
            health["size"] = pool.size()
        if hasattr(pool, "checkedout"):
            health["checked_out"] = pool.checkedout()
        if hasattr(pool, "overflow"):
            health["overflow"] = pool.overflow()

        # Calculate available connections
        if health["size"] is not None and health["checked_out"] is not None:
            health["available"] = health["size"] - health["checked_out"]

    except Exception as e:
        health["error"] = str(e)
        logger.error(f"Failed to check pool health: {e}", exc_info=True)

    return health


def emit_fork_safety_warning(pool_class_name: str) -> None:
    """Emit a warning if using non-fork-safe pool in multiprocessing context.

    Args:
        pool_class_name: Name of the pool class being used
    """
    if pool_class_name not in ("NullPool", "StaticPool"):
        warnings.warn(
            f"Using {pool_class_name} with multiprocessing workers can cause "
            "connection sharing issues. Consider using NullPool for workers:\n\n"
            "from sqlalchemy.pool import NullPool\n"
            "engine = create_async_engine(dsn, poolclass=NullPool)\n\n"
            "See: https://docs.sqlalchemy.org/en/20/core/pooling.html"
            "#using-connection-pools-with-multiprocessing",
            UserWarning,
            stacklevel=3,
        )
