"""Integration tests for SerializationPipeline with ORM hooks."""

import asyncpg
from pytest import mark
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from asynctasq.serializers.hooks import SerializationPipeline

from . import conftest
from .conftest import POSTGRES_ASYNC_DSN, Base, SQLAlchemyUser


@mark.integration
class TestPipelineWithOrmHooks:
    """Integration tests for SerializationPipeline with ORM hooks."""

    @mark.asyncio
    async def test_pipeline_encodes_sqlalchemy_model(
        self,
        pipeline_with_orm: SerializationPipeline,
        async_session: AsyncSession,
        postgres_conn: asyncpg.Connection,
    ) -> None:
        """Test pipeline encodes SQLAlchemy models in nested structures."""
        await postgres_conn.execute(
            """
            INSERT INTO sqlalchemy_test_users (id, username, email, created_at)
            VALUES (9010, 'pipeline_test', 'pipeline@test.com', NOW())
            ON CONFLICT (id) DO NOTHING
            """
        )

        try:
            user = await async_session.get(SQLAlchemyUser, 9010)
            assert user is not None

            data = {
                "user": user,
                "metadata": {"action": "test"},
            }

            encoded = pipeline_with_orm.encode(data)

            assert "__orm:sqlalchemy__" in encoded["user"]
            assert encoded["metadata"] == {"action": "test"}
        finally:
            await postgres_conn.execute("DELETE FROM sqlalchemy_test_users WHERE id = 9010")

    @mark.asyncio
    async def test_pipeline_decodes_sqlalchemy_model(
        self,
        pipeline_with_orm: SerializationPipeline,
        async_session: AsyncSession,
        postgres_conn: asyncpg.Connection,
    ) -> None:
        """Test pipeline decodes ORM references back to models."""
        await postgres_conn.execute(
            """
            INSERT INTO sqlalchemy_test_users (id, username, email, created_at)
            VALUES (9011, 'decode_test', 'decode@test.com', NOW())
            ON CONFLICT (id) DO NOTHING
            """
        )

        try:
            # Set up session factory
            engine = create_async_engine(POSTGRES_ASYNC_DSN, poolclass=NullPool)
            Base._asynctasq_session_factory = async_sessionmaker(engine, expire_on_commit=False)

            encoded_data = {
                "user": {
                    "__orm:sqlalchemy__": 9011,
                    "__orm_class__": f"{conftest.__name__}.SQLAlchemyUser",
                },
                "action": "test",
            }

            decoded = await pipeline_with_orm.decode_async(encoded_data)

            assert isinstance(decoded["user"], SQLAlchemyUser)
            assert decoded["user"].id == 9011
            assert decoded["user"].username == "decode_test"
            assert decoded["action"] == "test"

            await engine.dispose()
        finally:
            await postgres_conn.execute("DELETE FROM sqlalchemy_test_users WHERE id = 9011")
            if hasattr(Base, "_asynctasq_session_factory"):
                delattr(Base, "_asynctasq_session_factory")

    @mark.asyncio
    async def test_pipeline_handles_list_of_models(
        self,
        pipeline_with_orm: SerializationPipeline,
        async_session: AsyncSession,
        postgres_conn: asyncpg.Connection,
    ) -> None:
        """Test pipeline handles lists containing ORM models."""
        await postgres_conn.execute(
            """
            INSERT INTO sqlalchemy_test_users (id, username, email, created_at)
            VALUES
                (9020, 'list_user1', 'list1@test.com', NOW()),
                (9021, 'list_user2', 'list2@test.com', NOW())
            ON CONFLICT (id) DO NOTHING
            """
        )

        try:
            user1 = await async_session.get(SQLAlchemyUser, 9020)
            user2 = await async_session.get(SQLAlchemyUser, 9021)

            data = {"users": [user1, user2]}
            encoded = pipeline_with_orm.encode(data)

            assert len(encoded["users"]) == 2
            assert "__orm:sqlalchemy__" in encoded["users"][0]
            assert "__orm:sqlalchemy__" in encoded["users"][1]
        finally:
            await postgres_conn.execute(
                "DELETE FROM sqlalchemy_test_users WHERE id IN (9020, 9021)"
            )
