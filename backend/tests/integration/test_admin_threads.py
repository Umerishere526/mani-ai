# ABOUTME: Proves an admin can list and read every person's conversations, and that each full read is logged.
# ABOUTME: Runs against a live database with fabricated users, removed afterwards.

import uuid

import asyncpg
import pytest

from mani.config import get_settings
from mani.db import admin_threads, pool
from tests.integration.cleanup import remove_test_users

ADMIN = uuid.UUID("a0000000-0000-4000-8000-0000000000d1")
ALICE = uuid.UUID("a0000000-0000-4000-8000-0000000000d2")
BOB = uuid.UUID("a0000000-0000-4000-8000-0000000000d3")


async def reachable() -> bool:
    try:
        conn = await asyncpg.connect(get_settings().database_url, timeout=3)
    except (OSError, asyncpg.PostgresError):
        return False
    await conn.close()
    return True


async def _thread(conn, user_id: uuid.UUID, title: str, lines: list[tuple[str, str]]) -> uuid.UUID:
    thread_id = uuid.uuid4()
    await conn.execute(
        "insert into public.threads (id, user_id, title) values ($1, $2, $3)", thread_id, user_id, title
    )
    for role, content in lines:
        await conn.execute(
            "insert into public.messages (thread_id, user_id, role, content) values ($1, $2, $3, $4)",
            thread_id, user_id, role, content,
        )
    return thread_id


@pytest.fixture
async def conn():
    if not await reachable():
        pytest.skip("no database reachable; run `supabase start`")
    await pool.open_pool()
    async with pool.as_admin() as c:
        await remove_test_users(c, ADMIN, ALICE, BOB)
        await c.execute(
            "insert into auth.users (id, email) values ($1, 'admin-d1@t.test'), "
            "($2, 'alice-d2@t.test'), ($3, 'bob-d3@t.test')",
            ADMIN, ALICE, BOB,
        )
    try:
        async with pool.as_admin() as c:
            yield c
    finally:
        async with pool.as_admin() as c:
            await remove_test_users(c, ADMIN, ALICE, BOB)
        await pool.close_pool()


async def test_an_admin_lists_everyones_threads_but_not_the_deleted_ones(conn):
    alices = await _thread(conn, ALICE, "Alice's", [("user", "hi")])
    bobs = await _thread(conn, BOB, "Bob's", [("user", "hey")])
    deleted = await _thread(conn, BOB, "Gone", [("user", "bye")])
    await conn.execute("update public.threads set deleted_at = now() where id = $1", deleted)
    await conn.execute("update public.profiles set support_style = 'reflective' where user_id = $1", ALICE)
    await conn.execute("update public.threads set conversation_style = 'directive' where id = $1", bobs)

    # The newest activity comes first, so these are on the first page whatever else the database holds.
    listed = {t.id: t for t in (await admin_threads.list_all(conn, limit=admin_threads.MAX_PAGE)).threads}

    assert {alices, bobs} <= set(listed)
    assert deleted not in listed
    assert listed[alices].user_email == "alice-d2@t.test"
    # A conversation's own style wins; without one, the person's onboarding default is what Mani used.
    assert listed[bobs].conversation_style.value == "directive"
    assert listed[alices].conversation_style.value == "reflective"
    assert [t.id for t in (await admin_threads.list_all(conn, search="BOB-D3")).threads] == [bobs]
    assert [t.id for t in (await admin_threads.list_all(conn, search=str(ALICE))).threads] == [alices]


async def test_reading_a_transcript_returns_every_message_in_order_and_logs_the_read(conn):
    lines = [("mani", "Hello"), ("user", "I can't sleep"), ("mani", "What keeps you up?"), ("user", "Work")]
    thread_id = await _thread(conn, ALICE, "Sleep", lines)

    thread, messages = await admin_threads.read_transcript(conn, thread_id, ADMIN)

    assert thread.user_id == ALICE
    assert [(m.role.value, m.content) for m in messages] == lines
    logged = await conn.fetch(
        "select admin_id from admin.thread_reads where thread_id = $1", thread_id
    )
    assert [r["admin_id"] for r in logged] == [ADMIN]


async def test_a_missing_thread_is_not_read_and_not_logged(conn):
    assert await admin_threads.read_transcript(conn, uuid.uuid4(), ADMIN) is None
    assert await conn.fetchval(
        "select count(*) from admin.thread_reads where admin_id = $1", ADMIN
    ) == 0


async def test_the_read_log_goes_with_the_persons_account(conn):
    thread_id = await _thread(conn, ALICE, "Theirs", [("user", "hi")])
    await admin_threads.read_transcript(conn, thread_id, ADMIN)

    await conn.execute("delete from auth.users where id = $1", ALICE)

    assert await conn.fetchval(
        "select count(*) from admin.thread_reads where thread_id = $1", thread_id
    ) == 0
