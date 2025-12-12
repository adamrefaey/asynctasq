"""
Shared fixtures and models for ORM integration tests.

These fixtures provide database connections, ORM engines/sessions, and test models
for SQLAlchemy, Django, and Tortoise ORM integration tests.

Setup:
    1. Ensure PostgreSQL is running (see Docker setup)
    2. Install optional dependencies:
       - pip install sqlalchemy django tortoise-orm asyncpg
"""

from collections.abc import AsyncGenerator, Generator
from datetime import datetime
import sys

import asyncpg
import django
from django.conf import settings
from django.db import models
from pytest import fixture
import pytest_asyncio
from sqlalchemy import Column, DateTime, Integer, String, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from tortoise import Tortoise
from tortoise.fields import CharField, IntField
from tortoise.fields import DatetimeField as DateTimeField
from tortoise.models import Model

from asynctasq.serializers.hooks import (
    DjangoOrmHook,
    HookRegistry,
    SerializationPipeline,
    SqlalchemyOrmHook,
    TortoiseOrmHook,
    register_orm_hooks,
)

# =============================================================================
# Test Configuration
# =============================================================================

POSTGRES_DSN = "postgresql://test:test@localhost:5432/test_db"
POSTGRES_ASYNC_DSN = "postgresql+asyncpg://test:test@localhost:5432/test_db"

# =============================================================================
# Django Setup
# =============================================================================

if not settings.configured:
    settings.configure(
        DEBUG=True,
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": "test_db",
                "USER": "test",
                "PASSWORD": "test",
                "HOST": "localhost",
                "PORT": "5432",
            }
        },
        INSTALLED_APPS=[],
        USE_TZ=True,
    )
    django.setup()


# =============================================================================
# SQLAlchemy Models
# =============================================================================


class Base(DeclarativeBase):
    pass


class SQLAlchemyUser(Base):
    __tablename__ = "sqlalchemy_test_users"

    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.now)


class SQLAlchemyUserSession(Base):
    """Model with composite primary key."""

    __tablename__ = "sqlalchemy_test_user_sessions"

    user_id = Column(Integer, primary_key=True)
    session_id = Column(String(100), primary_key=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.now)


# =============================================================================
# Django Models
# =============================================================================


class DjangoUser(models.Model):
    username = models.CharField(max_length=100, unique=True)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "test_app"
        db_table = "django_test_users"


# =============================================================================
# Tortoise Models
# =============================================================================


class TortoiseUser(Model):
    id = IntField(primary_key=True)
    username = CharField(max_length=100, unique=True)
    email = CharField(max_length=255)
    created_at = DateTimeField(auto_now_add=True)

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        table = "tortoise_test_users"


# =============================================================================
# Database Fixtures
# =============================================================================


@fixture(scope="module")
def postgres_dsn() -> str:
    """PostgreSQL DSN for sync connections."""
    return POSTGRES_DSN


@pytest_asyncio.fixture
async def postgres_conn() -> AsyncGenerator[asyncpg.Connection, None]:
    """Create async PostgreSQL connection for setup/teardown."""
    conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        user="test",
        password="test",
        database="test_db",
    )

    # Create test tables
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS sqlalchemy_test_users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            email VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS sqlalchemy_test_user_sessions (
            user_id INTEGER NOT NULL,
            session_id VARCHAR(100) NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            PRIMARY KEY (user_id, session_id)
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS tortoise_test_users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            email VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    yield conn

    # Cleanup test data (but keep tables for other tests)
    await conn.execute("DELETE FROM sqlalchemy_test_users WHERE id >= 9000")
    await conn.execute("DELETE FROM sqlalchemy_test_user_sessions WHERE user_id >= 1")
    await conn.execute("DELETE FROM tortoise_test_users WHERE id >= 9000")
    await conn.close()


# =============================================================================
# SQLAlchemy Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def async_engine():
    """Create async SQLAlchemy engine."""
    engine = create_async_engine(POSTGRES_ASYNC_DSN, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async SQLAlchemy session."""
    async_session_maker = async_sessionmaker(async_engine, expire_on_commit=False)
    async with async_session_maker() as session:
        yield session


@fixture
def sync_engine():
    """Create sync SQLAlchemy engine."""
    return create_engine(POSTGRES_DSN.replace("postgresql://", "postgresql+psycopg2://"))


@fixture
def sync_session(sync_engine) -> Generator[Session, None, None]:
    """Create sync SQLAlchemy session."""
    SessionLocal = sessionmaker(bind=sync_engine)
    session = SessionLocal()
    yield session
    session.close()


# =============================================================================
# Tortoise Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def setup_tortoise():
    """Initialize Tortoise ORM."""
    await Tortoise.init(
        db_url="postgres://test:test@localhost:5432/test_db",
        modules={"models": [sys.modules[__name__]]},
    )
    yield
    await Tortoise.close_connections()


# =============================================================================
# Hook Fixtures
# =============================================================================


@fixture
def sqlalchemy_hook() -> SqlalchemyOrmHook:
    """Create SQLAlchemy hook."""
    return SqlalchemyOrmHook()


@fixture
def django_hook() -> DjangoOrmHook:
    """Create Django hook."""
    return DjangoOrmHook()


@fixture
def tortoise_hook() -> TortoiseOrmHook:
    """Create Tortoise hook."""
    return TortoiseOrmHook()


@fixture
def registry_with_orm_hooks() -> HookRegistry:
    """Create registry with all ORM hooks registered."""
    registry = HookRegistry()
    register_orm_hooks(registry)
    return registry


@fixture
def pipeline_with_orm(registry_with_orm_hooks: HookRegistry) -> SerializationPipeline:
    """Create pipeline with ORM hooks."""
    return SerializationPipeline(registry_with_orm_hooks)
