# ABOUTME: What a turn leaves for after its reply waits on the thread until the app asks for it, then runs once.
# ABOUTME: Against a live database with a scripted model: what is stored, what runs, and what is never run.

import uuid

from mani.chat import orchestrator, runner
from mani.config import get_settings
from mani.db import llm_calls, pool, summaries, threads
from mani.llm import client
from mani.llm.schema import Extraction, Reply
from tests.integration.test_turn import (  # noqa: F401 - alice and model are fixtures
    ScriptedModel,
    _thread_row,
    alice,
    claims_for,
    felt,
    model,
    start,
)


async def _waiting(thread_id) -> dict | None:
    async with pool.as_admin() as conn:
        return await conn.fetchval("select pending_follow_up from public.threads where id = $1", thread_id)


async def test_a_chat_turn_leaves_its_reading_for_the_app_and_it_runs_once(alice, model):
    """On Vercel work started after the response was cut off: 15 of 49 readings (2026-11-05). The turn stores it and
    the app asks for it with a request of its own. A second request, a retry, pays nothing."""
    scripted = model(Reply(text="That sounds lonely. What happened?", picture=felt("lonely")))
    thread = await start(alice)
    turn = await runner.send(alice, thread.id, "my brother never calls")

    waiting = await _waiting(thread.id)
    assert waiting["message_id"] == str(turn.message_id)
    assert waiting["reading"] is not None and waiting["summary"] is False
    assert scripted.reads == [], "nothing is read until the app asks"

    done = await orchestrator.follow_up(alice, thread.id, turn.message_id)

    assert done.understanding["picture"]["feelings"] == [{"feeling": "lonely"}]
    assert not done.summarized
    assert (await _thread_row(alice, thread.id)).understanding == done.understanding
    assert await _waiting(thread.id) is None
    assert await orchestrator.follow_up(alice, thread.id, turn.message_id) is None
    assert len(scripted.reads) == 1


async def test_a_summary_that_falls_due_waits_for_the_app_and_runs_beside_the_reading(alice, monkeypatch):
    """The summary was left running after the response too. It now waits with the reading and runs with it."""
    scripted = ScriptedModel(Reply(text="What has been the hardest part?"), Reply(text="What changed?"))
    summarized = []

    async def complete(messages, schema, **kwargs):
        if schema is Extraction:
            summarized.append(messages)
            return client.Call(value=Extraction(summary="Work has been hard."), model="test/model",
                               usage=llm_calls.Usage(), latency_ms=1, call_id=uuid.uuid4())
        return await scripted(messages, schema, **kwargs)

    monkeypatch.setattr(orchestrator.client, "complete", complete)
    monkeypatch.setattr(get_settings(), "context_budget_chars", 40)
    thread = await start(alice)
    await runner.send(alice, thread.id, "work has been hard lately, every single day of it")
    turn = await runner.send(alice, thread.id, "and nobody at work seems to notice how much I carry")

    assert (await _waiting(thread.id))["summary"] is True
    assert summarized == [], "nothing is summarized until the app asks"

    done = await orchestrator.follow_up(alice, thread.id, turn.message_id)

    assert done.summarized and done.understanding is not None
    assert len(summarized) == 1
    async with pool.as_user(alice) as conn:
        assert (await summaries.get(conn, thread.id)).summary == "Work has been hard."


async def test_a_request_for_another_reply_runs_nothing_and_leaves_the_waiting_one(alice, model):
    scripted = model(Reply(text="That sounds lonely. What happened?", picture=felt("lonely")))
    thread = await start(alice)
    turn = await runner.send(alice, thread.id, "my brother never calls")

    assert await orchestrator.follow_up(alice, thread.id, thread.id) is None

    assert scripted.reads == []
    assert (await _waiting(thread.id))["message_id"] == str(turn.message_id)


async def test_the_next_turn_replaces_what_the_app_never_asked_for(alice, model):
    """At most one follow-up waits: the one for the newest reply. A request for an older reply finds nothing."""
    scripted = model(
        Reply(text="That sounds lonely. What happened?", picture=felt("lonely")),
        Reply(text="What did you hope he would say?"),
    )
    thread = await start(alice)
    first = await runner.send(alice, thread.id, "my brother never calls")
    second = await runner.send(alice, thread.id, "he only calls when he needs something")

    assert (await _waiting(thread.id))["message_id"] == str(second.message_id)
    assert await orchestrator.follow_up(alice, thread.id, first.message_id) is None
    assert scripted.reads == []


async def test_a_reading_asked_for_after_the_next_turn_began_adds_to_it_and_overwrites_nothing(alice, model):
    """The app's request and their next message can cross: the reading merges onto the record as it is when it lands."""
    model(
        Reply(text="That sounds lonely. What happened?", picture=felt("lonely")),
        Reply(text="What did you hope he would say?", heart="core_named"),
    )
    thread = await start(alice)
    first = await runner.send(alice, thread.id, "my brother never calls")
    async with pool.as_user(alice) as conn:
        waiting = await threads.take_pending_follow_up(conn, thread.id, alice.user_id, first.message_id)
    await runner.send(alice, thread.id, "he only calls when he needs something")

    stored = await orchestrator.read_understanding(alice, orchestrator.ReadAfter.from_stored(waiting["reading"]))

    assert stored["heart"] == "core_named", "the later turn's record is kept"
    assert stored["picture"]["feelings"] == [{"feeling": "lonely"}]


async def test_another_person_cannot_run_what_waits(alice, model):
    scripted = model(Reply(text="That sounds lonely. What happened?", picture=felt("lonely")))
    thread = await start(alice)
    turn = await runner.send(alice, thread.id, "my brother never calls")

    assert await orchestrator.follow_up(claims_for(uuid.uuid4()), thread.id, turn.message_id) is None
    assert scripted.reads == []
    assert await _waiting(thread.id) is not None
