# ABOUTME: Runs whole turns against a live database with a scripted model in place.
# ABOUTME: The model is faked; every write, policy and transition under test is real.

import uuid

import asyncpg
import pytest

from mani.auth.jwt import Claims
from mani.chat import context, crisis, orchestrator
from mani.config import get_settings
from mani.db import llm_calls, messages as messages_db, profiles, threads
from mani.llm import client
from mani.llm.schema import Crisis, Reply, SmartPrompt, Style, TechniqueState
from mani.models.rows import TechniqueOutcome

ALICE = uuid.UUID("a0000000-0000-4000-8000-0000000000d1")


def claims_for(user_id: uuid.UUID) -> Claims:
    return Claims(sub=str(user_id), raw={"sub": str(user_id), "role": "authenticated"})


class ScriptedModel:
    """A model that answers from a script, and counts how often it was asked.

    The count is the regression test for the behaviour this port exists to remove: the
    implementation ported from made up to twenty-one provider calls for one user message,
    because every output check it failed was answered by generating again.
    """

    def __init__(self, *replies: Reply) -> None:
        self._replies = list(replies)
        self.calls = 0
        self.last_messages: list[dict] | None = None

    async def __call__(self, messages, schema, **kwargs):
        self.calls += 1
        self.last_messages = messages
        reply = self._replies[min(self.calls - 1, len(self._replies) - 1)]
        return client.Call(
            value=reply,
            model="test/model",
            usage=llm_calls.Usage(input_tokens=100, output_tokens=20),
            latency_ms=1,
            call_id=None,
        )


class ScriptedChooser:
    """Stands in for the exercise-selection tool call, counting when it was needed.

    A completing framework is the only turn shape that reaches it, and only when the
    catalog actually has something for that framework - so `calls` is the regression test
    for the second provider call staying rare rather than becoming routine.
    """

    def __init__(self, chosen: str | None = None) -> None:
        self._chosen = chosen
        self.calls = 0
        self.kwargs: dict = {}

    async def __call__(self, candidates, framework_name, **kwargs):
        self.calls += 1
        self.kwargs = kwargs
        return self._chosen if self._chosen is not None else candidates[0]["id"]


async def reachable() -> bool:
    try:
        conn = await asyncpg.connect(get_settings().database_url, timeout=3)
    except (OSError, asyncpg.PostgresError):
        return False
    await conn.close()
    return True


@pytest.fixture
async def alice():
    if not await reachable():
        pytest.skip("no database reachable; run `supabase start`")
    from mani.db import pool

    await pool.open_pool()
    async with pool.as_admin() as conn:
        await conn.execute("delete from auth.users where id = $1", ALICE)
        await conn.execute(
            "insert into auth.users (id, email) values ($1, 'd1@t.test')", ALICE
        )
    try:
        yield claims_for(ALICE)
    finally:
        async with pool.as_admin() as conn:
            await conn.execute("delete from auth.users where id = $1", ALICE)
        await pool.close_pool()


@pytest.fixture
def model(monkeypatch):
    def install(*replies: Reply) -> ScriptedModel:
        scripted = ScriptedModel(*replies)
        monkeypatch.setattr(orchestrator.client, "complete", scripted)
        return scripted

    return install


async def start(claims: Claims):
    from mani.db import pool

    async with pool.as_user(claims) as conn:
        await profiles.upsert(conn, ALICE, nickname="Al")
        thread, _ = await orchestrator.start_thread(conn, claims)
    return thread


async def send(claims: Claims, thread_id, content, **kwargs):
    from mani.db import pool

    async with pool.as_user(claims) as conn:
        return await orchestrator.send(conn, claims, thread_id, content, **kwargs)


async def test_a_turn_costs_exactly_one_provider_call(alice, model):
    scripted = model(
        Reply(
            # Everything the six checks look at is wrong at once: leaked script text, a
            # phase jumped to out of order, a duplicated label, and four buttons.
            text="Here you go.\n\n**Mani:** breathe\n\n(Include prompts: yes/no)",
            prompts=[
                SmartPrompt(label="Tell me more"),
                SmartPrompt(label="tell me more"),
                SmartPrompt(label="Try it", technique="made_up_technique"),
                SmartPrompt(label="Later"),
                SmartPrompt(label="Not now"),
            ],
            state=TechniqueState(technique="abcde", step="examine"),
            style=Style(shape="mirror and ask", voice="naming"),
        )
    )
    thread = await start(alice)
    turn = await send(alice, thread.id, "I had a hard day")

    assert scripted.calls == 1
    assert "**Mani:**" not in turn.content
    assert [p.label for p in turn.prompts] == ["Tell me more", "Later", "Not now"]


async def test_the_turn_is_stored_and_the_thread_state_follows_it(alice, model):
    model(
        Reply(
            text="Want to try something with me?",
            prompts=[
                SmartPrompt(label="Yes, let's try it", technique="abcde"),
                SmartPrompt(label="Not right now", decline=True),
            ],
            state=TechniqueState(technique="abcde", step="offering"),
            style=Style(shape="warmth lead"),
        )
    )
    from mani.db import pool

    thread = await start(alice)
    await send(alice, thread.id, "everything feels like too much")

    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)

    assert ctx.technique.framework_id == "abcde"
    assert ctx.technique.outcome is TechniqueOutcome.OFFERED
    assert ctx.techniques_offered == ["abcde"]
    assert ctx.recent_styles[-1].shape == "warmth lead"
    assert [m.role for m in (await _history(alice, thread.id))][-2:] == ["user", "mani"]


async def test_tapping_the_offer_records_acceptance(alice, model):
    model(
        Reply(
            text="Want to try something?",
            prompts=[SmartPrompt(label="Yes, let's try it", technique="abcde")],
            state=TechniqueState(technique="abcde", step="offering"),
        ),
        Reply(
            text="Good. What happened first?",
            state=TechniqueState(technique="abcde", step="activate"),
        ),
    )
    from mani.db import pool

    thread = await start(alice)
    await send(alice, thread.id, "I keep spiralling")
    await send(alice, thread.id, "Yes, let's try it")

    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)

    assert ctx.technique.outcome is TechniqueOutcome.ACCEPTED
    assert ctx.technique.phase == "activate"


async def test_finishing_a_technique_retires_it_without_losing_the_turn(alice, model):
    """The turn after a technique lands is the normal successful path, not an edge case.

    Retiring the row is an UPDATE inside the turn's one transaction: if it is refused,
    the user's message and Mani's reply go down with it. The row has to survive, because
    at_message_count is what the next turn's cooldown is measured from.
    """
    model(Reply(text="How has the rest of the week been?"))
    from mani.db import pool

    thread = await start(alice)
    # The phase clamp only advances one step per turn, so the landed state is set
    # directly rather than walked through all six of abcde's phases.
    async with pool.as_user(alice) as conn:
        await threads.set_technique_outcome(
            conn, thread.id, ALICE, "abcde", TechniqueOutcome.ACCEPTED,
            at_message_count=2, phase="closing",
        )

    turn = await send(alice, thread.id, "that helped, thanks")

    assert turn.content == "How has the rest of the week been?"

    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)

    # Retired, not deleted: the framework is finished but the thread remembers running it.
    assert ctx.technique is not None
    assert ctx.technique.phase is None
    assert ctx.technique.outcome is TechniqueOutcome.ACCEPTED
    assert ctx.technique.at_message_count == 2
    assert "cooldown_passed: no" in context.build(ctx)
    assert [m.role for m in (await _history(alice, thread.id))][-2:] == ["user", "mani"]


async def _retire_abcde_on(alice, thread_id) -> None:
    """Land a thread on ABCDE's final phase, so the next turn is the completing one."""
    from mani.db import pool

    async with pool.as_user(alice) as conn:
        await threads.set_technique_outcome(
            conn, thread_id, ALICE, "abcde", TechniqueOutcome.ACCEPTED,
            at_message_count=2, phase="closing",
        )


@pytest.fixture
async def abcde_exercise(alice):
    """One exercise that names abcde, for the turns where the hand-off should fire.

    A fixture rather than seed content: the real catalog is empty, and the mechanism has
    to be provable before there is anything real in it.
    """
    from mani.db import pool

    async with pool.as_admin() as conn:
        exercise_id = await conn.fetchval(
            "insert into admin.exercises (title, category, audio_path, framework_id) "
            "values ('Settling after ABCDE', 'grounding', 'abcde/settle.mp3', 'abcde') "
            "returning id"
        )
    try:
        yield exercise_id
    finally:
        async with pool.as_admin() as conn:
            await conn.execute("delete from admin.exercises where id = $1", exercise_id)


async def test_a_completing_framework_with_no_exercise_still_costs_one_call(
    alice, model, monkeypatch
):
    """The production case today - the catalog is empty, so the hand-off's second call
    never happens and a completing turn costs exactly what every other turn costs."""
    scripted = model(Reply(text="How has the rest of the week been?"))
    chooser = ScriptedChooser()
    monkeypatch.setattr(orchestrator.client, "choose_exercise", chooser)

    thread = await start(alice)
    await _retire_abcde_on(alice, thread.id)

    turn = await send(alice, thread.id, "that helped, thanks")

    assert scripted.calls == 1
    assert chooser.calls == 0
    assert turn.exercise is None


async def test_a_completing_framework_hands_off_to_its_exercise(
    alice, model, monkeypatch, abcde_exercise
):
    """With something in the catalog for that framework, the turn spends a second call -
    a bound tool call - and the reply carries the exercise it chose."""
    scripted = model(Reply(text="How has the rest of the week been?"))
    chooser = ScriptedChooser()
    monkeypatch.setattr(orchestrator.client, "choose_exercise", chooser)

    thread = await start(alice)
    await _retire_abcde_on(alice, thread.id)

    turn = await send(alice, thread.id, "that helped, thanks")

    assert scripted.calls == 1
    assert chooser.calls == 1
    assert chooser.kwargs["purpose"] is llm_calls.Purpose.EXERCISE_SELECT
    assert turn.exercise is not None
    assert turn.exercise.id == abcde_exercise
    assert turn.exercise.framework_id == "abcde"


async def test_an_ordinary_turn_never_reaches_the_exercise_hand_off(
    alice, model, monkeypatch, abcde_exercise
):
    """The second call is scoped to a completing framework, not to having a catalog."""
    model(Reply(text="Tell me more about that."))
    chooser = ScriptedChooser()
    monkeypatch.setattr(orchestrator.client, "choose_exercise", chooser)

    thread = await start(alice)
    turn = await send(alice, thread.id, "I had a hard day")

    assert chooser.calls == 0
    assert turn.exercise is None


async def test_free_text_during_an_offer_leaves_it_open(alice, model):
    """The reference read silence as a decline, quietly halving the cooldown."""
    model(
        Reply(
            text="Want to try something?",
            prompts=[SmartPrompt(label="Yes, let's try it", technique="abcde")],
            state=TechniqueState(technique="abcde", step="offering"),
        ),
        Reply(text="Tell me about work, then."),
    )
    from mani.db import pool

    thread = await start(alice)
    await send(alice, thread.id, "I keep spiralling")
    await send(alice, thread.id, "actually can we talk about work instead")

    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)

    assert ctx.technique.outcome is TechniqueOutcome.OFFERED


async def test_a_crisis_answers_with_real_words_and_records_the_event(alice, model):
    """The reference returned an empty string here and stored no reason."""
    model(
        Reply(
            text="I hear you.",
            crisis=Crisis(reason="expressed suicidal ideation"),
        )
    )
    from mani.db import pool

    thread = await start(alice)
    turn = await send(alice, thread.id, "there is no point in me being here")

    assert turn.crisis_detected is True
    assert turn.content == crisis.CRISIS_REPLY
    assert turn.content.strip()

    async with pool.as_admin() as conn:
        event = await conn.fetchrow(
            "select reason, message_id from admin.crisis_events where thread_id = $1",
            thread.id,
        )
    assert event["reason"] == "expressed suicidal ideation"
    assert event["message_id"] is not None


async def test_the_safety_screen_locks_a_thread_with_no_provider_call(alice, model):
    """An explicit statement is caught before the model is ever asked anything - the
    scripted model has no reply queued, so a call here would raise, not just cost extra."""
    from mani.db import pool

    scripted = model()
    thread = await start(alice)
    turn = await send(alice, thread.id, "I am going to kill myself tonight.")

    assert scripted.calls == 0
    assert turn.crisis_detected is True
    assert turn.content.strip()

    async with pool.as_admin() as conn:
        event = await conn.fetchrow(
            "select reason from admin.crisis_events where thread_id = $1", thread.id
        )
    assert event["reason"] == "safety screen: suicide"


async def test_the_router_shortlist_reaches_the_prompt_without_a_second_call(alice, model):
    """The router runs in process; it must narrow the field without paying for it."""
    scripted = model(
        Reply(text="How is that affecting your days?"),
        Reply(text="What would it look like to take one step?"),
        Reply(text="What keeps that feeling from arriving?"),
    )
    thread = await start(alice)
    await send(alice, thread.id, "I have stopped answering people for a week now.")
    await send(alice, thread.id, "I know what I need to do, I just cannot make myself begin.")
    await send(alice, thread.id, "I keep waiting to want to do something, but it never comes.")

    assert scripted.calls == 3
    final_prompt = scripted.last_messages[-1]["content"]
    assert "framework_shortlist: behavioral_activation" in final_prompt


async def test_a_crisis_thread_refuses_another_turn(alice, model):
    model(Reply(text="I hear you.", crisis=Crisis(reason="hopelessness")))
    thread = await start(alice)
    await send(alice, thread.id, "there is no point")

    from mani.errors import ServiceError

    with pytest.raises(ServiceError):
        await send(alice, thread.id, "are you there")


async def test_a_retried_send_returns_the_first_reply_without_paying_again(alice, model):
    scripted = model(Reply(text="I'm here."), Reply(text="A different answer."))
    thread = await start(alice)
    client_id = uuid.uuid4()

    first = await send(alice, thread.id, "hello", client_message_id=client_id)
    again = await send(alice, thread.id, "hello", client_message_id=client_id)

    assert scripted.calls == 1
    assert again.was_duplicate is True
    assert again.content == first.content


async def test_a_title_is_written_once_the_thread_has_an_exchange(alice, model):
    """`message_count == 3` exactly was the reference's gate; one crisis turn writes a
    single message, moved the count past it, and the thread was never titled."""
    model(
        Reply(text="Go on."),
        Reply(text="I see.", title='"Replaying a hard day at work."'),
    )
    from mani.db import pool

    thread = await start(alice)
    await send(alice, thread.id, "work was hard")
    turn = await send(alice, thread.id, "I keep replaying it")

    assert turn.title == "Replaying a hard day at work"
    async with pool.as_user(alice) as conn:
        assert (await threads.get(conn, thread.id, ALICE)).title == turn.title


async def test_starting_a_chat_twice_reuses_the_untouched_thread(alice):
    """Tapping "new chat" repeatedly used to leave a trail of empty threads."""
    from mani.db import pool

    async with pool.as_user(alice) as conn:
        first, created_first = await orchestrator.start_thread(conn, alice)
        second, created_second = await orchestrator.start_thread(conn, alice)

    assert second.id == first.id
    assert created_first is True and created_second is False

    async with pool.as_user(alice) as conn:
        history = await messages_db.recent_for_context(conn, first.id, ALICE)
    assert len(history) == 1, "a reused thread must not get a second greeting"


async def test_starting_a_chat_after_speaking_makes_a_new_one(alice, model):
    model(Reply(text="Go on."))
    from mani.db import pool

    first = await start(alice)
    await send(alice, first.id, "work was hard")

    async with pool.as_user(alice) as conn:
        second, created = await orchestrator.start_thread(conn, alice)

    assert second.id != first.id and created is True


async def test_buttons_are_returned_only_on_manis_newest_message(alice, model):
    """Buttons are presentation, not history. The reference kept them on old rows and
    cleaned up with an UPDATE, so a failed write left stale offers tappable."""
    model(
        Reply(
            text="Want to try something?",
            prompts=[SmartPrompt(label="Yes, let's try it", technique="abcde")],
        ),
        Reply(text="Good. What happened first?"),
    )
    from mani.db import pool
    from mani.routers.serializers import to_messages

    thread = await start(alice)
    await send(alice, thread.id, "I keep spiralling")
    await send(alice, thread.id, "Yes, let's try it")

    async with pool.as_user(alice) as conn:
        history = await messages_db.recent_for_context(conn, thread.id, ALICE)
        live = await messages_db.latest_mani_id(conn, thread.id, ALICE)

    rendered = to_messages(history, live)
    offer = next(m for m in rendered if m.content == "Want to try something?")
    newest = rendered[-1]

    assert newest.id == live and newest.content == "Good. What happened first?"
    assert offer.prompts == [], "an answered offer must not stay tappable"
    assert [m for m in rendered if m.prompts] == []
    # What the person chose stays in the record even once the offer is gone.
    assert [m.selected_prompt for m in rendered if m.selected_prompt] == [
        "Yes, let's try it"
    ]


async def test_a_failed_summary_is_logged_and_does_not_break_the_thread(
    alice, model, monkeypatch, caplog
):
    """Summarization is allowed to fail - it costs Mani some memory, not a reply. The
    swallow must leave a trace, or a silently dead summary looks like working code."""
    from mani import summarize

    model(Reply(text="Go on."))
    thread = await start(alice)
    await send(alice, thread.id, "work was hard")

    async def explode(*_args, **_kwargs):
        raise RuntimeError("provider is down")

    monkeypatch.setattr(summarize, "update", explode)
    with caplog.at_level("ERROR"):
        await summarize.update_quietly(alice, thread.id)

    assert "summarization failed" in caplog.text
    assert [m.content for m in await _history(alice, thread.id)][-1] == "Go on."


async def _history(claims: Claims, thread_id):
    from mani.db import pool

    async with pool.as_user(claims) as conn:
        return await messages_db.recent_for_context(conn, thread_id, ALICE)
