# ABOUTME: Exercises the query layer against a live database, as a real user would be.
# ABOUTME: Covers the composed turn read, the batched write, and the old leak's shape.

import uuid

import asyncpg
import pytest

from mani.auth.jwt import Claims
from mani.config import get_settings
from mani.db import config_tables, llm_calls, messages, profiles, summaries, threads
from mani.models.rows import (
    ResponseStyle,
    TechniqueOutcome,
    TechniqueState,
    TechniqueTried,
)

ALICE = uuid.UUID("a0000000-0000-4000-8000-0000000000c1")
BOB = uuid.UUID("a0000000-0000-4000-8000-0000000000c2")


def claims_for(user_id: uuid.UUID) -> Claims:
    return Claims(sub=str(user_id), raw={"sub": str(user_id), "role": "authenticated"})


async def reachable() -> bool:
    try:
        conn = await asyncpg.connect(get_settings().database_url, timeout=3)
    except (OSError, asyncpg.PostgresError):
        return False
    await conn.close()
    return True


@pytest.fixture
async def users():
    if not await reachable():
        pytest.skip("no database reachable; run `supabase start`")
    from mani.db import pool

    await pool.open_pool()
    async with pool.as_admin() as conn:
        await conn.execute("delete from auth.users where id = any($1::uuid[])", [ALICE, BOB])
        await conn.execute(
            "insert into auth.users (id, email) values ($1,'c1@t.test'),($2,'c2@t.test')",
            ALICE, BOB)
    try:
        yield
    finally:
        async with pool.as_admin() as conn:
            await conn.execute("delete from auth.users where id = any($1::uuid[])",
                               [ALICE, BOB])
        await pool.close_pool()


@pytest.fixture
async def alice(users):
    from mani.db import pool

    async with pool.as_user(claims_for(ALICE)) as conn:
        yield conn


async def test_a_thread_round_trips(alice):
    thread, _ = await threads.create_or_reuse(alice, ALICE, title="First")
    assert await threads.get(alice, thread.id, ALICE) is not None
    page = await threads.list_for_user(alice, ALICE)
    assert [t.id for t in page.threads] == [thread.id]


async def test_a_soft_deleted_thread_disappears_from_listings(alice):
    thread, _ = await threads.create_or_reuse(alice, ALICE)
    assert await threads.soft_delete(alice, thread.id, ALICE) is True
    assert await threads.get(alice, thread.id, ALICE) is None
    assert await threads.list_for_user(alice, ALICE) == threads.Page([], None)


async def test_a_turn_writes_both_sides_and_is_idempotent(alice):
    thread, _ = await threads.create_or_reuse(alice, ALICE)
    client_id = uuid.uuid4()

    first = await messages.create_pair(
        alice, thread.id, "I had a hard day", "That sounds heavy.",
        prompt_options=[{"label": "Tell me more"}], client_message_id=client_id)
    assert first.was_duplicate is False

    again = await messages.create_pair(
        alice, thread.id, "I had a hard day", "a different reply",
        client_message_id=client_id)
    assert again.was_duplicate is True
    assert again.user_message_id == first.user_message_id

    history = await messages.recent_for_context(alice, thread.id, ALICE)
    assert [m.role for m in history] == ["user", "mani"]
    assert history[1].prompt_options == [{"label": "Tell me more"}]


async def test_the_idempotency_lookup_is_user_scoped(alice, users):
    """A guessed client id must not surface someone else's message."""
    from mani.db import pool

    thread, _ = await threads.create_or_reuse(alice, ALICE)
    client_id = uuid.uuid4()
    await messages.create_pair(alice, thread.id, "private", "reply",
                               client_message_id=client_id)

    async with pool.as_user(claims_for(BOB)) as bob:
        assert await messages.find_by_client_id(bob, BOB, client_id) is None


async def test_listing_another_users_thread_returns_nothing(alice, users):
    """The previous system's live defect, from the query layer's side."""
    from mani.db import pool

    thread, _ = await threads.create_or_reuse(alice, ALICE)
    await messages.create_pair(alice, thread.id, "something private", "reply")

    async with pool.as_user(claims_for(BOB)) as bob:
        page = await messages.list_for_thread(bob, thread.id, BOB)
    assert page.messages == []


async def test_a_greeting_cannot_be_used_to_forge_later_turns(alice):
    thread, _ = await threads.create_or_reuse(alice, ALICE)
    await messages.create_greeting(alice, thread.id, "Hi. It's Mani.")

    with pytest.raises(asyncpg.PostgresError):
        await messages.create_greeting(alice, thread.id, "and another thing")


async def test_the_composed_read_returns_the_whole_turn(alice):
    thread, _ = await threads.create_or_reuse(alice, ALICE)
    await profiles.upsert(alice, ALICE, nickname="Al", topics=["anxiety"],
                          support_style="reflective")
    await threads.apply(alice, thread.id, ALICE, threads.ThreadUpdates(
        technique=TechniqueState(
            thread_id=thread.id, framework_id="thought_reframe",
            outcome=TechniqueOutcome.OFFERED, phase="offering", at_message_count=2),
        offer_frameworks=["thought_reframe"],
        style=ResponseStyle(shape="mirror and ask", voice="naming"),
    ))
    await summaries.upsert(
        alice, thread.id, ALICE, summary="Talked about work.",
        techniques_tried=[TechniqueTried(name="thought_reframe", helpful=True)],
        summarized_through_message_id=None, summarized_message_count=2)

    ctx = await threads.load_turn_context(alice, thread.id, ALICE)
    assert ctx is not None
    assert ctx.profile.nickname == "Al"
    assert ctx.profile.support_style == "reflective"
    assert ctx.technique.framework_id == "thought_reframe"
    assert ctx.technique.outcome == TechniqueOutcome.OFFERED
    assert ctx.techniques_offered == ["thought_reframe"]
    assert ctx.recent_styles[0].shape == "mirror and ask"
    assert ctx.summary.summary == "Talked about work."
    assert ctx.summary.techniques_tried[0].name == "thought_reframe"


async def test_a_conversation_style_survives_the_round_trip(alice):
    """The only thing that catches a missing column grant. `grant update (...)` in 001 is
    column-scoped, so a new column inherits nothing and fails at runtime with 42501 -
    taking the whole turn's transaction with it, message pair included."""
    from mani.models.rows import SupportStyle

    thread, _ = await threads.create_or_reuse(alice, ALICE)
    assert thread.conversation_style is None

    await threads.apply(
        alice, thread.id, ALICE,
        threads.ThreadUpdates(conversation_style=SupportStyle.DIRECT),
    )

    reread = await threads.get(alice, thread.id, ALICE)
    assert reread.conversation_style is SupportStyle.DIRECT

    ctx = await threads.load_turn_context(alice, thread.id, ALICE)
    assert ctx.thread.conversation_style is SupportStyle.DIRECT


async def test_the_composed_read_refuses_another_users_thread(alice, users):
    from mani.db import pool

    thread, _ = await threads.create_or_reuse(alice, ALICE)
    async with pool.as_user(claims_for(BOB)) as bob:
        assert await threads.load_turn_context(bob, thread.id, BOB) is None


async def test_offering_the_same_technique_twice_stores_it_once(alice):
    """A composite primary key, rather than merging an array in application code."""
    thread, _ = await threads.create_or_reuse(alice, ALICE)
    for _ in range(3):
        await threads.apply(alice, thread.id, ALICE,
                            threads.ThreadUpdates(offer_frameworks=["abcde"]))

    ctx = await threads.load_turn_context(alice, thread.id, ALICE)
    assert ctx.techniques_offered == ["abcde"]


async def test_a_turn_keeps_its_halves_in_order(alice):
    """now() is fixed per transaction, so both halves of a pair would share a timestamp
    and their order would be undefined. The previous project shipped that, hit it, and
    patched it by adding a millisecond to Mani's row."""
    thread, _ = await threads.create_or_reuse(alice, ALICE)
    for n in range(5):
        await messages.create_pair(alice, thread.id, f"user {n}", f"mani {n}")

    history = await messages.recent_for_context(alice, thread.id, ALICE, limit=10)
    assert [m.content for m in history] == [
        c for n in range(5) for c in (f"user {n}", f"mani {n}")
    ]


async def test_the_style_window_keeps_only_the_recent_ones(alice):
    thread, _ = await threads.create_or_reuse(alice, ALICE)
    for n in range(10):
        await threads.apply(alice, thread.id, ALICE, threads.ThreadUpdates(
            style=ResponseStyle(shape=f"shape-{n}", voice=None)))

    ctx = await threads.load_turn_context(alice, thread.id, ALICE)
    assert len(ctx.recent_styles) == threads.STYLE_WINDOW
    assert ctx.recent_styles[-1].shape == "shape-9"


async def test_an_empty_update_touches_nothing(alice):
    thread, _ = await threads.create_or_reuse(alice, ALICE)
    await threads.apply(alice, thread.id, ALICE, threads.ThreadUpdates())
    ctx = await threads.load_turn_context(alice, thread.id, ALICE)
    assert ctx.technique is None and ctx.techniques_offered == []


async def test_a_crisis_is_recorded_with_its_reason(alice):
    thread, _ = await threads.create_or_reuse(alice, ALICE)
    event_id = await threads.mark_crisis(alice, thread.id, "expressed suicidal ideation")

    refreshed = await threads.get(alice, thread.id, ALICE)
    assert refreshed.crisis_detected is True

    # A user cannot read admin.crisis_events, which is the point - so step out of the
    # role to check the row landed. Same connection, because the fixture's transaction
    # has not committed and another connection would not see it yet.
    await alice.execute("reset role")
    row = await alice.fetchrow(
        "select reason, detected_at from admin.crisis_events where id = $1", event_id)
    assert row["reason"] == "expressed suicidal ideation"
    assert row["detected_at"] is not None


async def test_the_summary_checkpoint_must_be_a_real_message(alice):
    """A foreign key refuses the id-namespace confusion the previous version had."""
    thread, _ = await threads.create_or_reuse(alice, ALICE)
    with pytest.raises(asyncpg.PostgresError):
        await summaries.upsert(
            alice, thread.id, ALICE, summary="x", techniques_tried=[],
            summarized_through_message_id=uuid.uuid4(),  # not a message id
            summarized_message_count=1)


async def test_config_tables_are_readable_and_seeded(users):
    from mani.db import pool

    async with pool.as_admin() as conn:
        prompts = await config_tables.list_active_prompts(conn)
        frameworks = await config_tables.list_active_frameworks(conn)

    # The two authored layers. The framework catalogue between them is generated from the
    # registry at compose time, so it is deliberately not a row here.
    assert {p.name for p in prompts} >= {"mani_base", "response_format"}
    assert "framework_index" not in {p.name for p in prompts}
    assert {f.id for f in frameworks} == {
        "abcde", "thought_reframe", "behavioral_activation",
        "structured_problem_solving", "act_choice_point", "dbt_stop",
    }
    assert frameworks[0].phases[0] == "offering"


async def test_a_model_call_is_recorded_with_its_cost(users):
    from mani.db import pool

    async with pool.as_admin() as conn:
        await llm_calls.record(
            conn, purpose=llm_calls.Purpose.CHAT, model="google/gemini-3-flash-preview",
            outcome=llm_calls.Outcome.OK, latency_ms=4200, user_id=ALICE,
            usage=llm_calls.Usage(input_tokens=8230, output_tokens=385))
        spend = await llm_calls.spend_since(conn, ALICE)

    assert spend["input_tokens"] == 8230
    assert spend["calls"] == 1
