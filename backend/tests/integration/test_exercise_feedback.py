# ABOUTME: Proves who can rate which exercise: one rating per person per active exercise, each person seeing only
# ABOUTME: their own, and admins reading everyone's filtered by email. Runs against a live database with fabricated users.

import uuid

import asyncpg
import pytest

from mani.auth.jwt import Claims
from mani.config import get_settings
from mani.db import exercise_feedback, pool
from tests.integration.cleanup import remove_test_users

ALICE = uuid.UUID("a0000000-0000-4000-8000-0000000000e1")
BOB = uuid.UUID("a0000000-0000-4000-8000-0000000000e2")
ACTIVE = uuid.UUID("e0000000-0000-4000-8000-0000000000e1")
RETIRED = uuid.UUID("e0000000-0000-4000-8000-0000000000e2")


def claims_for(user_id: uuid.UUID) -> Claims:
    return Claims(sub=str(user_id), raw={"sub": str(user_id), "role": "authenticated"})


async def reachable() -> bool:
    try:
        conn = await asyncpg.connect(get_settings().database_url, timeout=3)
    except (OSError, asyncpg.PostgresError):
        return False
    await conn.close()
    return True


async def _remove(conn: asyncpg.Connection) -> None:
    await remove_test_users(conn, ALICE, BOB)
    await conn.execute("delete from admin.exercises where id = any($1::uuid[])", [ACTIVE, RETIRED])


@pytest.fixture
async def library():
    if not await reachable():
        pytest.skip("no database reachable; run `supabase start`")
    await pool.open_pool()
    async with pool.as_admin() as conn:
        await _remove(conn)
        await conn.execute(
            "insert into auth.users (id, email) values ($1, 'alice.e1@t.test'), ($2, 'bob.e2@t.test')", ALICE, BOB
        )
        await conn.execute(
            "insert into admin.exercises (id, title, type, category, audio_path, is_active) values "
            "($1, 'The Night Drive', 'Story', 'Anxiety', 'night.mp3', true), "
            "($2, 'Retired Breath', 'Breathing', 'Anxiety', 'retired.mp3', false)",
            ACTIVE, RETIRED,
        )
    try:
        yield
    finally:
        async with pool.as_admin() as conn:
            await _remove(conn)
        await pool.close_pool()


async def test_an_exercise_holds_one_rating_per_person_and_a_new_one_replaces_it(library):
    async with pool.as_user(claims_for(ALICE)) as conn:
        first = await exercise_feedback.rate(conn, ALICE, ACTIVE, "down", "too long for a lunch break")
        second = await exercise_feedback.rate(conn, ALICE, ACTIVE, "up", None)
        stored = await exercise_feedback.for_user(conn, ALICE)

    assert (first.rating, first.reason) == ("down", "too long for a lunch break")
    assert (second.rating, second.reason) == ("up", None)
    assert list(stored) == [ACTIVE] and stored[ACTIVE].rating == "up"


async def test_a_person_sees_only_their_own_ratings_and_clearing_removes_one(library):
    async with pool.as_user(claims_for(ALICE)) as conn:
        await exercise_feedback.rate(conn, ALICE, ACTIVE, "up", "calming")
    async with pool.as_user(claims_for(BOB)) as conn:
        # RLS, not the query's filter: asking for Alice's rows on Bob's connection returns none.
        assert await exercise_feedback.for_user(conn, ALICE) == {}
        await exercise_feedback.clear(conn, BOB, ACTIVE)
    async with pool.as_user(claims_for(ALICE)) as conn:
        assert list(await exercise_feedback.for_user(conn, ALICE)) == [ACTIVE], "Bob's clear left Alice's rating"
        await exercise_feedback.clear(conn, ALICE, ACTIVE)
        await exercise_feedback.clear(conn, ALICE, ACTIVE)
        assert await exercise_feedback.for_user(conn, ALICE) == {}


async def test_a_retired_or_unknown_exercise_cannot_be_rated(library):
    async with pool.as_user(claims_for(ALICE)) as conn:
        assert await exercise_feedback.rate(conn, ALICE, RETIRED, "up", None) is None
        assert await exercise_feedback.rate(conn, ALICE, uuid.uuid4(), "up", None) is None
        assert await exercise_feedback.for_user(conn, ALICE) == {}


async def test_an_admin_reads_every_rating_with_its_exercise_and_filters_by_email(library):
    async with pool.as_user(claims_for(ALICE)) as conn:
        await exercise_feedback.rate(conn, ALICE, ACTIVE, "down", "too long")
    async with pool.as_user(claims_for(BOB)) as conn:
        await exercise_feedback.rate(conn, BOB, ACTIVE, "up", None)

    async with pool.as_admin() as conn:
        everyone = await exercise_feedback.list_all(conn, "t.test")
        alice_only = await exercise_feedback.list_all(conn, "ALICE.e1")

    assert [r.user_email for r in everyone if r.exercise_id == ACTIVE] == ["bob.e2@t.test", "alice.e1@t.test"]
    assert [(r.user_email, r.exercise_title, r.exercise_type, r.rating, r.reason) for r in alice_only] == [
        ("alice.e1@t.test", "The Night Drive", "Story", "down", "too long")
    ]
