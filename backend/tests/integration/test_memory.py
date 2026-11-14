# ABOUTME: Folding finished conversations into the per-person memory, against a live database.
# ABOUTME: The model is scripted; the claim, the lock, the RLS scoping and the writes are real.

import datetime as dt
import uuid

import pytest

from mani import memory
from mani.chat import orchestrator, runner
from mani.db import llm_calls, threads
from mani.llm import client
from mani.llm.schema import Memory, Reply
from tests.integration.test_turn import claims_for, reachable
from tests.integration.cleanup import remove_test_users

BEA = uuid.UUID("a0000000-0000-4000-8000-0000000000d2")

REMEMBERED = Memory(low_times=["feels low on Sunday evenings, because of work on Monday"])


class Scripted:
    """Answers a chat turn with a Reply and a fold with a Memory, and keeps what it was sent."""

    def __init__(self, remembered: Memory = REMEMBERED, fail_fold: bool = False) -> None:
        self.remembered = remembered
        self.fail_fold = fail_fold
        self.folds: list[list[dict]] = []

    async def __call__(self, messages, schema, **kwargs):
        if schema is Memory:
            self.folds.append(messages)
            if self.fail_fold:
                raise RuntimeError("provider down")
            value = self.remembered
        else:
            # In the shape the turn asked for, as the real call returns it.
            value = schema.model_validate({"text": "What happens on those evenings?"})
        return client.Call(
            value=value, model="test/model",
            usage=llm_calls.Usage(input_tokens=10, output_tokens=5),
            latency_ms=1, call_id=uuid.uuid4(),
        )


@pytest.fixture
async def bea():
    if not await reachable():
        pytest.skip("no database reachable; run `supabase start`")
    from mani.db import pool

    await pool.open_pool()
    async with pool.as_admin() as conn:
        await remove_test_users(conn, BEA)
        await conn.execute("insert into auth.users (id, email) values ($1, 'd2@t.test')", BEA)
    try:
        yield claims_for(BEA)
    finally:
        async with pool.as_admin() as conn:
            await remove_test_users(conn, BEA)
        await pool.close_pool()


@pytest.fixture
def scripted(monkeypatch):
    def install(**kwargs) -> Scripted:
        fake = Scripted(**kwargs)
        monkeypatch.setattr(client, "complete", fake)
        return fake

    return install


async def _chat(claims, text: str):
    from mani.db import pool

    async with pool.as_user(claims) as conn:
        thread = await orchestrator.start_thread(conn, claims)
    await runner.send(claims, thread.id, text)
    return thread


async def _new_chat(claims):
    from mani.db import pool

    async with pool.as_user(claims) as conn:
        thread = await threads.create(conn, claims.user_id)
    return thread


async def _stored(claims):
    from mani.db import pool, memory as memory_db

    async with pool.as_user(claims) as conn:
        return await memory_db.get(conn, claims.user_id)


async def _folded_at(thread_id):
    from mani.db import pool

    async with pool.as_admin() as conn:
        return await conn.fetchval(
            "select memory_folded_at from public.threads where id = $1", thread_id
        )


async def test_a_finished_chat_is_folded_into_the_memory_once(bea, scripted):
    fake = scripted()
    first = await _chat(bea, "I always feel low on Sunday evenings because of work")

    assert await memory.fold_finished(bea) == 1
    assert (await _stored(bea)).low_times == REMEMBERED.low_times
    assert await _folded_at(first.id) is not None

    # Nothing new has been said, so folding again costs nothing.
    assert await memory.fold_finished(bea) == 0
    assert len(fake.folds) == 1


async def test_a_conversation_that_continues_is_folded_again_from_where_it_stopped(bea, scripted):
    fake = scripted()
    first = await _chat(bea, "I always feel low on Sunday evenings because of work")
    await memory.fold_finished(bea)

    await runner.send(bea, first.id, "walking the dog helped this week")
    await memory.fold_finished(bea)

    sent = fake.folds[-1][-1]["content"]
    assert "walking the dog" in sent
    assert "Sunday evenings because of work" not in sent.split("just finished")[1]


async def test_the_idle_job_leaves_a_conversation_that_is_still_going(bea, scripted):
    scripted()
    await _chat(bea, "I always feel low on Sunday evenings because of work")

    idle_before = dt.datetime.now(dt.UTC) - memory.IDLE_AFTER
    assert await memory.fold_finished(bea, idle_before=idle_before) == 0


async def test_a_conversation_holding_only_a_style_tap_is_not_folded(bea, scripted):
    from mani.db import pool

    fake = scripted()
    async with pool.as_user(bea) as conn:
        tapped = await orchestrator.start_thread(conn, bea)
    turn = await runner.send(bea, tapped.id, "Supportive")
    assert turn.content == "How can I support you today?", "the greeting's style button, not a message"

    assert await memory.fold_finished(bea) == 0
    assert fake.folds == []
    assert await _folded_at(tapped.id) is None


async def test_a_crisis_conversation_is_never_folded(bea, scripted):
    fake = scripted()
    await _chat(bea, "I am going to kill myself")  # the safety screen flags this thread
    assert await memory.fold_finished(bea) == 0
    assert fake.folds == []


async def test_a_failed_fold_releases_its_claim(bea, scripted, caplog):
    scripted(fail_fold=True)
    first = await _chat(bea, "I always feel low on Sunday evenings because of work")

    with caplog.at_level("ERROR", logger="mani.memory"):
        assert await memory.fold_finished(bea) == 0
    assert await _folded_at(first.id) is None
    [record] = [r for r in caplog.records if r.name == "mani.memory"]
    assert "memory fold failed" in record.getMessage()
    assert "Sunday" not in caplog.text  # what they said never reaches the log


async def test_one_run_folds_no_more_than_its_limit(bea, scripted, monkeypatch, caplog):
    """The backstop against a fold that never marks its thread done: it stops, and says so."""
    scripted()
    await _chat(bea, "I always feel low on Sunday evenings because of work")
    await _chat(bea, "work again this week")
    monkeypatch.setattr(memory, "MAX_FOLDS_PER_RUN", 1)

    with caplog.at_level("WARNING", logger="mani.memory"):
        assert await memory.fold_finished(bea) == 1
    assert "stopped at 1" in caplog.text
    assert await memory.fold_finished(bea) == 1  # the other one is still waiting, not lost


async def test_the_idle_job_folds_a_quiet_conversation_and_not_a_live_one(bea, scripted):
    """Someone who never taps New chat still has their quiet conversations remembered: the schedule folds them."""
    scripted()
    quiet = await _chat(bea, "I always feel low on Sunday evenings because of work")
    live = await _chat(bea, "today was fine actually")

    from mani.db import pool

    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.threads set last_message_at = now() - interval '30 hours' where id = $1",
            quiet.id,
        )
        # The local database also holds eval and chat-tester users, so a fixed batch size could
        # leave BEA outside an unordered page. Ask for everyone.
        everyone = await conn.fetchval("select count(*) from auth.users")

    await memory.fold_idle(limit=everyone)

    assert await _folded_at(quiet.id) is not None
    assert await _folded_at(live.id) is None


async def test_the_idle_job_gives_up_on_a_chat_it_could_not_fold_for_a_day(bea, scripted):
    """A fold that keeps failing is not paid for every run forever; the chat folds at their next New chat instead."""
    scripted()
    stale = await _chat(bea, "I always feel low on Sunday evenings because of work")

    from mani.db import pool

    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.threads set last_message_at = now() - $2::interval where id = $1",
            stale.id, memory.IDLE_AFTER + memory.FOLD_RETRY_FOR + dt.timedelta(hours=1),
        )
        everyone = await conn.fetchval("select count(*) from auth.users")

    await memory.fold_idle(limit=everyone)

    assert await _folded_at(stale.id) is None


async def test_the_idle_job_folds_no_more_chats_than_its_limit(bea, scripted):
    """The limit counts paid folds, not people: one person with many quiet chats cannot spend a whole run."""
    scripted()
    chats = [await _chat(bea, f"work has been hard, week {week}") for week in (1, 2)]

    from mani.db import pool

    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.threads set last_message_at = now() - interval '30 hours' where id = any($1::uuid[])",
            [chat.id for chat in chats],
        )

    assert await memory.fold_idle(limit=1) == 1
    assert [await _folded_at(chat.id) is not None for chat in chats].count(True) == 1


async def test_the_next_chat_is_shaped_by_the_memory_but_carries_none_of_the_old_chat(
    bea, scripted, monkeypatch
):
    scripted()
    await _chat(bea, "I always feel low on Sunday evenings because of work")
    second = await _new_chat(bea)
    await memory.fold_finished(bea)

    sent: list[list[dict]] = []

    async def watching(messages, schema, **kwargs):
        sent.append(messages)
        return client.Call(value=schema.model_validate({"text": "How has today been?"}), model="test/model",
                           usage=llm_calls.Usage(), latency_ms=1, call_id=uuid.uuid4())

    monkeypatch.setattr(client, "complete", watching)
    await runner.send(bea, second.id, "hi")

    system, *conversation = sent[-1]
    assert "feels low on Sunday evenings" in system["content"]
    assert not any("Sunday" in m["content"] for m in conversation)


async def test_an_admin_can_read_what_was_remembered_and_the_person_cannot(bea, scripted):
    scripted()
    await _chat(bea, "I always feel low on Sunday evenings because of work")
    await memory.fold_finished(bea)

    from mani.db import pool
    from mani.routers.admin import get_user_memory

    async with pool.as_admin() as conn:
        out = await get_user_memory(conn, BEA)
    assert out.memory.low_times == REMEMBERED.low_times

    # The person's own role - what PostgREST would give their token - reaches nothing.
    import asyncpg

    async with pool.as_admin() as conn:
        await conn.execute("set local role authenticated")
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await conn.fetch("select memory from admin.user_memory")


async def test_a_fold_can_record_its_own_cost_while_it_holds_the_thread(
    bea, scripted, monkeypatch
):
    """Found live, not by the other tests here: their fake model never writes a cost row.

    The real one does, on its own admin connection, and that row's foreign key to the
    thread has to take a key-share lock on the very row the fold has claimed. Claimed with
    FOR UPDATE, the two waited on each other through the application - a deadlock Postgres
    cannot see - until the pool timed out.
    """
    import asyncio

    fake = scripted()
    recorded: list[uuid.UUID | None] = []

    async def records_like_production(messages, schema, **kwargs):
        call = await fake(messages, schema, **kwargs)
        recorded.append(await client._record(
            purpose=kwargs["purpose"], model="test/model", outcome=llm_calls.Outcome.OK,
            usage=call.usage, latency_ms=1, user_id=kwargs.get("user_id"),
            thread_id=kwargs.get("thread_id"), prompt_version_id=None, error_message=None,
        ))
        return call

    monkeypatch.setattr(client, "complete", records_like_production)
    await _chat(bea, "I always feel low on Sunday evenings because of work")

    assert await asyncio.wait_for(memory.fold_finished(bea), timeout=15) == 1
    assert recorded[-1] is not None  # the cost row was written, not timed out and dropped
