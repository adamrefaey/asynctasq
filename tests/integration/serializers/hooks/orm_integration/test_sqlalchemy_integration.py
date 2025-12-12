"""Integration tests for SQLAlchemy ORM hook."""

import asyncpg
from pytest import mark
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from asynctasq.serializers.hooks import SqlalchemyOrmHook

from .conftest import POSTGRES_ASYNC_DSN, Base, SQLAlchemyUser, SQLAlchemyUserSession


@mark.integration
class TestSqlalchemyHookIntegration:
    """Integration tests for SQLAlchemy ORM hook."""

    @mark.asyncio
    async def test_can_encode_real_sqlalchemy_model(
        self,
        sqlalchemy_hook: SqlalchemyOrmHook,
        async_session: AsyncSession,
        postgres_conn: asyncpg.Connection,
    ) -> None:
        """Test can_encode with real SQLAlchemy model."""
        # Create test data
        await postgres_conn.execute(
            """
            INSERT INTO sqlalchemy_test_users (id, username, email, created_at)
            VALUES (9001, 'encode_test', 'encode@test.com', NOW())
            ON CONFLICT (id) DO NOTHING
            """
        )

        try:
            user = await async_session.get(SQLAlchemyUser, 9001)
            assert user is not None
            assert sqlalchemy_hook.can_encode(user) is True
        finally:
            await postgres_conn.execute("DELETE FROM sqlalchemy_test_users WHERE id = 9001")

    @mark.asyncio
    async def test_encode_real_sqlalchemy_model(
        self,
        sqlalchemy_hook: SqlalchemyOrmHook,
        async_session: AsyncSession,
        postgres_conn: asyncpg.Connection,
    ) -> None:
        """Test encoding a real SQLAlchemy model."""
        await postgres_conn.execute(
            """
            INSERT INTO sqlalchemy_test_users (id, username, email, created_at)
            VALUES (9002, 'encode_real', 'real@test.com', NOW())
            ON CONFLICT (id) DO NOTHING
            """
        )

        try:
            user = await async_session.get(SQLAlchemyUser, 9002)
            assert user is not None

            result = sqlalchemy_hook.encode(user)
            assert result["__orm:sqlalchemy__"] == 9002
            assert "SQLAlchemyUser" in result["__orm_class__"]
        finally:
            await postgres_conn.execute("DELETE FROM sqlalchemy_test_users WHERE id = 9002")

    @mark.asyncio
    async def test_round_trip_sqlalchemy_model(
        self,
        sqlalchemy_hook: SqlalchemyOrmHook,
        async_session: AsyncSession,
        postgres_conn: asyncpg.Connection,
    ) -> None:
        """Test full round-trip encode/decode for SQLAlchemy model."""
        await postgres_conn.execute(
            """
            INSERT INTO sqlalchemy_test_users (id, username, email, created_at)
            VALUES (9003, 'roundtrip', 'roundtrip@test.com', NOW())
            ON CONFLICT (id) DO NOTHING
            """
        )

        try:
            # Get original model
            user = await async_session.get(SQLAlchemyUser, 9003)
            assert user is not None

            # Encode
            encoded = sqlalchemy_hook.encode(user)

            # Set up session factory for decode
            engine = create_async_engine(POSTGRES_ASYNC_DSN, poolclass=NullPool)
            Base._asynctasq_session_factory = async_sessionmaker(engine, expire_on_commit=False)

            # Decode
            decoded = await sqlalchemy_hook.decode_async(encoded)

            assert decoded.id == user.id
            assert decoded.username == user.username
            assert decoded.email == user.email

            await engine.dispose()
        finally:
            await postgres_conn.execute("DELETE FROM sqlalchemy_test_users WHERE id = 9003")
            if hasattr(Base, "_asynctasq_session_factory"):
                delattr(Base, "_asynctasq_session_factory")

    @mark.asyncio
    async def test_composite_primary_key(
        self,
        sqlalchemy_hook: SqlalchemyOrmHook,
        async_session: AsyncSession,
        postgres_conn: asyncpg.Connection,
    ) -> None:
        """Test encoding model with composite primary key."""
        await postgres_conn.execute(
            """
            INSERT INTO sqlalchemy_test_user_sessions (user_id, session_id, created_at)
            VALUES (1, 'session-abc', NOW())
            ON CONFLICT DO NOTHING
            """
        )

        try:
            session_model = await async_session.get(SQLAlchemyUserSession, (1, "session-abc"))
            assert session_model is not None

            encoded = sqlalchemy_hook.encode(session_model)
            # Composite PK should be a tuple
            assert encoded["__orm:sqlalchemy__"] == (1, "session-abc")
        finally:
            await postgres_conn.execute(
                "DELETE FROM sqlalchemy_test_user_sessions WHERE user_id = 1 AND session_id = 'session-abc'"
            )
