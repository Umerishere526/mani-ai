# ABOUTME: Proves every owned table cascades from auth.users, so the account-deletion
# ABOUTME: endpoint has nothing left to clean up once Supabase Auth deletes the user row.

import uuid

import asyncpg
import pytest

from mani.config import get_settings
from mani.db import pool
from tests.integration.cleanup import remove_test_users

USER = "a0000000-0000-4000-8000-0000000000c9"


async def database_reachable() -> bool:
    try:
        conn = await asyncpg.connect(get_settings().database_url, timeout=3)
    except (OSError, asyncpg.PostgresError):
        return False
    await conn.close()
    return True


@pytest.fixture
async def admin_conn():
    if not await database_reachable():
        pytest.skip("no database reachable; run `supabase start`")

    await pool.open_pool()
    async with pool.as_admin() as conn:
        await remove_test_users(conn, USER)
    try:
        async with pool.as_admin() as conn:
            yield conn
    finally:
        async with pool.as_admin() as conn:
            await remove_test_users(conn, USER)
        await pool.close_pool()


async def test_deleting_the_auth_user_takes_every_owned_row_with_it(admin_conn):
    """The account-deletion endpoint only calls Supabase's Admin API to delete auth.users -
    it makes no direct write of its own. This proves that's genuinely enough: the trigger
    from migration 004 creates a profile, and every owned table's FK is declared
    `on delete cascade` from auth.users (since migration 001), so deleting that one row is
    the entire account teardown."""
    thread_id = uuid.uuid4()

    await admin_conn.execute(
        "insert into auth.users (id, email) values ($1, $2)", USER, "cascade@t.test"
    )
    # The migration 004 trigger should have already created this; assert it, then add more
    # owned data so the cascade is proven across more than one table.
    assert await admin_conn.fetchval(
        "select count(*) from public.profiles where user_id = $1", USER
    ) == 1

    await admin_conn.execute(
        "insert into public.threads (id, user_id, title) values ($1, $2, $3)",
        thread_id, USER, "a thread that should not survive",
    )
    await admin_conn.execute(
        "insert into public.messages (thread_id, user_id, role, content) values ($1, $2, 'user', $3)",
        thread_id, USER, "should not survive either",
    )

    # What was remembered about them across conversations is theirs too, and goes with them.
    await admin_conn.execute(
        "insert into admin.user_memory (user_id, memory) values ($1, $2::jsonb)",
        USER, {"low_times": ["should not survive"]},
    )

    await admin_conn.execute("delete from auth.users where id = $1", USER)

    assert await admin_conn.fetchval(
        "select count(*) from public.profiles where user_id = $1", USER
    ) == 0
    assert await admin_conn.fetchval(
        "select count(*) from public.threads where user_id = $1", USER
    ) == 0
    assert await admin_conn.fetchval(
        "select count(*) from public.messages where user_id = $1", USER
    ) == 0
    assert await admin_conn.fetchval(
        "select count(*) from admin.user_memory where user_id = $1", USER
    ) == 0
