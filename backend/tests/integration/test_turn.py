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
from tests.integration.cleanup import remove_test_users

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
            call_id=uuid.uuid4(),
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
        await remove_test_users(conn, ALICE)
        await conn.execute(
            "insert into auth.users (id, email) values ($1, 'd1@t.test')", ALICE
        )
    try:
        yield claims_for(ALICE)
    finally:
        async with pool.as_admin() as conn:
            await remove_test_users(conn, ALICE)
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
    # "Tell me more" goes with the unknown technique it would have explained, and the rest go
    # because ordinary chat carries no buttons.
    assert turn.prompts == []


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
    scripted = model(
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
    # So the first stage builds on what they already said instead of asking it again.
    assert "framework_starting: yes" in scripted.last_messages[-1]["content"]


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
            at_message_count=2, phase="somatic",
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
            at_message_count=2, phase="somatic",
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


async def test_asking_about_an_offer_leaves_it_open(alice, model):
    """A question about the offer is answered and the offer made again, so it is still waiting
    for their answer - unlike carrying on past it, which is Keep chatting."""
    model(
        Reply(
            text="Want to try something?",
            prompts=[SmartPrompt(label="Try it", technique="abcde")],
            state=TechniqueState(technique="abcde", step="offering"),
        ),
        Reply(
            text="We'd look at what happened and what you told yourself about it. Would you like to try it?",
            prompts=[SmartPrompt(label="Try it", technique="abcde"),
                     SmartPrompt(label="Keep chatting", decline=True)],
            state=TechniqueState(technique="abcde", step="offering"),
        ),
    )
    from mani.db import pool

    thread = await start(alice)
    await send(alice, thread.id, "I keep spiralling")
    await send(alice, thread.id, "what would that involve?")

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


async def test_a_framework_completing_on_a_crisis_turn_is_still_retired(alice, model):
    """A crisis turn is still a turn. It used to return before the end-of-turn write, so a
    framework that finished on the same message stayed mid-flight forever - and the thread
    locks one way, so nothing would ever correct it."""
    from mani.db import pool

    thread = await start(alice)
    await _retire_abcde_on(alice, thread.id)

    turn = await send(alice, thread.id, "I am going to kill myself tonight.")
    assert turn.crisis_detected is True

    # The thread is locked, so the snapshot is read as admin rather than through a turn.
    async with pool.as_admin() as conn:
        row = await conn.fetchrow(
            "select phase, outcome from public.thread_technique_state where thread_id = $1",
            thread.id,
        )
    assert row["phase"] is None
    assert row["outcome"] == TechniqueOutcome.ACCEPTED


async def test_a_crisis_the_model_reported_links_to_the_call_that_decided_it(alice, model):
    """The safety screen answers before any call, so it has none to link. The model's own
    report costs a real generation, and admin.crisis_events is where someone reviewing a
    crisis asks which model produced it."""
    model(Reply(text="I hear you.", crisis=Crisis(reason="expressed hopelessness")))
    thread = await start(alice)
    reported = await send(alice, thread.id, "there is no point in any of it")
    assert reported.llm_call_id is not None

    screened = await start(alice)
    caught = await send(alice, screened.id, "I am going to kill myself tonight.")
    assert caught.llm_call_id is None


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


async def test_a_concern_pauses_a_running_framework_for_that_turn(alice, model):
    """The specification: avoid continuing the framework until the safety concern has been
    addressed. The model is told, gets no stage question to ask, and cannot advance or open
    a framework on this turn - the framework resumes where it stood once the concern passes."""
    scripted = model(
        Reply(
            text="Thank you for telling me. I'm with you.",
            prompts=[SmartPrompt(label="Try this", technique="thought_reframe")],
            state=TechniqueState(technique="abcde", step="consequence"),
        )
    )
    from mani.db import pool

    thread = await start(alice)
    async with pool.as_user(alice) as conn:
        await threads.set_technique_outcome(
            conn, thread.id, ALICE, "abcde", TechniqueOutcome.ACCEPTED,
            at_message_count=2, phase="belief",
        )

    turn = await send(alice, thread.id, "honestly I don’t want to be here anymore")

    sent = scripted.last_messages[-1]["content"]
    assert "safety: concern" in sent
    assert "stage_ask" not in sent and "active_framework" not in sent
    assert not any(p.technique for p in turn.prompts)

    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)
    assert ctx.technique.phase == "belief"


async def test_a_new_chat_after_a_crisis_carries_the_flag_but_not_the_lock(alice, model):
    """New chat must not become a way round the crisis path, and must not lock someone out
    either: the next conversation opens, and the model is told to stay gentle and near
    support. What was said is never carried across - only that it happened."""
    scripted = model(Reply(text="I'm glad you came back. What is on your mind?"))
    from mani.db import pool

    first = await start(alice)
    await send(alice, first.id, "I am going to kill myself")  # the screen locks this thread

    async with pool.as_user(alice) as conn:
        second, created = await threads.create_or_reuse(conn, ALICE)
    assert created and second.id != first.id

    await send(alice, second.id, "hi again")
    assert "recent_crisis: yes" in scripted.last_messages[-1]["content"]


async def test_a_finished_framework_no_longer_counts_as_running(alice, model):
    """Retired means finished. The row stays so the cooldown can be measured from it, but it
    must not keep stripping every later technique button as though the framework were live."""
    model(
        Reply(
            text="Would you like to try another way of looking at it?",
            prompts=[SmartPrompt(label="Yes, let's try", technique="thought_reframe")],
            state=TechniqueState(technique="thought_reframe", step="offering"),
        )
    )
    from mani.db import pool

    thread = await start(alice)
    async with pool.as_user(alice) as conn:
        await threads.set_technique_outcome(
            # Finished long enough ago that the cooldown has passed: what this checks is that
            # the finished row no longer blocks offers, not the cooldown itself.
            conn, thread.id, ALICE, "abcde", TechniqueOutcome.ACCEPTED,
            at_message_count=-context.COOLDOWN_AFTER_COMPLETE, phase=None,
        )

    turn = await send(alice, thread.id, "something else happened today")
    assert [p.technique for p in turn.prompts] == ["thought_reframe"]


async def test_the_router_runs_again_after_a_declined_offer(alice, model):
    scripted = model(Reply(text="What has that been like?"))
    from mani.db import pool

    thread = await start(alice)
    async with pool.as_user(alice) as conn:
        await threads.set_technique_outcome(
            conn, thread.id, ALICE, "abcde", TechniqueOutcome.DECLINED,
            at_message_count=2, phase=None,
        )
    await send(alice, thread.id, "I have stopped answering people for a week now.")
    await send(alice, thread.id, "I know what I need to do, I just cannot make myself begin.")
    await send(alice, thread.id, "I keep waiting to want to do something, but it never comes.")

    assert "framework_shortlist: behavioral_activation" in scripted.last_messages[-1]["content"]


async def test_tapping_decline_records_it_even_when_the_model_reports_no_state(alice, model):
    """After a decline there is no technique to report, so state: null is the model doing
    what the schema asks. The decline is the button's meaning, not the model's to confirm."""
    model(
        Reply(
            text="Want to try something?",
            prompts=[SmartPrompt(label="Yes, let's try it", technique="abcde"),
                     SmartPrompt(label="Not right now", decline=True)],
            state=TechniqueState(technique="abcde", step="offering"),
        ),
        Reply(text="That's fine. What would help most right now?"),
    )
    from mani.db import pool

    thread = await start(alice)
    await send(alice, thread.id, "I keep spiralling")
    await send(alice, thread.id, "Not right now")

    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)
    assert ctx.technique.outcome is TechniqueOutcome.DECLINED
    assert "active_framework" not in context.build(ctx)


async def test_a_reply_that_repairs_empty_fails_cleanly_and_stores_nothing(alice, model):
    """A reply that was only leaked script metadata is empty once cleaned. It must fail as a
    retryable turn, not reach the messages_content_not_empty constraint as a 500."""
    model(Reply(text="(Include prompts: Yes, No)"))
    from mani.errors import ServiceError

    thread = await start(alice)
    with pytest.raises(ServiceError) as raised:
        await send(alice, thread.id, "hello")
    assert raised.value.retryable
    assert [m.role for m in await _history(alice, thread.id)] == ["mani"]  # the greeting only


async def test_an_imminent_action_reaches_the_offer_on_the_first_message(alice, model):
    """The two-exchange wait exists so a framework is not offered on a first hint. STOP is
    the case where waiting is the failure: the message may be sent before a third turn."""
    scripted = model(Reply(text="Before you send it, can we pause for a moment?"))
    thread = await start(alice)
    await send(alice, thread.id, "I am furious and I am about to send a message I will regret")

    sent = scripted.last_messages[-1]["content"]
    assert "framework_shortlist: dbt_stop" in sent
    assert "offer_ask" in sent


async def test_a_new_chat_asks_how_the_person_wants_to_be_spoken_to(alice):
    thread = await start(alice)
    [first] = await _history(alice, thread.id)
    assert first.content == "Hi Al. It's MANI. How would you like me to speak with you today?"
    assert [o["label"] for o in first.prompt_options] == ["Direct", "Supportive", "Reflective"]


async def test_choosing_a_style_sets_it_and_opens_in_it_with_no_model_call(alice, model):
    """The client's cadence: greeting, style selection, then that style's opening question.
    The opener is fixed wording from the spec, so it costs nothing to say."""
    scripted = model(Reply(text="What is happening for you?"))
    from mani.db import pool

    thread = await start(alice)
    turn = await send(alice, thread.id, "Reflective")

    assert turn.content == "What's on your mind today?"
    assert turn.prompts == []
    assert scripted.calls == 0
    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)
    assert ctx.thread.conversation_style.value == "reflective"

    await send(alice, thread.id, "I keep going over an argument with my sister")
    assert "conversation_style: reflective" in scripted.last_messages[-1]["content"]


async def test_the_same_message_sent_twice_at_once_is_answered_and_paid_for_once(alice, model):
    """A mobile client retrying while the first request is still waiting on the model. Both
    used to pass the duplicate check, both paid for a generation, and the second returned a
    reply that was never stored."""
    import asyncio

    scripted = model(Reply(text="What has been the hardest part?"))
    real = orchestrator.client.complete

    async def slow(*args, **kwargs):
        await asyncio.sleep(0.3)  # long enough that the second request arrives mid-call
        return await real(*args, **kwargs)

    orchestrator.client.complete = slow
    try:
        thread = await start(alice)
        client_message_id = uuid.uuid4()
        first, second = await asyncio.gather(
            send(alice, thread.id, "work has been hard lately", client_message_id=client_message_id),
            send(alice, thread.id, "work has been hard lately", client_message_id=client_message_id),
        )
    finally:
        orchestrator.client.complete = real

    assert scripted.calls == 1
    assert first.message_id == second.message_id
    assert first.content == second.content


async def test_a_message_id_reused_in_another_chat_is_refused_not_answered(alice, model):
    """The key is per person, so a reuse in a second chat used to return the first chat's
    reply - a message from another conversation, and nothing written where it was sent."""
    from mani.errors import ErrorCategory, ServiceError

    model(Reply(text="What has been the hardest part?"))
    first_chat = await start(alice)
    client_message_id = uuid.uuid4()
    await send(alice, first_chat.id, "work has been hard lately", client_message_id=client_message_id)

    from mani.db import pool

    async with pool.as_user(alice) as conn:
        second_chat, _ = await threads.create_or_reuse(conn, ALICE)
    with pytest.raises(ServiceError) as refused:
        await send(alice, second_chat.id, "a different chat", client_message_id=client_message_id)
    assert refused.value.category is ErrorCategory.CONFLICT


async def test_two_summaries_started_together_pay_for_one(alice, monkeypatch):
    """A summary runs after the reply, in the background. A second message arriving before it
    has committed schedules another over the same messages - two generations, one kept."""
    import asyncio

    from mani import summarize
    from mani.llm.schema import Extraction

    calls = 0

    async def slow_summary(messages, schema, **kwargs):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.3)
        return client.Call(value=Extraction(summary="The user talked about work."),
                           model="test/model", usage=llm_calls.Usage(), latency_ms=1,
                           call_id=uuid.uuid4())

    monkeypatch.setattr(orchestrator.client, "complete",
                        ScriptedModel(Reply(text="Go on.")))
    thread = await start(alice)
    await send(alice, thread.id, "work was hard")
    monkeypatch.setattr(summarize.client, "complete", slow_summary)

    await asyncio.gather(
        summarize.update_quietly(alice, thread.id), summarize.update_quietly(alice, thread.id)
    )
    assert calls == 1


async def test_past_the_daily_limit_a_turn_is_refused_before_anything_is_paid(
    alice, model, monkeypatch
):
    from mani.config import get_settings
    from mani.errors import ErrorCategory, ServiceError

    scripted = model(Reply(text="What has been the hardest part?"))
    monkeypatch.setattr(get_settings(), "daily_message_limit", 1)
    thread = await start(alice)
    await send(alice, thread.id, "work has been hard lately")

    with pytest.raises(ServiceError) as refused:
        await send(alice, thread.id, "and it's getting worse")
    assert refused.value.category is ErrorCategory.RATE_LIMITED
    assert scripted.calls == 1


async def test_a_crisis_is_still_answered_past_the_daily_limit(alice, model, monkeypatch):
    """The limit caps what can be spent, never whether someone in danger gets a reply: the
    safety screen runs first and answers with no model call at all."""
    from mani.config import get_settings

    model(Reply(text="What has been the hardest part?"))
    monkeypatch.setattr(get_settings(), "daily_message_limit", 1)
    thread = await start(alice)
    await send(alice, thread.id, "work has been hard lately")

    turn = await send(alice, thread.id, "I am going to kill myself")
    assert turn.crisis_detected


async def test_finishing_a_framework_always_offers_chat_more_and_the_library(alice, model):
    """The client's cadence ends every framework on the same two choices. Left to the model
    they came back mislabeled ("Something else"), or not at all, on the reply that ends it."""
    model(Reply(text="Your shoulders feel looser. Does that feel right? What would you like next?",
                prompts=[SmartPrompt(label="Something else")]))
    from mani.db import pool

    thread = await start(alice)
    async with pool.as_user(alice) as conn:
        await threads.set_technique_outcome(
            conn, thread.id, ALICE, "abcde", TechniqueOutcome.ACCEPTED,
            at_message_count=2, phase="somatic",
        )

    turn = await send(alice, thread.id, "my shoulders feel a bit looser")
    assert [(p.label, p.library) for p in turn.prompts] == [
        ("Chat More", None), ("Go to Library", "home"),
    ]


async def test_the_body_check_in_waits_for_their_answer_before_the_two_choices(alice, model):
    """The client's order: ask about the body, mirror what they notice, then Chat More / Go to
    Library. Observed: the model put both on the check-in question, and they came again on the
    reply after it."""
    model(Reply(text="What are you noticing in your body now, compared with when we started?",
                prompts=[SmartPrompt(label="Chat More"),
                         SmartPrompt(label="Go to Library", library="home")],
                state=TechniqueState(technique="abcde", step="somatic")))
    from mani.db import pool

    thread = await start(alice)
    async with pool.as_user(alice) as conn:
        await threads.set_technique_outcome(
            conn, thread.id, ALICE, "abcde", TechniqueOutcome.ACCEPTED,
            at_message_count=2, phase="closing",
        )

    turn = await send(alice, thread.id, "yes, that fits what happened")
    assert turn.prompts == []


async def test_a_body_they_already_described_ends_on_the_two_choices_once(alice, model):
    """Someone who answers the closing question with their body ("a bit lighter in my chest")
    has done the check-in, so that reply mirrors it and asks what next - and carries the two
    choices, which then do not come back on the reply after."""
    model(
        Reply(text="Your chest feels lighter. Does that feel right? What would you like to do next?",
              state=TechniqueState(technique="abcde", step="somatic")),
        Reply(text="It's still on your mind. What feels most important about this now?"),
    )
    from mani.db import pool

    thread = await start(alice)
    async with pool.as_user(alice) as conn:
        await threads.set_technique_outcome(
            conn, thread.id, ALICE, "abcde", TechniqueOutcome.ACCEPTED,
            at_message_count=2, phase="closing",
        )

    checked_in = await send(alice, thread.id, "a bit lighter in my chest")
    assert [(p.label, p.library) for p in checked_in.prompts] == [
        ("Chat More", None), ("Go to Library", "home"),
    ]
    after = await send(alice, thread.id, "I still keep thinking about that meeting")
    assert after.prompts == []


async def test_a_choice_already_made_is_not_offered_again(alice, model):
    """If they have already said Chat More, the ending reply just carries on talking."""
    model(Reply(text="We can keep talking. What's on your mind now?"))
    from mani.db import pool

    thread = await start(alice)
    async with pool.as_user(alice) as conn:
        await threads.set_technique_outcome(
            conn, thread.id, ALICE, "abcde", TechniqueOutcome.ACCEPTED,
            at_message_count=2, phase="somatic",
        )

    turn = await send(alice, thread.id, "Chat More")
    assert turn.prompts == []


async def test_carrying_on_past_an_offer_is_keep_chatting(alice, model):
    """muhammad, 2026-09-24: someone who types on without answering the offer has chosen to keep
    chatting. Observed: "Would you like to try it?" came back on the very next reply, and the
    one after."""
    offer = Reply(
        text="I have a sequence of questions that could help. Would you like to try it?",
        prompts=[SmartPrompt(label="Try it", technique="abcde"),
                 SmartPrompt(label="Tell me about this"),
                 SmartPrompt(label="Keep chatting", decline=True)],
        state=TechniqueState(technique="abcde", step="offering"),
    )
    # What the model actually does: reports no answer either way, and makes the offer again.
    offered_again = offer.model_copy(update={
        "text": "You pick the phone back up. I have a sequence of questions that could help. "
                "Would you like to try it?",
    })
    model(offer, offered_again)
    from mani.db import pool

    thread = await start(alice)
    await send(alice, thread.id, "my manager criticized me in front of everyone")
    turn = await send(alice, thread.id, "every time I try to start I pick the phone back up")

    assert turn.prompts == []
    assert turn.content == "You pick the phone back up."
    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)
    assert ctx.technique.outcome is TechniqueOutcome.DECLINED


async def test_an_offer_they_typed_past_is_flagged_then_closed(alice, model):
    """The model is told, on the turn itself, that its offer is waiting and they typed instead;
    a reply that neither re-offers nor reports an answer has let it go, and so does the offer."""
    offer = Reply(
        text="I have a sequence of questions that could help. Would you like to try it?",
        prompts=[SmartPrompt(label="Try it", technique="abcde"),
                 SmartPrompt(label="Tell me about this"),
                 SmartPrompt(label="Keep chatting", decline=True)],
        state=TechniqueState(technique="abcde", step="offering"),
    )
    scripted = model(offer, Reply(text="You pick the phone back up. What happens right before?"))
    from mani.db import pool

    thread = await start(alice)
    await send(alice, thread.id, "my manager criticized me in front of everyone")
    await send(alice, thread.id, "every time I try to start I pick the phone back up")

    sent = scripted.last_messages[-1]["content"]
    assert "offer_waiting: yes" in sent
    # The offering stage's question is the offer itself; handing it over again is asking for it.
    assert not any(line.startswith("stage_ask:") for line in sent.splitlines())
    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)
    assert ctx.technique.outcome is TechniqueOutcome.DECLINED


async def test_asking_for_a_declined_framework_themselves_starts_it(alice, model):
    """Someone who carried on past an offer and then asks for that help themselves has said
    yes, even before the cooldown would let Mani offer it again. Observed: Mani began the
    questions in its own words while nothing was running."""
    offer = Reply(
        text="I have a sequence of questions that could help. Would you like to try it?",
        prompts=[SmartPrompt(label="Try it", technique="abcde"),
                 SmartPrompt(label="Tell me about this"),
                 SmartPrompt(label="Keep chatting", decline=True)],
        state=TechniqueState(technique="abcde", step="offering"),
    )
    model(
        offer,
        Reply(text="You keep replaying it. Which part stays with you?"),
        Reply(text="Okay. We'll take it one step at a time together. What happened?",
              state=TechniqueState(technique="abcde", step="activate", accepted=True)),
    )
    from mani.db import pool

    thread = await start(alice)
    await send(alice, thread.id, "my manager criticized me in front of everyone")
    await send(alice, thread.id, "I keep replaying it")
    await send(alice, thread.id, "actually I'd like some help looking at it")

    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)
    assert (ctx.technique.framework_id, ctx.technique.outcome, ctx.technique.phase) == (
        "abcde", TechniqueOutcome.ACCEPTED, "activate",
    )


async def test_a_declined_framework_can_be_offered_again_after_a_few_replies(alice, model):
    """muhammad, 2026-09-24: after "I want to keep talking", Mani checks again after a few
    more messages - the same framework if it still fits best."""
    offer = Reply(
        text="We could look at what happened and what you told yourself about it. Would you like to try?",
        prompts=[SmartPrompt(label="Yes, let's try it", technique="abcde"),
                 SmartPrompt(label="Tell me more"),
                 SmartPrompt(label="I want to keep talking", decline=True)],
        state=TechniqueState(technique="abcde", step="offering"),
    )
    chat = Reply(text="What else has been on your mind about it?")
    model(offer, chat, chat, chat, chat, offer)
    thread = await start(alice)
    await send(alice, thread.id, "my manager criticized me in front of everyone")
    await send(alice, thread.id, "I want to keep talking")
    for text in ("it keeps coming back", "I replay it at night", "I can't let it go"):
        await send(alice, thread.id, text)

    again = await send(alice, thread.id, "maybe I do want to look at it")
    assert [p.technique for p in again.prompts if p.technique] == ["abcde"]
