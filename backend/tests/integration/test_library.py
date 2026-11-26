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


async def test_a_collecting_topic_lists_other_topics_exercises_under_their_subcategories(alice):
    async with pool.as_admin() as conn:
        await conn.execute(
            "insert into admin.library_topics (id, title) values ('ZzLibraryCalm', 'Calm'), ('ZzLibraryWork', 'Work')"
        )
        breath, story, unrecorded = [
            await conn.fetchval(
                "insert into admin.exercises (title, category, audio_path, display_order) "
                "values ($1, $2, $3, $4) returning id",
                title, category, path, order,
            )
            for title, category, path, order in (
                ("Breath", "ZzLibraryCalm", "breath.mp3", 0),
                ("Story", "ZzLibraryCalm", "story.mp3", 1),
                ("Desk Stretch", "ZzLibraryWork", None, 0),
            )
        ]
        await conn.execute(
            "insert into admin.exercise_topic_links (topic_id, exercise_id, subcategory, display_order) "
            "values ('ZzLibraryWork', $1, 'Stress & Pressure', 1), ('ZzLibraryWork', $2, 'Stress & Pressure', 0)",
            breath, story,
        )

    work = await exercises.list_active(alice, "ZzLibraryWork")
    calm = await exercises.list_active(alice, "ZzLibraryCalm")
    everything = [e.id for e in await exercises.list_active(alice) if e.category in TOPICS]

    # Its own exercise first, then the collected ones in the link's order, each under its subcategory.
    assert [(e.title, e.subcategory) for e in work] == [
        ("Desk Stretch", None), ("Story", "Stress & Pressure"), ("Breath", "Stress & Pressure"),
    ]
    assert work[0].audio_path is None, "an unrecorded item is listed, with no audio"
    assert [(e.title, e.subcategory) for e in calm] == [("Breath", None), ("Story", None)]
    assert sorted(everything) == sorted([breath, story, unrecorded]), "the whole catalog lists each exercise once"


async def test_with_no_topics_seeded_the_categories_the_exercises_carry_are_the_topics(alice):
    """DEP-2 (2026-11-25): hosted has its exercises but not the client's topics until seed_exercises.py runs with the
    recordings, and the library must not show nothing in between. Run in a transaction that is rolled back, so the
    shared database keeps its topics."""
    async with pool.as_admin() as conn:
        transaction = conn.transaction()
        await transaction.start()
        try:
            await conn.execute("delete from admin.exercise_topic_links")
            await conn.execute("delete from admin.library_topics")
            await conn.execute("update admin.exercises set is_active = false")
            await conn.execute(
                "insert into admin.exercises (title, category, audio_path, display_order) values "
                "('Breathe', 'ZzLibraryCalm', 'zz/breathe.mp3', 1), ('Boundaries', 'ZzLibraryWork', 'zz/b.mp3', 2)"
            )
            topics = await exercises.list_topics(conn)
        finally:
            await transaction.rollback()

    assert [(t.id, t.title) for t in topics] == [("ZzLibraryCalm", "Zz Library Calm"), ("ZzLibraryWork", "Zz Library Work")]
