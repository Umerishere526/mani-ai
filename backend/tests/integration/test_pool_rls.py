# ABOUTME: Proves as_user() really applies RLS on a live connection, not just in theory.
# ABOUTME: Skipped when no database is reachable, so the unit suite stays runnable offline.

import uuid

import asyncpg
import pytest

from mani.auth.jwt import Claims
from mani.config import get_settings
from mani.db import pool
from tests.integration.cleanup import remove_test_users

ALICE = "a0000000-0000-4000-8000-0000000000a1"
BOB = "a0000000-0000-4000-8000-0000000000b1"


def claims_for(user_id: str) -> Claims:
    return Claims(sub=user_id, raw={"sub": user_id, "role": "authenticated"})


async def database_reachable() -> bool:
    try:
        conn = await asyncpg.connect(get_settings().database_url, timeout=3)
    except (OSError, asyncpg.PostgresError):
        return False
    await conn.close()
    return True


@pytest.fixture
async def db():
    if not await database_reachable():
        pytest.skip("no database reachable; run `supabase start`")

    await pool.open_pool()
    async with pool.as_admin() as conn:
        await conn.execute("delete from public.threads where user_id = any($1::uuid[])",
                           [ALICE, BOB])
        await remove_test_users(conn, ALICE, BOB)
        await conn.execute(
            "insert into auth.users (id, email) values ($1,'alice@t.test'),($2,'bob@t.test')",
            ALICE, BOB)
        await conn.execute(
            "insert into public.threads (id, user_id, title) values ($1,$2,$3),($4,$5,$6)",
            uuid.uuid4(), ALICE, "Alice thread", uuid.uuid4(), BOB, "Bob thread")
    try:
        yield
    finally:
        async with pool.as_admin() as conn:
            await conn.execute("delete from public.threads where user_id = any($1::uuid[])",
                               [ALICE, BOB])
            await remove_test_users(conn, ALICE, BOB)
        await pool.close_pool()


async def test_a_user_connection_sees_only_that_user(db):
    async with pool.as_user(claims_for(ALICE)) as conn:
        titles = [r["title"] for r in await conn.fetch("select title from public.threads")]
    assert titles == ["Alice thread"]


async def test_the_missing_filter_no_longer_leaks(db):
    """The previous implementation's live defect: a query with no ownership predicate."""
    async with pool.as_user(claims_for(ALICE)) as conn:
        rows = await conn.fetch(
            "select title from public.threads where title = 'Bob thread'")
    assert rows == []


async def test_a_user_cannot_write_a_row_owned_by_another(db):
    async with pool.as_user(claims_for(ALICE)) as conn:
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await conn.execute(
                "insert into public.threads (user_id, title) values ($1, $2)",
                BOB, "a thread in Bob's name")


async def test_identity_does_not_leak_between_connections(db):
    """A pooled connection must not carry one caller's claims into the next request."""
    async with pool.as_user(claims_for(ALICE)) as conn:
        assert await conn.fetchval("select auth.uid()") == uuid.UUID(ALICE)

    async with pool.as_user(claims_for(BOB)) as conn:
        assert await conn.fetchval("select auth.uid()") == uuid.UUID(BOB)

    # And with no claims set at all, the session has no identity.
    async with pool.as_admin() as conn:
        assert await conn.fetchval("select auth.uid()") is None


async def test_admin_connection_is_not_user_scoped(db):
    async with pool.as_admin() as conn:
        count = await conn.fetchval(
            "select count(*) from public.threads where user_id = any($1::uuid[])",
            [ALICE, BOB])
    assert count == 2


async def test_a_turn_rolls_back_as_one(db):
    """The reason for a direct connection: many writes that stand or fall together."""
    thread_id = uuid.uuid4()
    with pytest.raises(asyncpg.PostgresError):
        async with pool.as_user(claims_for(ALICE)) as conn:
            await conn.execute(
                "insert into public.threads (id, user_id, title) values ($1,$2,$3)",
                thread_id, ALICE, "should not survive")
            # Fails: no such column. The insert above must go with it.
            await conn.execute("update public.threads set nope = 1 where id = $1", thread_id)

    async with pool.as_admin() as conn:
        assert await conn.fetchval(
            "select count(*) from public.threads where id = $1", thread_id) == 0
