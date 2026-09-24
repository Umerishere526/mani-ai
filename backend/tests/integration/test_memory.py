# ABOUTME: Folding finished conversations into the per-person memory, against a live database.
# ABOUTME: The model is scripted; the claim, the lock, the RLS scoping and the writes are real.

import datetime as dt
import uuid

import pytest

from mani import memory
from mani.chat import orchestrator
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
            value = Reply(text="What happens on those evenings?")
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
        thread, _ = await orchestrator.start_thread(conn, claims)
    async with pool.as_user(claims) as conn:
        await orchestrator.send(conn, claims, thread.id, text)
    return thread


async def _new_chat(claims):
    from mani.db import pool

    async with pool.as_user(claims) as conn:
        thread, created = await threads.create_or_reuse(conn, claims.user_id)
    assert created
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


async def test_starting_a_new_chat_folds_the_one_that_finished(bea, scripted):
    fake = scripted()
    first = await _chat(bea, "I always feel low on Sunday evenings because of work")
    second = await _new_chat(bea)

    assert await memory.fold_finished(bea, keep=second.id) == 1
    assert (await _stored(bea)).low_times == REMEMBERED.low_times
    assert await _folded_at(first.id) is not None

    # Nothing new has been said, so a second new chat costs nothing.
    assert await memory.fold_finished(bea, keep=second.id) == 0
    assert len(fake.folds) == 1


async def test_the_new_chat_itself_is_never_folded_and_carries_no_old_messages(bea, scripted):
    scripted()
    await _chat(bea, "I always feel low on Sunday evenings because of work")
    second = await _new_chat(bea)
    await memory.fold_finished(bea, keep=second.id)

    from mani.db import messages as messages_db, pool

    async with pool.as_user(bea) as conn:
        history = await messages_db.recent_for_context(conn, second.id, bea.user_id)
    assert all("Sunday" not in m.content for m in history)
    assert await _folded_at(second.id) is None


async def test_a_conversation_that_continues_is_folded_again_from_where_it_stopped(bea, scripted):
    fake = scripted()
    first = await _chat(bea, "I always feel low on Sunday evenings because of work")
    await memory.fold_finished(bea)

    from mani.db import pool

    async with pool.as_user(bea) as conn:
        await orchestrator.send(conn, bea, first.id, "walking the dog helped this week")
    await memory.fold_finished(bea)

    sent = fake.folds[-1][-1]["content"]
    assert "walking the dog" in sent
    assert "Sunday evenings because of work" not in sent.split("just finished")[1]


async def test_the_idle_job_leaves_a_conversation_that_is_still_going(bea, scripted):
    scripted()
    await _chat(bea, "I always feel low on Sunday evenings because of work")

    idle_before = dt.datetime.now(dt.UTC) - memory.IDLE_AFTER
    assert await memory.fold_finished(bea, idle_before=idle_before) == 0


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


async def test_the_idle_job_finds_a_quiet_conversation_and_not_a_live_one(bea, scripted):
    scripted()
    quiet = await _chat(bea, "I always feel low on Sunday evenings because of work")
    live = await _chat(bea, "today was fine actually")

    from mani.db import memory as memory_db, pool

    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.threads set last_message_at = now() - interval '2 days' where id = $1",
            quiet.id,
        )
        idle_before = dt.datetime.now(dt.UTC) - memory.IDLE_AFTER
        assert BEA in await memory_db.users_with_idle_threads(conn, idle_before, 100)

    assert await memory.fold_finished(bea, idle_before=idle_before) == 1
    assert await _folded_at(quiet.id) is not None
    assert await _folded_at(live.id) is None


async def test_the_next_chat_is_shaped_by_the_memory_but_carries_none_of_the_old_chat(
    bea, scripted, monkeypatch
):
    scripted()
    await _chat(bea, "I always feel low on Sunday evenings because of work")
    second = await _new_chat(bea)
    await memory.fold_finished(bea, keep=second.id)

    sent: list[list[dict]] = []

    async def watching(messages, schema, **kwargs):
        sent.append(messages)
        return client.Call(value=Reply(text="How has today been?"), model="test/model",
                           usage=llm_calls.Usage(), latency_ms=1, call_id=uuid.uuid4())

    monkeypatch.setattr(client, "complete", watching)
    from mani.db import pool

    async with pool.as_user(bea) as conn:
        await orchestrator.send(conn, bea, second.id, "hi")

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
