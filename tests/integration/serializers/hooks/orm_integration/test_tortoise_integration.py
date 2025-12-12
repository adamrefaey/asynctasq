"""Integration tests for Tortoise ORM hook."""

import asyncpg
from pytest import mark

from asynctasq.serializers.hooks import TortoiseOrmHook

from .conftest import TortoiseUser


@mark.integration
class TestTortoiseHookIntegration:
    """Integration tests for Tortoise ORM hook."""

    @mark.asyncio
    async def test_can_encode_real_tortoise_model(
        self,
        tortoise_hook: TortoiseOrmHook,
        postgres_conn: asyncpg.Connection,
        setup_tortoise,
    ) -> None:
        """Test can_encode with real Tortoise model."""
        await postgres_conn.execute(
            """
            INSERT INTO tortoise_test_users (id, username, email, created_at)
            VALUES (9001, 'tortoise_test', 'tortoise@test.com', NOW())
            ON CONFLICT (id) DO NOTHING
            """
        )

        try:
            user = await TortoiseUser.get(id=9001)
            assert tortoise_hook.can_encode(user) is True
        finally:
            await postgres_conn.execute("DELETE FROM tortoise_test_users WHERE id = 9001")

    @mark.asyncio
    async def test_encode_real_tortoise_model(
        self,
        tortoise_hook: TortoiseOrmHook,
        postgres_conn: asyncpg.Connection,
        setup_tortoise,
    ) -> None:
        """Test encoding a real Tortoise model."""
        await postgres_conn.execute(
            """
            INSERT INTO tortoise_test_users (id, username, email, created_at)
            VALUES (9002, 'tortoise_encode', 'encode@test.com', NOW())
            ON CONFLICT (id) DO NOTHING
            """
        )

        try:
            user = await TortoiseUser.get(id=9002)
            result = tortoise_hook.encode(user)

            assert result["__orm:tortoise__"] == 9002
            assert "TortoiseUser" in result["__orm_class__"]
        finally:
            await postgres_conn.execute("DELETE FROM tortoise_test_users WHERE id = 9002")

    @mark.asyncio
    async def test_round_trip_tortoise_model(
        self,
        tortoise_hook: TortoiseOrmHook,
        postgres_conn: asyncpg.Connection,
        setup_tortoise,
    ) -> None:
        """Test full round-trip encode/decode for Tortoise model."""
        await postgres_conn.execute(
            """
            INSERT INTO tortoise_test_users (id, username, email, created_at)
            VALUES (9003, 'tortoise_rt', 'rt@test.com', NOW())
            ON CONFLICT (id) DO NOTHING
            """
        )

        try:
            user = await TortoiseUser.get(id=9003)
            encoded = tortoise_hook.encode(user)
            decoded = await tortoise_hook.decode_async(encoded)

            assert decoded.id == user.id
            assert decoded.username == user.username
            assert decoded.email == user.email
        finally:
            await postgres_conn.execute("DELETE FROM tortoise_test_users WHERE id = 9003")
