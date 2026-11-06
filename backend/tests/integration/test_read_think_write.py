# ABOUTME: A turn reads, calls the model holding no database connection, then writes (chat/runner.py).
# ABOUTME: Against a live database with a scripted model: what holds while the model thinks, and after.

import asyncio
import uuid

import pytest

from mani.chat import orchestrator, runner
from mani.config import get_settings
from mani.db import pool
from mani.errors import ErrorCategory, ServiceError
from mani.llm.schema import Reply
from mani.prompts import cache
from tests.integration.test_turn import (  # noqa: F401 - alice and model are fixtures
    ALICE,
    ScriptedModel,
    _last_user_message_id,
    _thread_row,
    _user_messages,
    alice,
    felt,
    model,
    past_the_opening,
    send,
    start,
)


def _checked_out() -> int:
    """Connections in this process's pool that someone holds right now."""
    held = pool.get_pool()
    return held.get_size() - held.get_idle_size()


class _HoldsNothing(ScriptedModel):
    """A model that notes, each time it is asked, how many pool connections are held while it thinks."""

    def __init__(self, *replies: Reply) -> None:
        super().__init__(*replies)
        self.held_while_thinking: list[int] = []

    async def __call__(self, messages, schema, **kwargs):
        self.held_while_thinking.append(_checked_out())
        return await super().__call__(messages, schema, **kwargs)


async def _mani_messages(thread_id) -> list[str]:
    async with pool.as_admin() as conn:
        rows = await conn.fetch(
            "select content from public.messages where thread_id = $1 and role = 'mani' order by created_at", thread_id
        )
    return [r["content"] for r in rows]


async def test_no_connection_is_held_while_the_model_thinks_on_a_send_or_an_edit(alice, monkeypatch):
    """A turn held its transaction across the model call (6 to 30 s), so ten turns in flight emptied the
    pool and hung the instance (2026-11-05). The read commits or rolls back before the model is asked."""
    thinking = _HoldsNothing(Reply(text="What has been the hardest part?"), Reply(text="What changed?"))
    monkeypatch.setattr(orchestrator.client, "complete", thinking)
    thread = await past_the_opening(await start(alice))

    await runner.send(alice, thread.id, "work has been hard lately")
    await runner.edit(alice, thread.id, await _last_user_message_id(thread.id), "work has been hard this year")

    assert thinking.calls == 2
    assert thinking.held_while_thinking == [0, 0]
    assert await _user_messages(thread.id) == ["work has been hard this year"]


async def test_the_same_message_on_two_instances_at_once_stores_one_turn(alice, monkeypatch):
    """Two instances do not share the in-process wait on a message id, so both read before either writes and
    both pay. The second write finds the first's turn under the thread lock and returns it."""
    slow = ScriptedModel(Reply(text="What has been the hardest part?"))
    real = slow.__call__

    async def thinking(*args, **kwargs):
        await asyncio.sleep(0.3)
        return await real(*args, **kwargs)

    monkeypatch.setattr(orchestrator.client, "complete", thinking)
    thread = await past_the_opening(await start(alice))
    client_message_id = uuid.uuid4()

    config = await cache.load()

    def on_its_own_instance():
        async def steps(conn, ask):
            return await orchestrator.send(
                conn, alice, thread.id, "work was hard", client_message_id, ask=ask, config=config
            )
        return runner.run(alice, thread.id, steps)

    first, second = await asyncio.gather(on_its_own_instance(), on_its_own_instance())

    assert slow.calls == 2
    assert first.message_id == second.message_id
    assert {first.was_duplicate, second.was_duplicate} == {False, True}
    assert await _user_messages(thread.id) == ["work was hard"]


@pytest.mark.parametrize("fails", ["while_thinking", "at_the_write"])
async def test_a_failed_edit_leaves_the_original_exchange_in_place(alice, monkeypatch, fails):
    """The edit's promise: the original message and Mani's reply stay unless the new turn is written."""
    first = ScriptedModel(Reply(text="What has been the hardest part?"))
    monkeypatch.setattr(orchestrator.client, "complete", first)
    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "work has been hard lately")
    before = await _thread_row(alice, thread.id)
    said = await _mani_messages(thread.id)

    async def timed_out(messages, schema, **kwargs):
        raise ServiceError("provider timed out", ErrorCategory.LLM_TIMEOUT, retryable=True)

    # Leaked script metadata only: empty once repaired, so the write refuses it.
    empty = ScriptedModel(Reply(text="(Include prompts: Yes, No)"))
    monkeypatch.setattr(orchestrator.client, "complete", timed_out if fails == "while_thinking" else empty)
    with pytest.raises(ServiceError):
        await runner.edit(alice, thread.id, await _last_user_message_id(thread.id), "it's more that I'm tired")

    assert await _user_messages(thread.id) == ["work has been hard lately"]
    assert await _mani_messages(thread.id) == said
    after = await _thread_row(alice, thread.id)
    assert (after.message_count, after.understanding) == (before.message_count, before.understanding)


async def test_a_reading_that_lands_while_the_next_reply_is_thought_is_kept(alice, monkeypatch):
    """The reading after a reply runs in the background, so it can land while the next message's model call
    runs. The write rebuilds from the thread as it is then, so the reading is merged, never written over."""
    scripted = ScriptedModel(
        Reply(text="That sounds lonely. What happened?", picture=felt("lonely")),
        Reply(text="What did you hope he would say?", heart="core_named"),
    )
    monkeypatch.setattr(orchestrator.client, "complete", scripted)
    thread = await start(alice)
    first = await runner.send(alice, thread.id, "my brother never calls")

    landed = []

    async def reading_lands_meanwhile(messages, schema, **kwargs):
        reply = await scripted(messages, schema, **kwargs)
        if not landed:
            landed.append(await orchestrator.read_understanding(alice, first.read_after))
        return reply

    monkeypatch.setattr(orchestrator.client, "complete", reading_lands_meanwhile)
    await runner.send(alice, thread.id, "he only calls when he needs something")

    stored = (await _thread_row(alice, thread.id)).understanding
    assert stored["heart"] == "core_named", "the later turn is written"
    assert stored["picture"]["feelings"] == [{"feeling": "lonely"}], "the reading that landed meanwhile is kept"


async def test_past_the_minute_limit_a_turn_is_refused_and_a_crisis_still_answered(alice, model, monkeypatch):
    scripted = model(Reply(text="What has been the hardest part?"))
    monkeypatch.setattr(get_settings(), "minute_message_limit", 2)
    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "work has been hard lately")
    await send(alice, thread.id, "and it's getting worse")

    with pytest.raises(ServiceError) as refused:
        await send(alice, thread.id, "and my manager noticed")
    assert refused.value.category is ErrorCategory.RATE_LIMITED and refused.value.status_code == 429
    assert refused.value.retryable
    assert refused.value.user_message == (
        "You're sending messages faster than Mani can answer. Please wait a minute and try again."
    )
    assert scripted.calls == 2

    turn = await send(alice, thread.id, "I am going to kill myself")
    assert turn.crisis_detected


async def test_an_empty_pool_refuses_quickly_as_busy_instead_of_hanging(alice, monkeypatch):
    monkeypatch.setattr(get_settings(), "db_acquire_timeout_seconds", 0.1)
    size = pool.get_pool().get_max_size()
    holders = [await pool.get_pool().acquire() for _ in range(size)]
    try:
        with pytest.raises(ServiceError) as refused:
            async with pool.as_user(alice):
                pass
    finally:
        for conn in holders:
            await pool.get_pool().release(conn)

    assert refused.value.category is ErrorCategory.BUSY and refused.value.status_code == 503
    assert refused.value.retryable
    assert refused.value.user_message == "Mani is busy right now. Please try again in a moment."
