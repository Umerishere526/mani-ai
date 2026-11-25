# ABOUTME: The library as a signed-in person reads it: its topics with their blurbs, and each topic's exercises.
# ABOUTME: Runs against a live database with fabricated topics and exercises, removed afterwards.

import uuid

import asyncpg
import pytest

from mani.auth.jwt import Claims
from mani.config import get_settings
from mani.db import exercises, pool

ALICE = uuid.UUID("a0000000-0000-4000-8000-0000000000f1")
TOPICS = ("ZzLibraryCalm", "ZzLibraryWork")


async def reachable() -> bool:
    try:
        conn = await asyncpg.connect(get_settings().database_url, timeout=3)
    except (OSError, asyncpg.PostgresError):
        return False
    await conn.close()
    return True


async def _remove(conn: asyncpg.Connection) -> None:
    await conn.execute("delete from admin.exercises where category = any($1::text[])", list(TOPICS))
    await conn.execute("delete from admin.library_topics where id = any($1::text[])", list(TOPICS))


@pytest.fixture
async def alice():
    if not await reachable():
        pytest.skip("no database reachable; run `supabase start`")
    await pool.open_pool()
    async with pool.as_admin() as conn:
        await _remove(conn)
    try:
        async with pool.as_user(Claims(sub=str(ALICE), raw={"sub": str(ALICE), "role": "authenticated"})) as conn:
            yield conn
    finally:
        async with pool.as_admin() as conn:
            await _remove(conn)
        await pool.close_pool()


async def test_a_person_reads_the_topics_in_the_clients_order_with_their_blurbs(alice):
    async with pool.as_admin() as conn:
        await conn.execute(
            "insert into admin.library_topics (id, title, blurb, display_order) values "
            "('ZzLibraryWork', 'Workplace', '', 2), ('ZzLibraryCalm', 'Calm', 'Calm your mind.', 1)"
        )

    listed = [t for t in await exercises.list_topics(alice) if t.id in TOPICS]

    assert [(t.id, t.title, t.blurb) for t in listed] == [
        ("ZzLibraryCalm", "Calm", "Calm your mind."),
        ("ZzLibraryWork", "Workplace", ""),
    ]
