# ABOUTME: What a turn leaves for after its reply (only the summary, when it falls due) waits on the thread until the
# ABOUTME: app or the schedule asks for it, then runs once. Against a live database with a scripted model.

import datetime as dt
import uuid

import pytest

from mani import catch_up
from mani.chat import runner, turn as chat_turn
from mani.config import get_settings
from mani.db import llm_calls, pool, summaries, threads
from mani.llm import client
from mani.llm.schema import Extraction
from tests.integration.fixtures import ScriptedModel, claims_for, said, start


async def _waiting(thread_id) -> dict | None:
    async with pool.as_admin() as conn:
        return await conn.fetchval("select pending_follow_up from public.threads where id = $1", thread_id)


async def _quiet_for(thread_id, age: dt.timedelta) -> None:
    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.threads set last_message_at = now() - make_interval(secs => $2) where id = $1",
            thread_id, age.total_seconds(),
        )


@pytest.fixture
def summary_due(monkeypatch):
    """A scripted chat, and a window so small that every turn leaves messages a summary must cover. `fails` makes
    the first summary call fail."""
    def install(fails: bool = False):
        scripted = ScriptedModel(said("What has been the hardest part?"), said("What changed?"))
        asked = []

        async def complete(messages, schema, **kwargs):
            if schema is Extraction:
                asked.append(messages)
                if fails and len(asked) == 1:
                    raise TimeoutError("provider timed out")
                return client.Call(value=Extraction(summary="Work has been hard."), model="test/model",
                                   usage=llm_calls.Usage(), latency_ms=1, call_id=uuid.uuid4())
            return await scripted(messages, schema, **kwargs)

        monkeypatch.setattr(client, "complete", complete)
        monkeypatch.setattr(get_settings(), "context_budget_chars", 40)
        return asked

    return install


async def _two_turns(alice):
    thread = await start(alice)
    await runner.send(alice, thread.id, "work has been hard lately, every single day of it")
    return thread, await runner.send(alice, thread.id, "and nobody at work seems to notice how much I carry")


async def test_a_turn_with_a_summary_due_leaves_only_the_summary_pending(alice, summary_due):
    asked = summary_due()
    thread, turn = await _two_turns(alice)
    assert await _waiting(thread.id) == {"message_id": str(turn.message_id), "summary": True}
    assert asked == [], "nothing is summarized until the app asks"


async def test_a_turn_with_no_summary_due_leaves_nothing_waiting(alice, model):
    model(said("What happened?"))
    thread = await start(alice)
    await runner.send(alice, thread.id, "my brother never calls")
    assert await _waiting(thread.id) is None


async def test_the_summary_runs_once_when_the_app_asks(alice, summary_due):
    asked = summary_due()
    thread, turn = await _two_turns(alice)

    done = await chat_turn.follow_up(alice, thread.id, turn.message_id)

    assert done.summarized and not done.pending and len(asked) == 1
    assert await _waiting(thread.id) is None
    async with pool.as_user(alice) as conn:
        assert (await summaries.get(conn, thread.id)).summary == "Work has been hard."
    assert await chat_turn.follow_up(alice, thread.id, turn.message_id) is None


async def test_a_request_for_another_reply_runs_nothing_and_leaves_the_waiting_one(alice, summary_due):
    asked = summary_due()
    thread, turn = await _two_turns(alice)
    assert await chat_turn.follow_up(alice, thread.id, thread.id) is None
    assert asked == [] and (await _waiting(thread.id))["message_id"] == str(turn.message_id)


async def test_a_summary_that_fails_waits_to_be_asked_for_again(alice, summary_due):
    asked = summary_due(fails=True)
    thread, turn = await _two_turns(alice)

    first = await chat_turn.follow_up(alice, thread.id, turn.message_id)
    assert not first.summarized and first.pending and (await _waiting(thread.id))["summary"] is True

    second = await chat_turn.follow_up(alice, thread.id, turn.message_id)
    assert second.summarized and not second.pending and len(asked) == 2
    assert await _waiting(thread.id) is None


async def test_work_being_run_is_not_run_twice_until_its_claim_runs_out(alice, summary_due):
    asked = summary_due()
    thread, turn = await _two_turns(alice)
    async with pool.as_user(alice) as conn:
        assert await threads.claim_pending_follow_up(conn, thread.id, alice.user_id, turn.message_id) is not None
    assert await chat_turn.follow_up(alice, thread.id, turn.message_id) is None and asked == []

    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.threads set pending_follow_up = pending_follow_up || "
            "jsonb_build_object('claimed_at', now() - make_interval(secs => $2)) where id = $1",
            thread.id, threads.FOLLOW_UP_CLAIM_SECONDS + 1,
        )
    assert (await chat_turn.follow_up(alice, thread.id, turn.message_id)).summarized


async def test_a_summary_the_app_never_asked_for_is_run_by_the_schedule_once_the_reply_is_quiet(alice, summary_due):
    asked = summary_due()
    thread, _ = await _two_turns(alice)

    await catch_up.follow_ups()
    assert asked == [], "the app still has its chance to ask"

    await _quiet_for(thread.id, catch_up.QUIET_AFTER + dt.timedelta(seconds=1))
    await catch_up.follow_ups()
    assert len(asked) == 1 and await _waiting(thread.id) is None


async def test_another_person_cannot_run_what_waits(alice, summary_due):
    asked = summary_due()
    thread, turn = await _two_turns(alice)
    assert await chat_turn.follow_up(claims_for(uuid.uuid4()), thread.id, turn.message_id) is None
    assert asked == [] and await _waiting(thread.id) is not None
