# ABOUTME: What a turn leaves for after its reply waits on the thread until the app asks for it, then runs once.
# ABOUTME: Against a live database with a scripted model: what is stored, what runs, and what is never run.

import asyncio
import datetime as dt
import uuid

from mani import catch_up
from mani.chat import orchestrator, runner
from mani.config import get_settings
from mani.db import llm_calls, pool, summaries, threads
from mani.llm import client
from mani.llm.schema import ConversationUnderstanding, Extraction, Reply
from tests.integration.test_turn import (  # noqa: F401 - alice and model are fixtures
    ScriptedModel,
    _last_user_message_id,
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
        waiting = await threads.claim_pending_follow_up(conn, thread.id, alice.user_id, first.message_id)
    await runner.send(alice, thread.id, "he only calls when he needs something")

    stored = await orchestrator.read_understanding(alice, orchestrator.ReadAfter.from_stored(waiting["reading"]))

    assert stored["heart"] == "core_named", "the later turn's record is kept"
    assert stored["picture"]["feelings"] == [{"feeling": "lonely"}]


def _failing_reads(monkeypatch, scripted, times: int = 1):
    """The model, whose first `times` readings fail as a provider timeout does."""
    failures = [times]

    async def complete(messages, schema, **kwargs):
        if schema is ConversationUnderstanding and failures[0] > 0:
            failures[0] -= 1
            raise TimeoutError("provider timed out")
        return await scripted(messages, schema, **kwargs)

    monkeypatch.setattr(orchestrator.client, "complete", complete)


async def test_a_reading_that_fails_waits_to_be_asked_for_again_and_loses_nothing(alice, model, monkeypatch):
    """The reading used to be cleared as it was taken, so a timeout or a crash lost it for good."""
    scripted = model(Reply(text="That sounds lonely. What happened?", picture=felt("lonely")))
    thread = await start(alice)
    turn = await runner.send(alice, thread.id, "my brother never calls")
    _failing_reads(monkeypatch, scripted)

    failed = await orchestrator.follow_up(alice, thread.id, turn.message_id)

    assert failed.understanding is None and failed.pending
    assert (await _waiting(thread.id))["message_id"] == str(turn.message_id)

    again = await orchestrator.follow_up(alice, thread.id, turn.message_id)

    assert again.understanding["picture"]["feelings"] == [{"feeling": "lonely"}] and not again.pending
    assert await _waiting(thread.id) is None


async def test_only_the_part_that_failed_is_run_again(alice, monkeypatch):
    """A retry after the reading landed and the summary did not must not pay for the reading twice."""
    scripted = ScriptedModel(Reply(text="What has been the hardest part?", picture=felt("tired")),
                             Reply(text="What changed?"))
    summaries_asked = []

    async def complete(messages, schema, **kwargs):
        if schema is Extraction:
            summaries_asked.append(messages)
            if len(summaries_asked) == 1:
                raise TimeoutError("provider timed out")
            return client.Call(value=Extraction(summary="Work has been hard."), model="test/model",
                               usage=llm_calls.Usage(), latency_ms=1, call_id=uuid.uuid4())
        return await scripted(messages, schema, **kwargs)

    monkeypatch.setattr(orchestrator.client, "complete", complete)
    monkeypatch.setattr(get_settings(), "context_budget_chars", 40)
    thread = await start(alice)
    await runner.send(alice, thread.id, "work has been hard lately, every single day of it")
    turn = await runner.send(alice, thread.id, "and nobody at work seems to notice how much I carry")

    first = await orchestrator.follow_up(alice, thread.id, turn.message_id)
    assert first.understanding is not None and not first.summarized and first.pending
    assert (await _waiting(thread.id))["reading"] is None

    second = await orchestrator.follow_up(alice, thread.id, turn.message_id)

    assert second.summarized and second.understanding is None and not second.pending
    assert len(scripted.reads) == 1, "the reading that landed is not paid for again"
    assert len(summaries_asked) == 2 and await _waiting(thread.id) is None


async def test_work_being_run_is_not_run_twice_until_its_claim_runs_out(alice, model):
    """A double tap or a retry while the first request still works costs nothing; a request that died frees it."""
    scripted = model(Reply(text="That sounds lonely. What happened?", picture=felt("lonely")))
    thread = await start(alice)
    turn = await runner.send(alice, thread.id, "my brother never calls")
    async with pool.as_user(alice) as conn:
        assert await threads.claim_pending_follow_up(conn, thread.id, alice.user_id, turn.message_id) is not None

    assert await orchestrator.follow_up(alice, thread.id, turn.message_id) is None
    assert scripted.reads == []

    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.threads set pending_follow_up = pending_follow_up || "
            "jsonb_build_object('claimed_at', now() - make_interval(secs => $2)) where id = $1",
            thread.id, threads.FOLLOW_UP_CLAIM_SECONDS + 1,
        )

    done = await orchestrator.follow_up(alice, thread.id, turn.message_id)

    assert done.understanding is not None and len(scripted.reads) == 1


async def test_a_reading_of_a_reply_an_edit_took_back_is_not_applied(alice, model):
    """An edit takes back the reply and restores the record from before it. A reading of that reply already on its way
    lands on nothing it belongs to, so it is dropped, not merged onto the restored record."""
    model(
        Reply(text="That sounds lonely. What happened?", picture=felt("lonely")),
        Reply(text="That sounds tiring. What happened?"),
    )
    thread = await start(alice)
    await runner.send(alice, thread.id, "Supportive")
    first = await runner.send(alice, thread.id, "my brother never calls")
    async with pool.as_user(alice) as conn:
        waiting = await threads.claim_pending_follow_up(conn, thread.id, alice.user_id, first.message_id)
    await runner.edit(alice, thread.id, await _last_user_message_id(thread.id), "work has been exhausting")

    landed = await orchestrator.read_understanding(alice, orchestrator.ReadAfter.from_stored(waiting["reading"]))

    assert landed is None
    picture = (await _thread_row(alice, thread.id)).understanding.get("picture") or {}
    assert {"feeling": "lonely"} not in (picture.get("feelings") or [])


async def test_a_reading_that_outlasts_its_deadline_waits_for_the_next_request(alice, model, monkeypatch):
    """The work ends well inside its claim, so no second request runs it again while it still runs."""
    assert orchestrator.FOLLOW_UP_DEADLINE_SECONDS < threads.FOLLOW_UP_CLAIM_SECONDS
    scripted = model(Reply(text="That sounds lonely. What happened?", picture=felt("lonely")))
    thread = await start(alice)
    turn = await runner.send(alice, thread.id, "my brother never calls")

    async def slow(messages, schema, **kwargs):
        if schema is ConversationUnderstanding:
            await asyncio.sleep(1)
        return await scripted(messages, schema, **kwargs)

    monkeypatch.setattr(orchestrator.client, "complete", slow)
    monkeypatch.setattr(orchestrator, "FOLLOW_UP_DEADLINE_SECONDS", 0.05)

    done = await orchestrator.follow_up(alice, thread.id, turn.message_id)

    assert done.understanding is None and done.pending
    assert (await _waiting(thread.id))["reading"] is not None


async def _quiet_for(thread_id, age: dt.timedelta) -> None:
    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.threads set last_message_at = now() - make_interval(secs => $2) where id = $1",
            thread_id, age.total_seconds(),
        )


async def test_a_reading_the_app_never_asked_for_is_run_by_the_schedule_once_the_reply_is_quiet(alice, model):
    """A tab closed straight after the reply never asks. A reply still on screen is left for the app."""
    scripted = model(Reply(text="That sounds lonely. What happened?", picture=felt("lonely")))
    thread = await start(alice)
    await runner.send(alice, thread.id, "my brother never calls")

    await catch_up.follow_ups()
    assert scripted.reads == [], "the app still has its chance to ask"

    await _quiet_for(thread.id, catch_up.QUIET_AFTER + dt.timedelta(seconds=1))
    await catch_up.follow_ups()

    assert (await _thread_row(alice, thread.id)).understanding["picture"]["feelings"] == [{"feeling": "lonely"}]
    assert await _waiting(thread.id) is None


async def test_the_schedule_gives_up_on_work_that_kept_failing(alice, model):
    """Work still waiting long after its reply is left, so a reading that always fails is not paid for every run."""
    scripted = model(Reply(text="That sounds lonely. What happened?", picture=felt("lonely")))
    thread = await start(alice)
    await runner.send(alice, thread.id, "my brother never calls")
    await _quiet_for(thread.id, catch_up.GIVE_UP_AFTER + dt.timedelta(seconds=1))

    await catch_up.follow_ups()

    assert scripted.reads == []


async def test_finishing_an_older_reply_leaves_the_next_turns_work_alone(alice, model):
    """A request for reply one that ends after their next message must not clear or rewrite what reply two left."""
    model(
        Reply(text="That sounds lonely. What happened?", picture=felt("lonely")),
        Reply(text="What did you hope he would say?"),
    )
    thread = await start(alice)
    first = await runner.send(alice, thread.id, "my brother never calls")
    async with pool.as_user(alice) as conn:
        await threads.claim_pending_follow_up(conn, thread.id, alice.user_id, first.message_id)
    second = await runner.send(alice, thread.id, "he only calls when he needs something")

    async with pool.as_user(alice) as conn:
        await threads.settle_pending_follow_up(conn, thread.id, alice.user_id, first.message_id, None)

    assert (await _waiting(thread.id))["message_id"] == str(second.message_id)


async def test_the_schedule_passes_over_work_the_app_is_running(alice, model):
    """Work the app has claimed is not counted against the run's limit or touched; its claim decides."""
    scripted = model(Reply(text="That sounds lonely. What happened?", picture=felt("lonely")))
    thread = await start(alice)
    turn = await runner.send(alice, thread.id, "my brother never calls")
    async with pool.as_user(alice) as conn:
        await threads.claim_pending_follow_up(conn, thread.id, alice.user_id, turn.message_id)
    await _quiet_for(thread.id, catch_up.QUIET_AFTER + dt.timedelta(seconds=1))

    async with pool.as_admin() as conn:
        now = dt.datetime.now(dt.UTC)
        waiting = await threads.waiting_follow_ups(conn, now - catch_up.QUIET_AFTER, now - catch_up.GIVE_UP_AFTER, 10_000)

    assert thread.id not in [row["thread_id"] for row in waiting]
    assert scripted.reads == []


async def test_another_person_cannot_run_what_waits(alice, model):
    scripted = model(Reply(text="That sounds lonely. What happened?", picture=felt("lonely")))
    thread = await start(alice)
    turn = await runner.send(alice, thread.id, "my brother never calls")

    assert await orchestrator.follow_up(claims_for(uuid.uuid4()), thread.id, turn.message_id) is None
    assert scripted.reads == []
    assert await _waiting(thread.id) is not None
