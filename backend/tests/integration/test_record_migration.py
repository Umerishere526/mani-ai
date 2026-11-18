# ABOUTME: The migration that reshapes each thread's record for the one-call turn, run inside a transaction that is
# ABOUTME: rolled back, so a conversation mid-framework keeps its stage and never sees a declined set offered again.

import pathlib

import pytest

from mani.chat import decide as decide_mod
from mani.chat.reply import TurnReply, Safety
from mani.chat.taps import TapEvent
from mani.prompts import cache
from tests.integration.fixtures import ALICE, start

MIGRATION = pathlib.Path(__file__).resolve().parents[2] / "supabase/migrations/039_thread_record_one_call.sql"
OLD_RECORD = {
    "picture": {"feelings": [{"feeling": "stuck"}]}, "reading": {"core": "not enough"}, "heart": "ready",
    "known": {"happened": "x"}, "insights": ["a"], "danger_reached": True, "danger_about": "themselves",
    "return_check": {"pause": "p1", "state": "answered"},
}


class _RolledBack(Exception):
    pass


async def test_a_thread_mid_framework_keeps_its_stage_and_is_never_offered_its_declined_one_again(alice, model):
    from mani.db import pool

    thread = await start(alice)
    async with pool.as_admin() as conn:
        await conn.execute("update public.threads set understanding = $2::jsonb, rewind_snapshot = '{}'::jsonb "
                           "where id = $1", thread.id, OLD_RECORD)
        await conn.execute(
            "insert into public.thread_technique_state (thread_id, user_id, framework_id, outcome, phase, at_message_count) "
            "values ($1, $2, 'thought_reframe', 'declined', null, 4)", thread.id, ALICE)
    seen = {}
    with pytest.raises(_RolledBack):
        async with pool.as_admin() as conn, conn.transaction():
            await conn.execute(MIGRATION.read_text())
            seen["record"], seen["snapshot"] = await conn.fetchrow(
                "select understanding, rewind_snapshot from public.threads where id = $1", thread.id)
            raise _RolledBack
    assert set(seen["record"]) == {"notes", "declined", "finished", "danger_reached", "danger_about", "return_check"}
    assert seen["record"]["declined"] == ["thought_reframe"] and seen["record"]["finished"] == []
    assert seen["record"]["danger_reached"] is True and seen["snapshot"] is None

    config = await cache.load()
    refused = decide_mod.decide(
        TurnReply(text="Offer.", action="offer", framework="thought_reframe", safety=Safety(level="none"), notes=""),
        config.registry, thread_id=thread.id, running=None, open_offer=None, tap=TapEvent(), record=seen["record"],
        guarded=False, count_after=6, end_check_due=False, end_check_asked=False, person_messages=5,
    )
    assert refused.refused == "offer" and refused.prompts == []


async def test_a_thread_left_at_the_body_check_in_is_retired_and_counted_finished(alice, model):
    from mani.db import pool

    thread = await start(alice)
    async with pool.as_admin() as conn:
        await conn.execute(
            "insert into public.thread_technique_state (thread_id, user_id, framework_id, outcome, phase, at_message_count) "
            "values ($1, $2, 'abcde', 'accepted', 'somatic_ask', 12)", thread.id, ALICE)
    seen = {}
    with pytest.raises(_RolledBack):
        async with pool.as_admin() as conn, conn.transaction():
            await conn.execute(MIGRATION.read_text())
            seen["phase"] = await conn.fetchval(
                "select phase from public.thread_technique_state where thread_id = $1", thread.id)
            seen["record"] = await conn.fetchval("select understanding from public.threads where id = $1", thread.id)
            raise _RolledBack
    assert seen["phase"] is None and seen["record"]["finished"] == ["abcde"]


@pytest.mark.parametrize(("outcome", "phase"), [("accepted", "belief"), ("offered", "offering")])
async def test_a_set_running_or_on_offer_keeps_its_stage_and_is_not_counted_finished(alice, model, outcome, phase):
    """The final review, 2026-11-18: the test above never had a running or open row. One mid-set keeps its stage,
    one on offer stays on offer, and neither is counted finished or declined."""
    from mani.db import pool

    thread = await start(alice)
    async with pool.as_admin() as conn:
        await conn.execute(
            "insert into public.thread_technique_state (thread_id, user_id, framework_id, outcome, phase, at_message_count) "
            "values ($1, $2, 'abcde', $3, $4, 6)", thread.id, ALICE, outcome, phase)
    seen = {}
    with pytest.raises(_RolledBack):
        async with pool.as_admin() as conn, conn.transaction():
            await conn.execute(MIGRATION.read_text())
            seen["row"] = await conn.fetchrow(
                "select outcome, phase from public.thread_technique_state where thread_id = $1", thread.id)
            seen["record"] = await conn.fetchval("select understanding from public.threads where id = $1", thread.id)
            raise _RolledBack
    assert (seen["row"]["outcome"], seen["row"]["phase"]) == (outcome, phase)
    assert seen["record"]["finished"] == [] and seen["record"]["declined"] == []
