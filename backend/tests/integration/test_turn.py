# ABOUTME: Runs whole turns against a live database with a scripted model in place.
# ABOUTME: The model is faked; every write, policy and transition under test is real.

import asyncio
import uuid

import asyncpg
import pytest

from mani.auth.jwt import Claims
from mani.chat import context, crisis, orchestrator
from mani.config import get_settings
from mani.db import llm_calls, messages as messages_db, profiles, threads
from mani.llm import client
from mani.chat.repairs import PERMISSION_QUESTION
from mani.llm.schema import Check, Crisis, NextStage, Offer, Reply, StageUpdate, Style, UnderstandingUpdate
from mani.models.rows import TechniqueOutcome, TechniqueState as TechniqueRow
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
        self.schemas: list[type] = []
        self.kwargs: dict = {}

    async def __call__(self, messages, schema, **kwargs):
        self.calls += 1
        self.last_messages = messages
        self.schemas.append(schema)
        self.kwargs = kwargs
        reply = self._replies[min(self.calls - 1, len(self._replies) - 1)]
        return client.Call(
            # Parsed in the shape this turn sent, as the real call is: a field the moment does not
            # carry is dropped, however the script filled it.
            value=schema.model_validate(reply.model_dump()),
            model="test/model",
            usage=llm_calls.Usage(input_tokens=100, output_tokens=20),
            latency_ms=1,
            call_id=uuid.uuid4(),
        )


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


# The three steps before a check, all found (spec 0006).
FOUND = {
    "issue": "your coworkers miss deadlines",
    "core_issue": "the work always lands on you",
    "underlying_feeling": "you may feel worn down by it",
}


async def past_the_opening(thread):
    """The rounds of conversation the client wants before anything is offered, already had: the
    problem, its core issue and the feeling underneath found, ending on Mani's check of its
    understanding, so the next message answers it (spec 0006). For tests about what happens to an
    offer, not about when one may come."""
    from mani.db import pool

    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.threads set message_count = message_count + 8, "
            "check_at_message_count = message_count + 8, understanding = $2::jsonb where id = $1",
            thread.id, FOUND,
        )
    return thread


async def send(claims: Claims, thread_id, content, **kwargs):
    from mani.db import pool

    async with pool.as_user(claims) as conn:
        return await orchestrator.send(conn, claims, thread_id, content, **kwargs)


async def set_technique_outcome(
    conn, thread_id, user_id, framework_id: str, outcome: TechniqueOutcome,
    at_message_count: int, phase: str | None = None, stages_known: dict | None = None,
) -> None:
    """Puts the thread straight into a framework state a test would otherwise walk to."""
    await threads.apply(
        conn, thread_id, user_id,
        threads.ThreadUpdates(technique=TechniqueRow(
            thread_id=thread_id, framework_id=framework_id, outcome=outcome,
            phase=phase, at_message_count=at_message_count,
        ), stages_known=stages_known),
    )


async def test_a_turn_costs_exactly_one_provider_call(alice, model):
    scripted = model(
        Reply(
            # Everything the checks look at is wrong at once: leaked script text, a stage answer
            # with no stage running, and an offer for a set that does not exist.
            text="Here you go. What happened?\n\n**Mani:** breathe\n\n(Include prompts: yes/no)",
            heading_toward="made_up_technique",
            offer=Offer(going_through="a hard day", lead_line="That sounds hard."),
            stage_answer="answered",
            style=Style(shape="mirror and ask"),
        )
    )
    thread = await start(alice)
    turn = await send(alice, thread.id, "I had a hard day")

    assert scripted.calls == 1
    assert "**Mani:**" not in turn.content
    # An offer for an unknown set is not made, and ordinary chat carries no buttons.
    assert turn.prompts == []


# Lolly's first message in the Direct test that reached ABCDE at once (2026-10-12, R1).
RESENTFUL = (
    "I have a coworker who is always asking me for help, and I usually say yes. But whenever I "
    "need something, they're never available. I'm starting to feel resentful, and I don't like "
    "feeling this way."
)


def _offer(technique: str = "abcde") -> Reply:
    """An offer as the model makes one on a yes to its check: the slots of the client's template, for
    the set it heads toward. Its text is what goes when the offer cannot be made."""
    return Reply(
        text="What happened at work after that?",
        check_answer="yes",
        heading_toward=technique,
        offer=Offer(lead_line="That sounds like a lot to carry.", going_through="what happened at work"),
    )


def _check() -> Reply:
    """Mani's check of its understanding, each part its own sentence; its free text opens with their last
    answer, as the model's did live, and is never sent (spec 0006)."""
    return Reply(
        text="You may feel worn down. Your coworkers miss deadlines. Do I have that right?",
        check=Check(
            problem="Your coworkers keep missing deadlines", core_issue="The work always ends up landing on you.",
            underlying_feeling="You may feel worn down by it.",
            comes_down_to="It seems to come down to carrying what others drop.", question="Do I have that right",
        ),
        understanding_update=UnderstandingUpdate(underlying_feeling="you may feel worn down by it"),
    )


# _check() as sent: the problem, the core issue, the feeling underneath and what it comes down to, then the question.
CHECK_SENT = (
    "Your coworkers keep missing deadlines. The work always ends up landing on you. You may feel worn "
    "down by it. It seems to come down to carrying what others drop.\n\nDo I have that right?"
)


async def answering_a_check(thread):
    """Mani's last reply was its check, so the next message answers it (spec 0006)."""
    from mani.db import pool

    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.threads set check_at_message_count = message_count where id = $1", thread.id
        )
    return thread


async def _thread_row(alice, thread_id):
    from mani.db import pool

    async with pool.as_user(alice) as conn:
        return (await threads.load_turn_context(conn, thread_id, ALICE)).thread


# The client's supportive offer for ABCDE (abcde.md) with _offer's slots in it.
SUPPORTIVE_OFFER = (
    "That sounds like a lot to carry.\nThere's a framework called ABCDE that can help you understand "
    "the thoughts behind what happened at work, see whether those thoughts are really true, and find "
    "a more helpful way to think about what's happening.\n\nWould you like to try it?"
)


async def _in_style(thread, style):
    """The style tap and its opener, which the real greeting flow adds before their first message."""
    from mani.db import pool

    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.threads set conversation_style = $2, message_count = message_count + 2 "
            "where id = $1",
            thread.id, style.value,
        )
    return thread


async def test_before_the_window_opens_the_model_is_given_no_way_to_name_a_technique(alice, model):
    """R1: no framework after the first message, however well it seems to fit. The shape of the
    reply has no offer field, so the question the reply ends on is never traded for one."""
    from mani.models.rows import SupportStyle

    scripted = model(Reply(text="What has that been like for you this week?"))
    thread = await _in_style(await start(alice), SupportStyle.DIRECTIVE)
    turn = await send(alice, thread.id, RESENTFUL)

    assert scripted.calls == 1
    assert "offer" not in scripted.schemas[0].model_fields
    assert turn.prompts == []
    assert turn.content == "What has that been like for you this week?"


async def test_an_offer_still_made_on_their_first_message_cannot_start_a_framework(alice, model):
    """The model offered although the shape it was given has no way to: no button reaches them,
    so nothing is open for a yes to start."""
    from mani.db import pool
    from mani.models.rows import SupportStyle

    model(_offer("abcde"))
    thread = await _in_style(await start(alice), SupportStyle.DIRECTIVE)
    turn = await send(alice, thread.id, RESENTFUL)

    assert [p for p in turn.prompts if p.technique] == []
    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)
    assert ctx.technique is None


async def test_the_problem_its_core_issue_and_the_feeling_each_take_an_exchange_then_the_check_and_offer(
    alice, model,
):
    """Spec 0006, AC-2 to AC-4, AC-17, AC-18, muhammad's run of 2026-10-13. The model reports
    everything it can see from the first message; code takes one step per exchange, so the check field
    first appears on their third message, the check is stored once their own words give the feeling, even an I don't know, and a
    clear yes at their fourth makes that reply the client's offer. One call each."""
    from mani.models.rows import SupportStyle

    everything = UnderstandingUpdate(
        issue="your coworkers miss deadlines", core_issue="the work always lands on you",
        underlying_feeling="you may feel worn down by it",
    )
    scripted = model(
        Reply(text="That sounds draining. Who does it fall on when they miss them?", understanding_update=everything),
        Reply(text="That's a lot to carry. How does it sit with you underneath?", understanding_update=everything),
        _check(),
        _offer("abcde"),
    )
    thread = await _in_style(await start(alice), SupportStyle.SUPPORTIVE)
    await send(alice, thread.id, "i'm frustrated at work")
    first = await _thread_row(alice, thread.id)
    await send(alice, thread.id, "my coworkers keep missing deadlines and i end up doing their work")
    checked = await send(alice, thread.id, "i don't know, it just wears me down")
    assert (await _thread_row(alice, thread.id)).check_at_message_count is not None
    turn = await send(alice, thread.id, "yes, that's it")

    assert set(first.understanding) == {"issue"}, "the opening message fills the problem only"
    assert scripted.calls == 4
    assert ["check" in shape.model_fields for shape in scripted.schemas] == [False, False, True, False]
    assert ["offer" in shape.model_fields for shape in scripted.schemas] == [False, False, False, True]
    # The check's parts in the client's order, whatever order the model's own text took.
    assert checked.content == CHECK_SENT
    # The client's template word for word with the model's slots in it, never the model's text.
    assert turn.content == SUPPORTIVE_OFFER
    assert [p.label for p in turn.prompts] == ["Try it", "Tell me more", "Keep chatting"]
    # Their own words stay as stored, and what the check came down to is kept beside them.
    assert (await _thread_row(alice, thread.id)).understanding == {
        "issue": "your coworkers miss deadlines", "core_issue": "the work always lands on you",
        "underlying_feeling": "you may feel worn down by it",
        "comes_down_to": "It seems to come down to carrying what others drop.",
    }


async def test_a_check_whose_feeling_did_not_come_from_them_opens_nothing(alice, model):
    """Spec 0006, AC-18: on the turn that should ask about the feeling, a check carrying a feeling they never
    gave is not stored, so their yes to it brings no offer; it is counted."""
    from mani.db import pool

    model(_check().model_copy(update={"understanding_update": None}))
    thread = await start(alice)
    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.threads set message_count = 11, understanding = $2::jsonb where id = $1",
            thread.id, {k: FOUND[k] for k in ("issue", "core_issue")},
        )
    turn = await send(alice, thread.id, "it happens every week")

    assert (await _thread_row(alice, thread.id)).check_at_message_count is None
    assert "check before the three steps" in turn.checks


@pytest.mark.parametrize("style", ["directive", "supportive", "reflective"])
async def test_an_offer_on_a_yes_to_the_check_is_plain_and_costs_one_call(alice, model, style):
    """The same in every style."""
    from mani.models.rows import SupportStyle

    scripted = model(_offer("abcde"))
    thread = await past_the_opening(await _in_style(await start(alice), SupportStyle(style)))
    turn = await send(alice, thread.id, "yes, that's right")

    assert scripted.calls == 1
    assert [p.label for p in turn.prompts] == ["Try it", "Tell me more", "Keep chatting"]
    assert [p.technique for p in turn.prompts if p.technique] == ["abcde"]
    assert turn.checks == []


@pytest.mark.parametrize("answer", ["no", None])
async def test_anything_but_a_clear_yes_keeps_chatting_and_the_next_check_waits(alice, model, answer):
    """Spec 0006, AC-5: a no, a yes with an addition, or another topic gives no offer, even when the
    model fills one; the check is used, and the next waits three replies."""
    scripted = model(
        _offer().model_copy(update={"check_answer": answer, "text": "What part did I miss?"}),
        *[Reply(text=f"What happened {n}?") for n in range(4)],
    )
    thread = await past_the_opening(await start(alice))
    turn = await send(alice, thread.id, "yes, but it's also my manager")
    for n in range(3):
        await send(alice, thread.id, f"more {n}")

    assert turn.content == "What part did I miss?"
    assert turn.prompts == []
    assert "offer unusable: no yes to the check" in turn.checks
    assert ["check" in shape.model_fields for shape in scripted.schemas] == [False, False, False, True]


async def test_no_check_by_their_fifth_message_is_logged_and_never_asked_for(alice, model):
    """Spec 0006, AC-11: counted on that message only, and nothing about it reaches [ctx]."""
    from mani.models.rows import SupportStyle

    scripted = model(*[Reply(text=f"What happened then, {n}?") for n in range(6)])
    thread = await _in_style(await start(alice), SupportStyle.DIRECTIVE)
    turns = [await send(alice, thread.id, f"message {n}") for n in range(1, 7)]

    assert [("no check by message 5" in t.checks) for t in turns] == [False] * 4 + [True, False]
    assert "no check" not in scripted.last_messages[-1]["content"]


async def test_a_concern_on_the_answer_to_a_check_renders_no_offer_and_lets_the_check_lapse(alice, model):
    """Spec 0006, AC-7: nothing merged and nothing offered; the turn after is ordinary chat."""
    from mani.db import pool

    scripted = model(
        _offer().model_copy(update={
            "crisis": Crisis(reason="hopeless"), "text": "I'm here with you.",
            "understanding_update": UnderstandingUpdate(issue="should not be stored"),
        }),
        Reply(text="What is happening for you right now?"),
    )
    thread = await past_the_opening(await start(alice))
    turn = await send(alice, thread.id, "yes")
    await send(alice, thread.id, "I don't know")

    assert (turn.content, turn.prompts) == ("I'm here with you.", [])
    assert (await _thread_row(alice, thread.id)).understanding == FOUND
    assert "check_answer" not in scripted.schemas[-1].model_fields
    async with pool.as_user(alice) as conn:
        assert (await threads.load_turn_context(conn, thread.id, ALICE)).technique is None


async def test_asking_for_a_declined_set_on_the_answer_to_a_check_starts_it_and_stores_no_check(alice, model):
    """Spec 0006, AC-3, AC-6: a typed request for the set they declined starts it on any turn."""
    from mani.db import pool

    model(Reply(text="Let's begin.", offer_answer="yes", check=_check().check))
    thread = await past_the_opening(await start(alice))
    async with pool.as_user(alice) as conn:
        await set_technique_outcome(
            conn, thread.id, ALICE, "abcde", TechniqueOutcome.DECLINED, at_message_count=0,
        )
    before = (await _thread_row(alice, thread.id)).check_at_message_count
    await send(alice, thread.id, "actually, can we do that ABCDE thing?")

    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)
    assert (ctx.technique.outcome, ctx.thread.check_at_message_count) == (TechniqueOutcome.ACCEPTED, before)


async def test_typing_past_an_offer_is_keep_chatting_and_the_reply_cannot_offer_again(alice, model):
    """Typing past an offer is Keep chatting, so the shape of the next reply has no offer field and
    it keeps its question."""
    scripted = model(
        _offer("abcde"),
        Reply(text="Which of those two would cost you less if it went wrong?"),
    )
    thread = await start(alice)
    await past_the_opening(thread)
    await send(alice, thread.id, "i have an exam tomorrow and i do not know where to start")
    turn = await send(alice, thread.id, "i could study everything or pick topics")

    assert scripted.calls == 2
    assert "offer" not in scripted.schemas[-1].model_fields
    assert turn.content == "Which of those two would cost you less if it went wrong?"
    assert turn.prompts == []


async def test_a_comforting_reply_with_no_question_goes_out_as_written_and_is_logged(alice, model):
    """No second call for it: R5 asks for fewer questions, and the miss is counted so how often it
    happens is known."""
    scripted = model(Reply(text="It is okay to feel that way. I am here with you."))
    thread = await start(alice)
    turn = await send(alice, thread.id, "i felt small when she questioned me in front of everyone")

    assert scripted.calls == 1
    assert turn.content == "It is okay to feel that way. I am here with you."
    assert turn.checks == ["asks no question"]


async def test_someone_who_asks_only_to_be_heard_is_not_forced_to_answer_a_question(alice, model):
    """The model reads that someone only wants to be listened to and picks a shape that asks nothing;
    no phrase list in code decides it."""
    scripted = model(Reply(
        text="That sounds like it has been hard for a long time.",
        style=Style(shape="mirror and hold"),
    ))
    thread = await start(alice)
    turn = await send(alice, thread.id, "please don't ask me anything, i just need to get it out")

    assert scripted.calls == 1
    assert "?" not in turn.content


async def test_a_reply_that_asks_nothing_and_chose_to_ask_something_is_logged(alice, model):
    scripted = model(
        Reply(text="That sounds like it has been hard.", style=Style(shape="mirror and ask")),
    )
    thread = await start(alice)
    turn = await send(alice, thread.id, "work has been a lot lately")

    assert scripted.calls == 1
    assert turn.checks == ["asks no question"]


ASKED_INLINE = "Your coworkers keep missing deadlines and the work lands on you every time. Is that what started this?"


async def test_manis_own_reply_goes_out_with_its_question_on_its_own_line(alice, model):
    """The client's way of communication document (R13) lays a reply out this way."""
    model(Reply(text=ASKED_INLINE))
    thread = await start(alice)
    turn = await send(alice, thread.id, "my coworkers never deliver")

    assert turn.content == ASKED_INLINE.replace(" Is that", "\n\nIs that")


async def test_a_stage_reply_from_a_set_asked_for_again_stays_one_paragraph(alice, model):
    """The client's ABCDE document writes each stage as one paragraph, including when Mani's own text
    for the stage comes from a turn that started the framework."""
    from mani.db import pool

    model(Reply(
        text=ASKED_INLINE, offer_answer="yes",
        next_stage=NextStage(status="known", said="your coworkers miss deadlines"),
    ))
    thread = await past_the_opening(await start(alice))
    async with pool.as_user(alice) as conn:
        await set_technique_outcome(
            conn, thread.id, ALICE, "abcde", TechniqueOutcome.DECLINED, at_message_count=0,
        )
    turn = await send(alice, thread.id, "actually, can we do that ABCDE thing?")

    assert "Is that what started this?" in turn.content
    assert "\n" not in turn.content


async def test_a_concern_reported_by_the_model_goes_out_as_written(alice, model):
    model(Reply(text=ASKED_INLINE, crisis=Crisis(reason="hopelessness")))
    thread = await start(alice)
    turn = await send(alice, thread.id, "nothing matters anyway")

    assert turn.content == ASKED_INLINE


async def test_the_turn_is_stored_and_the_thread_state_follows_it(alice, model):
    model(_offer().model_copy(update={"style": Style(shape="warmth lead")}))
    from mani.db import pool

    thread = await past_the_opening(await start(alice))
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
        _offer(),
        Reply(text="Good. What happened first?"),
    )
    from mani.db import pool

    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "I keep spiralling")
    turn = await send(alice, thread.id, "Try it")

    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)

    assert ctx.technique.outcome is TechniqueOutcome.ACCEPTED
    assert ctx.technique.phase == "activate"
    assert turn.content.startswith("A is for Activating Event. ")
    # So the store is seeded from what they already said instead of asking it again.
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
        await set_technique_outcome(
            conn, thread.id, ALICE, "abcde", TechniqueOutcome.ACCEPTED,
            at_message_count=2, phase="somatic_closing",
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
    assert not context.may_check(ctx)
    assert [m.role for m in (await _history(alice, thread.id))][-2:] == ["user", "mani"]


async def _retire_abcde_on(alice, thread_id) -> None:
    """Land a thread on ABCDE's final phase, so the next turn is the completing one."""
    from mani.db import pool

    async with pool.as_user(alice) as conn:
        await set_technique_outcome(
            conn, thread_id, ALICE, "abcde", TechniqueOutcome.ACCEPTED,
            at_message_count=2, phase="somatic_closing",
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


@pytest.fixture
async def library_exercise(alice):
    """An ordinary library exercise, linked to no framework."""
    from mani.db import pool

    async with pool.as_admin() as conn:
        exercise_id = await conn.fetchval(
            "insert into admin.exercises (title, type, category, audio_path) "
            "values ('Unwinding', 'Breathing', 'Burnout', 'test-unwinding.mp3') returning id"
        )
    try:
        yield exercise_id
    finally:
        async with pool.as_admin() as conn:
            await conn.execute("delete from admin.exercises where id = $1", exercise_id)


@pytest.fixture
async def empty_catalog(alice):
    """Hide the seeded catalog for one test, and put back exactly what was hidden."""
    from mani.db import pool

    async with pool.as_admin() as conn:
        hidden = await conn.fetch(
            "update admin.exercises set is_active = false where is_active returning id"
        )
    try:
        yield
    finally:
        async with pool.as_admin() as conn:
            await conn.execute(
                "update admin.exercises set is_active = true where id = any($1::uuid[])",
                [r["id"] for r in hidden],
            )


async def test_asking_about_an_offer_leaves_it_open(alice, model):
    """A question about the offer is answered with the client's explanation and the offer made
    again, so it is still waiting for their answer - unlike carrying on past it, which is Keep
    chatting. The model's own text is not sent."""
    model(_offer(), Reply(text="We'd look at what happened.", offer_answer="asked"))
    from mani.db import pool

    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "I keep spiralling")
    told = await send(alice, thread.id, "what would that involve?")

    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)

    assert ctx.technique.outcome is TechniqueOutcome.OFFERED
    framework = (await orchestrator.cache.load()).registry.get("abcde")
    assert told.content == framework.stages["offering"]["explain"]["supportive"] + "\n\nWould you like to try it?"
    assert [(p.label, p.technique) for p in told.prompts] == [("Try it", "abcde"), ("Keep chatting", None)]


async def test_a_model_reported_crisis_does_not_lock_the_thread(alice, model):
    """The model's own crisis judgment no longer locks: a small model over-fires it on
    ordinary distress, pain, or injury. Only the deterministic screen locks. A model report
    is a non-locking concern - the reply stays in the model's words, no event is recorded,
    and the conversation the person came for is not cut off."""
    model(
        Reply(text="I hear you, and I'm right here with you.", crisis=Crisis(reason="hopelessness")),
        Reply(text="What has today been like?"),
    )
    from mani.db import pool

    thread = await start(alice)
    turn = await send(alice, thread.id, "there is no point in me being here")

    assert turn.crisis_detected is False
    assert turn.content != crisis.CRISIS_REPLY
    assert turn.content.strip()

    async with pool.as_admin() as conn:
        event = await conn.fetchrow(
            "select reason from admin.crisis_events where thread_id = $1", thread.id
        )
    assert event is None

    # The thread is not locked, so a following turn is answered normally.
    again = await send(alice, thread.id, "I guess I am still here")
    assert again.crisis_detected is False
    assert again.content.strip()


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


async def test_a_clear_wish_to_die_locks_before_any_call(alice, model):
    """"I want to die" is a clear wish to die, so the deterministic screen locks it before the
    model is ever asked - the sole locking authority, not the model. The scripted model has no
    reply queued, so a call here would raise rather than just cost extra."""
    from mani.db import pool

    scripted = model()
    thread = await start(alice)
    turn = await send(alice, thread.id, "I want to die")

    assert scripted.calls == 0
    assert turn.crisis_detected is True
    assert turn.llm_call_id is None

    async with pool.as_admin() as conn:
        event = await conn.fetchrow(
            "select reason from admin.crisis_events where thread_id = $1", thread.id
        )
    assert event["reason"] == "safety screen: suicide"


async def test_a_crisis_thread_refuses_another_turn(alice, model):
    # A deterministic crisis locks the thread; the model is never called for the first turn.
    model()
    thread = await start(alice)
    await send(alice, thread.id, "I want to die")

    from mani.errors import ServiceError

    with pytest.raises(ServiceError):
        await send(alice, thread.id, "are you there")


async def test_a_retried_send_returns_the_first_reply_without_paying_again(alice, model):
    scripted = model(Reply(text="I'm here. What happened?"), Reply(text="A different answer."))
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
        history = (await messages_db.for_context(conn, first.id, ALICE, budget_chars=get_settings().context_budget_chars)).messages
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
    model(_offer(), Reply(text="Good. What happened first?"))
    from mani.db import pool
    from mani.routers.serializers import to_messages

    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "I keep spiralling")
    await send(alice, thread.id, "Try it")

    async with pool.as_user(alice) as conn:
        history = (await messages_db.for_context(conn, thread.id, ALICE, budget_chars=get_settings().context_budget_chars)).messages
        live = await messages_db.latest_mani_id(conn, thread.id, ALICE)

    rendered = to_messages(history, live)
    # The offer's words are composed by the backend, ending on the client's permission question.
    offer = next(m for m in rendered if PERMISSION_QUESTION in m.content)
    newest = rendered[-1]

    assert newest.id == live and newest.content == _asks("activate")
    assert offer.prompts == [], "an answered offer must not stay tappable"
    assert [m for m in rendered if m.prompts] == []
    # What the person chose stays in the record even once the offer is gone.
    assert [m.selected_prompt for m in rendered if m.selected_prompt] == ["Try it"]


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
        return (await messages_db.for_context(conn, thread_id, ALICE, budget_chars=get_settings().context_budget_chars)).messages


async def test_a_concern_pauses_a_running_framework_for_that_turn(alice, model):
    """The specification: avoid continuing the framework until the safety concern has been
    addressed. The model is told, gets no stage question to ask, and cannot advance or open
    a framework on this turn - the framework resumes where it stood once the concern passes."""
    scripted = model(
        Reply(text="Thank you for telling me. I'm with you.")
    )
    from mani.db import pool

    thread = await start(alice)
    async with pool.as_user(alice) as conn:
        await set_technique_outcome(
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


async def test_the_framework_just_finished_is_offered_again_on_a_new_confirmed_check(alice, model):
    """Spec 0006, AC-6: once the cooldown after finishing has passed, a yes to a new check offers it
    again. Only ABCDE is active, and refusing the set just done would leave nothing to offer, ever."""
    scripted = model(_offer())
    from mani.db import pool

    thread = await start(alice)
    async with pool.as_user(alice) as conn:
        await set_technique_outcome(
            conn, thread.id, ALICE, "abcde", TechniqueOutcome.ACCEPTED,
            at_message_count=-context.COOLDOWN_AFTER_COMPLETE, phase=None,
        )
    await answering_a_check(thread)

    turn = await send(alice, thread.id, "yes, that's what it is")
    assert [p.technique for p in turn.prompts if p.technique] == ["abcde"]
    assert scripted.calls == 1


async def test_tapping_decline_records_it_even_when_the_model_reports_no_state(alice, model):
    """After a decline there is no technique to report, so state: null is the model doing
    what the schema asks. The decline is the button's meaning, not the model's to confirm."""
    model(_offer(), Reply(text="That's fine. What would help most right now?", offer_answer="yes"))
    from mani.db import pool

    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "I keep spiralling")
    # The tap decides by itself, whatever the model reports.
    await send(alice, thread.id, "Keep chatting")

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


async def test_a_new_chat_asks_how_the_person_wants_to_be_spoken_to(alice):
    thread = await start(alice)
    [first] = await _history(alice, thread.id)
    assert first.content == "Hi Al. It's MANI. How would you like me to speak with you today?"
    assert [o["label"] for o in first.prompt_options] == ["Directive", "Supportive", "Reflective"]


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
    # The client's styles document (2026-10-12): only the chosen style reaches the model.
    system = scripted.last_messages[0]["content"]
    assert "MANI is thoughtful, curious, and exploratory" in system
    assert "MANI is clear, concise, and focused" not in system and "MANI is warm, understanding" not in system


async def test_a_greeting_stored_with_the_direct_button_opens_in_directive_after_migration_019(alice, model):
    """A greeting written before the rename still waits for its tap. 019 rewrites its button, so
    the tap opens the thread in the renamed style. Replaying 019 is safe: it ends where it began."""
    import pathlib

    from mani.db import pool

    scripted = model(Reply(text="What is happening for you?"))
    thread = await start(alice)
    before_019 = [
        {"label": "Direct", "style": "direct"},
        {"label": "Supportive", "style": "supportive"},
        {"label": "Reflective", "style": "reflective"},
    ]
    migration = pathlib.Path(__file__).parents[2] / "supabase/migrations/019_conversation_style_directive.sql"
    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.messages set prompt_options = $2 where thread_id = $1",
            thread.id, before_019,
        )
        await conn.execute(migration.read_text())

    turn = await send(alice, thread.id, "Directive")

    assert turn.content == "How can I help you today?"
    assert scripted.calls == 0
    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)
    assert ctx.thread.conversation_style.value == "directive"


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


async def _land_on(alice, thread_id, phase, stages_known: dict | None = None) -> None:
    from mani.db import pool

    async with pool.as_user(alice) as conn:
        await set_technique_outcome(
            conn, thread_id, ALICE, "abcde", TechniqueOutcome.ACCEPTED,
            at_message_count=2, phase=phase, stages_known=stages_known,
        )


async def test_carrying_on_past_an_offer_is_keep_chatting(alice, model):
    """muhammad, 2026-09-24: someone who types on without answering the offer has chosen to keep
    chatting. Observed: "Would you like to try it?" came back on the very next reply, and the
    one after. The shape that answers an offer has no offer field, so it cannot be made again."""
    offered_again = _offer().model_copy(update={"text": "You pick the phone back up."})
    model(_offer(), offered_again)
    from mani.db import pool

    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "my manager criticized me in front of everyone")
    turn = await send(alice, thread.id, "every time I try to start I pick the phone back up")

    assert turn.prompts == []
    assert turn.content == "You pick the phone back up."
    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)
    assert ctx.technique.outcome is TechniqueOutcome.DECLINED


async def test_an_offer_they_typed_past_is_flagged_then_closed(alice, model):
    """The model is told, on the turn itself, that its offer is waiting and they typed instead;
    a reply that reports no answer has let it go, and so does the offer."""
    scripted = model(_offer(), Reply(text="You pick the phone back up. What happens right before?"))
    from mani.db import pool

    thread = await past_the_opening(await start(alice))
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
    model(
        _offer(),
        Reply(text="You keep replaying it. Which part stays with you?", offer_answer="moved_on"),
        Reply(text="What happened?", offer_answer="yes"),
    )
    from mani.db import pool

    thread = await past_the_opening(await start(alice))
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
    offer = _offer()
    # Each reply asks something different: a question repeated word for word is redrafted.
    chats = [
        Reply(text=text) for text in (
            "What else has been on your mind about it?",
            "When does it come back to you most?",
            "Who was in the room when it happened?",
            "How did the evening go afterwards?",
        )
    ]
    scripted = model(offer, *chats, _check(), offer)
    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "my manager criticized me in front of everyone")
    await send(alice, thread.id, "Keep chatting")
    for text in ("it keeps coming back", "I replay it at night", "I can't let it go"):
        await send(alice, thread.id, text)
    await send(alice, thread.id, "it's still on my mind")

    again = await send(alice, thread.id, "yes, that's it")
    assert [p.technique for p in again.prompts if p.technique] == ["abcde"]
    # The way back is a new check once the cooldown has passed, never an offer on its own.
    assert ["check" in shape.model_fields for shape in scripted.schemas[2:]] == [False, False, False, True, False]


async def test_an_offer_carries_the_clients_three_buttons_and_tell_me_more_offers_again(
    alice, model,
):
    """The client's offer: Try it, Tell me more, Keep chatting. Tell me more is answered with the
    client's explanation and the offer again with the other two, in the same turn and with no
    second model call, whatever the model wrote (muhammad, 2026-10-08)."""
    described = Reply(text="They help you look at what happened and what you made it mean.", offer_answer="no")
    scripted = model(_offer(), described)
    thread = await past_the_opening(await start(alice))

    offered = await send(alice, thread.id, "she criticized me in front of the team so i must be useless")
    assert [p.label for p in offered.prompts] == ["Try it", "Tell me more", "Keep chatting"]
    assert offered.prompts[0].technique == "abcde" and offered.prompts[2].decline is True

    # The tap decides by itself: the model's no is ignored, and the row stays offered.
    told = await send(alice, thread.id, "Tell me more")
    assert scripted.calls == 2
    assert [p.label for p in told.prompts] == ["Try it", "Keep chatting"]
    assert told.prompts[0].technique == "abcde"
    assert told.content.startswith("The ABCDE framework") and told.content.endswith("Would you like to try it?")


async def test_a_yes_to_an_open_offer_starts_it_even_with_no_buttons_showing(alice, model):
    """An offer can stay open with no buttons under Mani's last message, when the reply to Tell
    me more came on a safety concern and held them back. A yes then started the questions in
    Mani's words while the database still said offered, so the framework never properly began."""
    from mani.db import pool

    asked_instead = Reply(
        text="They help you choose a first step. What part of it bothers you most?",
        crisis=Crisis(reason="hopelessness"),
    )
    begins = Reply(text="What do you know for certain?", offer_answer="yes")
    model(_offer(), asked_instead, begins)
    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "my coworkers steal my work and take the credit")
    told = await send(alice, thread.id, "Tell me more")
    assert not any(p.technique for p in told.prompts)

    await send(alice, thread.id, "yes")
    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)
    assert ctx.technique.framework_id == "abcde"
    assert ctx.technique.outcome is TechniqueOutcome.ACCEPTED


class _SlowModel(ScriptedModel):
    """A model that takes a moment to answer, so two turns sent together overlap, and that keeps
    the conversation each call was shown."""

    def __init__(self, *replies: Reply) -> None:
        super().__init__(*replies)
        self.histories: list[list[str]] = []

    async def __call__(self, messages, schema, **kwargs):
        self.histories.append([m["content"] for m in messages])
        await asyncio.sleep(0.3)
        return await super().__call__(messages, schema, **kwargs)


async def test_a_second_message_waits_for_the_first_and_sees_its_reply(alice, monkeypatch):
    """muhammad's test, 2026-10-09: "idk yet" was sent again while the first was still waiting on
    a 25 second reply. Both turns ran at once on the same history, neither saw the other's
    answer, and Mani asked the same question twice."""
    slow = _SlowModel(
        Reply(text="What thought comes up when you picture seeing them?"),
        Reply(text="You said you don't know yet. Is it more the people, or the place?"),
    )
    monkeypatch.setattr(orchestrator.client, "complete", slow)
    thread = await past_the_opening(await start(alice))

    await asyncio.gather(send(alice, thread.id, "idk yet"), send(alice, thread.id, "idk yet"))

    assert slow.calls == 2
    assert "What thought comes up when you picture seeing them?" in slow.histories[1]


async def _offered_row(alice, thread_id):
    from mani.db import pool

    async with pool.as_user(alice) as conn:
        return (await threads.load_turn_context(conn, thread_id, ALICE)).technique


async def test_a_typed_no_is_the_clients_keep_chatting_question_with_their_words(alice, model):
    """Spec 0003, AC-4: the reply to a no is the client's Keep chatting line, only the slot changed.
    Without their words for the slot the model's own text goes, and the miss is logged."""
    model(
        _offer(),
        Reply(text="Okay.", offer_answer="no", their_words='"stuck".'),
        _offer(),
    )
    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "I keep spiralling")
    turn = await send(alice, thread.id, "no thanks")

    assert turn.content == "We can keep talking. What's been happening that's making things feel so stuck?"
    assert turn.prompts == []
    assert (await _offered_row(alice, thread.id)).outcome is TechniqueOutcome.DECLINED


@pytest.mark.parametrize("answer", ["moved_on", None, "perhaps"])
async def test_any_answer_but_yes_or_asked_declines_and_keeps_the_models_text(alice, model, answer):
    # Built without validation, so an off-list value reaches the turn's own parse as the model's would.
    model(_offer(), Reply.model_construct(text="What happened next?", offer_answer=answer))
    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "I keep spiralling")
    turn = await send(alice, thread.id, "my sister called later")

    assert turn.content == "What happened next?"
    assert (await _offered_row(alice, thread.id)).outcome is TechniqueOutcome.DECLINED


async def test_a_concern_reported_by_the_model_changes_no_row_and_renders_nothing(alice, model):
    """Spec 0003, AC-12, and spec 0004, AC-10: on the model's crisis field, a yes to the open offer
    starts nothing, seeds nothing, and only the model's text is sent."""
    scripted = model(_offer(), Reply(
        text="I'm here with you. What's happening right now?",
        offer_answer="yes", crisis=Crisis(reason="hopelessness"),
        next_stage=NextStage(status="known", said="spiralling at night"),
    ))
    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "I keep spiralling")
    turn = await send(alice, thread.id, "yes, nothing matters anyway")

    assert scripted.calls == 2
    assert (turn.content, turn.prompts) == ("I'm here with you. What's happening right now?", [])
    row = await _offered_row(alice, thread.id)
    assert (row.outcome, row.stages_known) == (TechniqueOutcome.OFFERED, {})


async def test_the_turn_log_names_the_moment_and_the_offer_and_never_their_words(alice, model, caplog):
    """Spec 0003, AC-10: the judgments are countable in the logs, and slot text never reaches one."""
    model(_offer())
    thread = await past_the_opening(await start(alice))
    with caplog.at_level("INFO", logger="mani"):
        await send(alice, thread.id, "I keep spiralling")

    assert "moment check_open: check_answer yes, offer_answer None, body None, stage_answer None, offered abcde" in caplog.text
    assert "what happened at work" not in caplog.text
    assert "a lot to carry" not in caplog.text


async def test_the_two_choices_never_come_from_reading_the_reply(alice, model):
    """Spec 0003, AC-6: a reply that only says "keep chatting or go to the library" on its own is
    not a hand-off; the branch or the retirement decides."""
    model(Reply(text="Would you like to keep chatting or go to the Library?"))
    thread = await start(alice)
    await _land_on(alice, thread.id, "somatic_body")

    turn = await send(alice, thread.id, "hmm")
    assert turn.prompts == []


# The ABCDE walk (spec 0004). What the client wrote is read from the seeded file, so each test pins
# the reply to the client's own lines rather than to a copy of them.

def _abcde_stages() -> dict:
    from scripts.seed import FRAMEWORKS_DIR, parse_framework

    return parse_framework(FRAMEWORKS_DIR / "abcde.md")["stages"]


def _opens(stage: str, then: str) -> str:
    return f"{_abcde_stages()[stage]['intro']} {then}"


def _asks(stage: str) -> str:
    return _opens(stage, _abcde_stages()[stage]["ask"]["supportive"])


# Nothing they said answers the stage the walk reaches next.
_MISSING = NextStage(status="missing")


def _answered(stage: str, words: str, then: str) -> Reply:
    """Their words for the stage in force, and Mani's own question for the stage reached, judged missing."""
    return Reply(text=then, stage_answer="answered", next_stage=_MISSING,
                 stage_updates=[StageUpdate(stage=stage, said=words, status="known")])


# Mani's own question for each stage reached as missing, about their situation (thread 425f6a55).
_OWN_QUESTIONS = {
    "activate": "What happened at work that you want to look at?",
    "belief": "What did you start telling yourself when they left you out of the meeting?",
    "consequence": "How did thinking nobody wants you there affect how you felt or what you did?",
    "dispute": "What makes you believe nobody wants you there, and what makes you question it?",
    "effective": "What's a more realistic way to think about being left out of that meeting?",
}


async def _store(alice, thread_id) -> dict:
    return (await _offered_row(alice, thread_id)).stages_known.get("abcde") or {}


async def test_a_walk_with_nothing_known_names_each_letter_and_asks_one_stage_per_reply(alice, model):
    """AC-1, AC-2, AC-6, AC-11: each stage opens with its letter line and Mani's own question about
    their situation, one stage per reply and one call per turn, then the body check-in follows E, after
    one short sentence with no question."""
    scripted = model(
        _offer(), Reply(text=_OWN_QUESTIONS["activate"], next_stage=_MISSING),
        _answered("activate", "left out of meetings", _OWN_QUESTIONS["belief"]),
        _answered("belief", "nobody wants me there", _OWN_QUESTIONS["consequence"]),
        _answered("consequence", "I stopped speaking up", _OWN_QUESTIONS["dispute"]),
        _answered("dispute", "they never said why", _OWN_QUESTIONS["effective"]),
        _answered("effective", "I don't know why yet", "Thank you."),
    )
    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "I keep getting left out at work")
    replies = [await send(alice, thread.id, said) for said in (
        "Try it", "they left me out of the meeting", "nobody wants me there", "I stopped speaking up",
        "they never said why", "maybe I don't know why yet",
    )]

    assert [turn.content for turn in replies[:5]] == [
        _opens(stage, _OWN_QUESTIONS[stage]) for stage in ("activate", "belief", "consequence", "dispute", "effective")
    ]
    assert replies[5].content.endswith("Where are you noticing any tension or discomfort right now?")
    assert scripted.calls == 7
    assert (await _offered_row(alice, thread.id)).phase == "somatic_body"
    store = await _store(alice, thread.id)
    assert {stage: entry["status"] for stage, entry in store.items()} == dict.fromkeys(
        ("activate", "belief", "consequence", "dispute", "effective"), "done")
    assert store["belief"]["said"] == "nobody wants me there"
    assert replies[1].stage_trace[1] == {"stage": "belief", "status": "missing", "asking": True}
    assert not any("reach unjudged" in turn.checks for turn in replies), "every stage was judged missing"


async def _say_yes(alice, thread_id, entry: str):
    """Their yes, the way `entry` gives it: a Try it tap, a typed yes, or asking for the set after
    declining it."""
    if entry == "declined":
        await send(alice, thread_id, "Keep chatting")
        return await send(alice, thread_id, "actually I'd like to look at it")
    return await send(alice, thread_id, "Try it" if entry == "tap" else "yes let's do it")


@pytest.mark.parametrize("entry", ["tap", "typed", "declined"])
async def test_what_they_said_before_the_yes_is_said_back_and_confirmed_once_never_asked(alice, model, entry):
    """AC-3, AC-4, AC-7, 2026-10-13: each stage is judged when the walk reaches it. On the yes the reply
    judges A in next_stage, and a B it reports that early is dropped; reaching B, it judges B from what
    they said before the offer. A and B open with the client's letter line, then Mani's own confirmation;
    C, which they never said, is asked."""
    a_own = "So it started with being left out of meetings at work. Is that where this began for you?"
    b_own = "You've been telling yourself nobody wants you there. Is that still how it feels?"
    declining = [Reply(text="What else is on your mind?", their_words="left out")] if entry == "declined" else []
    model(
        _offer(), *declining,
        Reply(text=a_own, offer_answer="yes",
              next_stage=NextStage(status="possible", said="being left out of meetings at work"),
              stage_updates=[StageUpdate(stage="belief", said="nobody wants me there", status="known")]),
        Reply(text=b_own, stage_answer="agreed", next_stage=NextStage(status="known", said="nobody wants me there")),
        Reply(text="Thank you.", stage_answer="agreed", next_stage=_MISSING),
    )
    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "I'm left out of meetings at work and I think nobody wants me there")

    started = await _say_yes(alice, thread.id, entry)
    assert started.content == _opens("activate", a_own)
    confirmed = await send(alice, thread.id, "yes")
    assert confirmed.content == _opens("belief", b_own)
    assert (await send(alice, thread.id, "yes")).content == _asks("consequence")
    store = await _store(alice, thread.id)
    assert (store["activate"]["status"], store["belief"]["status"]) == ("done", "done")


async def test_a_yes_whose_turn_was_guarded_starts_the_walk_on_the_next_turn(alice, model):
    """AC-3: the row was left accepted at the offer, so the next turn is the start turn."""
    model(Reply(text="Let's look at it.", understanding_update=UnderstandingUpdate(feeling="overwhelmed")))
    thread = await start(alice)
    await _land_on(alice, thread.id, "offering")

    turn = await send(alice, thread.id, "okay, I'm ready now")
    assert turn.content == _opens("activate", "What's been happening that's left you feeling so overwhelmed?")
    assert (await _offered_row(alice, thread.id)).phase == "activate"


async def test_a_plain_no_stays_on_the_stage_and_new_words_move_on(alice, model, caplog):
    """AC-8, AC-12: a no to the check is the model's follow up alone, with no letter line; their new
    words then replace the stored ones and the walk moves on. The log names the answer, never the words."""
    from mani.db import pool

    model(
        Reply(text="I misunderstood. What would be more accurate?", stage_answer="not_yet"),
        Reply(text="Thank you.", stage_answer="answered",
              stage_updates=[StageUpdate(stage="belief", said="they will fire me", status="known")]),
    )
    thread = await start(alice)
    async with pool.as_user(alice) as conn:
        await set_technique_outcome(
            conn, thread.id, ALICE, "abcde", TechniqueOutcome.ACCEPTED, at_message_count=2,
            phase="belief", stages_known={"abcde": {"belief": {"said": "nobody wants me", "status": "known"}}},
        )

    with caplog.at_level("INFO", logger="mani"):
        stayed = await send(alice, thread.id, "no, that's not it")
        moved = await send(alice, thread.id, "I think they will fire me")

    assert stayed.content == "I misunderstood. What would be more accurate?"
    assert moved.content == _asks("consequence")
    assert "reach unjudged" in moved.checks, "the reply moved the walk without judging C"
    assert (await _store(alice, thread.id))["belief"] == {"said": "they will fire me", "status": "done"}
    assert "stage_answer not_yet" in caplog.text and "stage_answer answered" in caplog.text
    assert "fire me" not in caplog.text and "nobody wants me" not in caplog.text


async def test_a_correction_to_an_earlier_stage_replaces_its_words_and_the_walk_stays(alice, model):
    """AC-8, AC-9."""
    from mani.db import pool

    model(Reply(text="Thanks for putting that right. What supports the belief?", stage_answer="not_yet",
                stage_updates=[StageUpdate(stage="activate", said="dropped from the team meeting",
                                           status="known", corrected=True)]))
    thread = await start(alice)
    async with pool.as_user(alice) as conn:
        await set_technique_outcome(
            conn, thread.id, ALICE, "abcde", TechniqueOutcome.ACCEPTED, at_message_count=2,
            phase="dispute", stages_known={"abcde": {"activate": {"said": "left out", "status": "done"}}},
        )

    await send(alice, thread.id, "actually it was being dropped from the team meeting")
    assert (await _offered_row(alice, thread.id)).phase == "dispute"
    assert (await _store(alice, thread.id))["activate"] == {"said": "dropped from the team meeting", "status": "done"}


async def test_a_stage_reached_late_is_confirmed_from_what_they_said_long_before(alice, model):
    """AC-9, 2026-10-13: the whole thread is in view, so the belief said 26 messages earlier is still
    there when the walk reaches B; the reply reports it then and confirms it, never asks it. A belief
    stored ahead by an earlier version is ignored."""
    from mani.db import pool

    belief = "You've been telling yourself nobody wants you there. Is that still how it feels?"
    scripted = model(
        *[Reply(text=f"What happened next, {n}?") for n in range(13)],
        Reply(text=belief, stage_answer="answered",
              stage_updates=[StageUpdate(stage="activate", said="left out of the meeting", status="known")],
              next_stage=NextStage(status="known", said="nobody wants me there")),
    )
    thread = await start(alice)
    await send(alice, thread.id, "I keep thinking nobody wants me there")
    for n in range(12):
        await send(alice, thread.id, f"one more thing, number {n}")
    async with pool.as_user(alice) as conn:
        await set_technique_outcome(
            conn, thread.id, ALICE, "abcde", TechniqueOutcome.ACCEPTED, at_message_count=2, phase="activate",
            stages_known={"abcde": {"belief": {"said": "a stale belief", "status": "known"}}},
        )

    turn = await send(alice, thread.id, "they left me out of the meeting")
    assert any("I keep thinking nobody wants me there" in m["content"] for m in scripted.last_messages)
    assert turn.content == _opens("belief", belief)
    assert (await _store(alice, thread.id))["belief"] == {"said": "nobody wants me there", "status": "known"}


async def test_a_feeling_from_their_first_message_is_said_back_when_the_walk_reaches_c(alice, model):
    """Thread 4b93d612, 2026-10-14: "I am frustrated" was their first message, before Mani's check, and
    C was asked again. Reaching C, the reply judges it partial from that message and its confirmation
    is sent. This pins the code path; the live scenario frustrated_work_full tests the judgement."""
    from mani.db import pool

    own = "You mentioned feeling frustrated. Is that how believing the timeline will slip has affected you?"
    scripted = model(
        Reply(text="I'm listening. What's frustrating you?"),
        Reply(text=own, stage_answer="answered",
              stage_updates=[StageUpdate(stage="belief", said="the whole timeline goes south", status="known")],
              next_stage=NextStage(status="partial", said="you feel frustrated")),
    )
    thread = await start(alice)
    await send(alice, thread.id, "I am frustrated.")
    async with pool.as_user(alice) as conn:
        await set_technique_outcome(
            conn, thread.id, ALICE, "abcde", TechniqueOutcome.ACCEPTED, at_message_count=2, phase="belief",
            stages_known={"abcde": {"activate": {"said": "your coworkers don't follow through", "status": "done"}}},
        )

    turn = await send(alice, thread.id, "everything that comes next goes south and the timeline slips")
    assert "next_stage" in scripted.schemas[-1].model_fields
    assert turn.content == _opens("consequence", own)
    assert (await _store(alice, thread.id))["consequence"] == {"said": "you feel frustrated", "status": "partial"}
    assert "reach unjudged" not in turn.checks


async def test_a_guarded_turn_leaves_the_store_and_the_stage_as_they_were(alice, model):
    """AC-10: on the model's crisis field nothing is merged, stepped or rendered."""
    from mani.db import pool

    stored = {"abcde": {"consequence": {"said": "I stopped going", "status": "partial"}}}
    model(Reply(text="I'm here with you. Are you safe right now?", crisis=Crisis(reason="hopelessness"),
                stage_answer="answered",
                stage_updates=[StageUpdate(stage="consequence", said="I stay in bed", status="known")]))
    thread = await start(alice)
    async with pool.as_user(alice) as conn:
        await set_technique_outcome(
            conn, thread.id, ALICE, "abcde", TechniqueOutcome.ACCEPTED, at_message_count=2,
            phase="consequence", stages_known=stored,
        )

    turn = await send(alice, thread.id, "I don't see the point of any of it")
    assert turn.content == "I'm here with you. Are you safe right now?"
    row = await _offered_row(alice, thread.id)
    assert (row.phase, row.stages_known) == ("consequence", stored)


async def test_a_new_offer_row_never_wipes_the_stage_store(alice):
    """AC-10: the store has its own write, so the shared upsert of a later offer keeps it."""
    from mani.db import pool

    stored = {"abcde": {"belief": {"said": "nobody wants me there", "status": "done"}}}
    thread = await start(alice)
    async with pool.as_user(alice) as conn:
        await set_technique_outcome(conn, thread.id, ALICE, "abcde", TechniqueOutcome.ACCEPTED,
                                    at_message_count=2, phase=None, stages_known=stored)
        await set_technique_outcome(conn, thread.id, ALICE, "abcde", TechniqueOutcome.OFFERED,
                                    at_message_count=60, phase="offering")

    row = await _offered_row(alice, thread.id)
    assert (row.outcome, row.stages_known) == (TechniqueOutcome.OFFERED, stored)


# Spec 0005: what Mani understands of them, their feeling word and their issue, kept by code.


async def _understood(alice, thread_id) -> dict:
    from mani.db import pool

    async with pool.as_user(alice) as conn:
        return (await threads.load_turn_context(conn, thread_id, ALICE)).thread.understanding


def _ctx_sent(scripted: ScriptedModel) -> str:
    return scripted.last_messages[-1]["content"]


async def test_what_they_name_is_stored_and_sent_back_on_every_later_turn(alice, model, caplog):
    """AC-1, AC-2, AC-11: the feeling from their first message and the issue from their second are
    stored, on one line, and the third turn's [ctx] carries both; a blank update keeps them. No log
    line carries either."""
    scripted = model(
        Reply(text="What is it about?", understanding_update=UnderstandingUpdate(feeling="frustrated")),
        Reply(text="What happens then?",
              understanding_update=UnderstandingUpdate(issue="my client keeps\nchanging the requirements")),
        Reply(text="What goes through your mind?", understanding_update=UnderstandingUpdate(feeling=" ")),
    )
    thread = await start(alice)

    with caplog.at_level("INFO", logger="mani"):
        first = await send(alice, thread.id, "i am frustrated")
        assert "understanding:" not in _ctx_sent(scripted)
        await send(alice, thread.id, "my client keeps changing the requirements")
        third = await send(alice, thread.id, "we are moving in circles")

    expected = {"feeling": "frustrated", "issue": "my client keeps changing the requirements"}
    assert "understanding: feeling: frustrated; issue: my client keeps changing the requirements" in _ctx_sent(scripted)
    assert (first.understanding, third.understanding) == ({"feeling": "frustrated"}, expected)
    assert await _understood(alice, thread.id) == expected
    assert scripted.calls == 3
    assert "frustrated" not in caplog.text and "changing the requirements" not in caplog.text


async def test_what_they_named_early_stays_in_view_and_in_the_understanding_line(alice, model):
    """AC-2, and 2026-10-13: the whole thread is in view within the budget, so the message that named
    the feeling is still there 25 messages later, and the understanding line still carries it."""
    scripted = model(
        Reply(text="What is it about?", understanding_update=UnderstandingUpdate(feeling="anxious")),
        Reply(text="And then?"),
    )
    thread = await start(alice)
    await send(alice, thread.id, "I feel anxious")
    for n in range(12):
        await send(alice, thread.id, f"one more thing, number {n}")

    assert any("I feel anxious" in m["content"] for m in scripted.last_messages)
    assert "understanding: feeling: anxious" in _ctx_sent(scripted)


@pytest.mark.parametrize("named", [True, False])
async def test_a_opens_with_the_feeling_they_named_before_the_yes(alice, model, caplog, named):
    """AC-7: on the start turn, A's missing line fills its slot from the stored feeling; with none
    stored it is the client's ask, and the empty slot is logged."""
    model(
        Reply(text="What happened?",
              understanding_update=UnderstandingUpdate(feeling="overwhelmed") if named else None),
        Reply(text="Let's look at it."),
    )
    thread = await start(alice)
    await send(alice, thread.id, "it's a lot at the moment")
    await _land_on(alice, thread.id, "offering")

    with caplog.at_level("INFO", logger="mani"):
        turn = await send(alice, thread.id, "okay, I'm ready now")

    if named:
        assert turn.content == _opens("activate", "What's been happening that's left you feeling so overwhelmed?")
    else:
        assert turn.content == _asks("activate")
        assert "slot empty" in caplog.text


async def test_a_concern_turn_leaves_what_was_understood_as_it_was(alice, model):
    """AC-11: a reply the model flags as a concern reports a feeling and an issue; neither is kept."""
    model(
        Reply(text="What is it about?", understanding_update=UnderstandingUpdate(feeling="sad")),
        Reply(text="I'm here with you.", crisis=Crisis(reason="may not be safe"),
              understanding_update=UnderstandingUpdate(feeling="hopeless", issue="everything")),
    )
    thread = await start(alice)
    await send(alice, thread.id, "I'm sad")
    turn = await send(alice, thread.id, "I don't see the point of anything")

    assert turn.understanding == {"feeling": "sad"}
    assert await _understood(alice, thread.id) == {"feeling": "sad"}


async def test_not_knowing_keeps_the_framework_on_its_stage_until_they_answer(alice, model):
    """muhammad, 2026-10-21: three "I don't know" in a row used to let the stage go. The walk stays on
    it each time, and the possibilities they pick are their answer when they say them as theirs."""
    unsure = Reply(text="That's hard to pin down. Maybe 'I'm not good enough', or 'I can't handle this'?",
                   stage_answer="not_yet")
    model(unsure, unsure, unsure, Reply(
        text="So you told yourself you can't handle this. What happened next?", stage_answer="answered",
        stage_updates=[StageUpdate(stage="belief", said="I can't handle this", status="known")],
        next_stage=NextStage(status="missing"),
    ))
    thread = await start(alice)
    await _land_on(alice, thread.id, "belief")

    for _ in range(3):
        await send(alice, thread.id, "i don't know")
        assert (await _offered_row(alice, thread.id)).phase == "belief"
    await send(alice, thread.id, "the second one, i can't handle this")
    assert (await _offered_row(alice, thread.id)).phase == "consequence"


async def test_a_wish_to_stop_leaves_the_framework_and_it_comes_back_only_when_asked_for(alice, model):
    """Only they can end the questions. Stopping leaves the framework as declined, not finished."""
    model(Reply(text="That's okay. What would you like to talk about?", stage_answer="stop"))
    thread = await start(alice)
    await _land_on(alice, thread.id, "belief")

    turn = await send(alice, thread.id, "i want to stop these questions")
    row = await _offered_row(alice, thread.id)

    assert turn.content == "That's okay. What would you like to talk about?"
    assert (row.outcome, row.phase) == (TechniqueOutcome.DECLINED, None)


async def test_a_stage_turn_is_sent_the_case_found_before_the_offer(alice, model):
    """muhammad, 2026-10-22: the problem and the core issue reach the model on every stage turn as
    their_case, so its question is about them."""
    from mani.db import pool

    scripted = model(Reply(text="What did he say about your work?", stage_answer="not_yet"))
    thread = await start(alice)
    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.threads set understanding = $2::jsonb where id = $1", thread.id,
            {"issue": "your coworkers miss deadlines", "core_issue": "the work always lands on you"},
        )
    await _land_on(alice, thread.id, "belief")

    await send(alice, thread.id, "i don't know")
    sent = scripted.last_messages[-1]["content"]
    assert "their_case: " in sent and "the work always lands on you" in sent


async def test_what_is_still_to_ask_at_d_is_stored_and_sent_on_the_next_turn(alice, model):
    """muhammad, 2026-10-21 (sister thread): D asked what supports the belief and later turns never asked what
    might challenge it. The reply reports the challenge as the part still to ask; it is stored and sent back."""
    scripted = model(
        Reply(text="You feel guilty at the thought of saying no because you believe family should always help. "
                   "What might make you question that, even a little?",
              stage_answer="not_yet",
              stage_updates=[StageUpdate(stage="dispute", said="family should always help", status="partial",
                                         gap="challenge")]),
        Reply(text="Thank you for telling me. What else comes to mind?", stage_answer="not_yet"),
    )
    thread = await start(alice)
    done = {"said": "x", "status": "done"}
    await _land_on(alice, thread.id, "dispute", {"abcde": {"activate": done, "belief": done, "consequence": done}})

    await send(alice, thread.id, "we always help family, no matter what")
    assert (await _store(alice, thread.id))["dispute"] == {
        "said": "family should always help", "status": "partial", "gap": "challenge"}

    await send(alice, thread.id, "i'm not sure")
    sent = scripted.last_messages[-1]["content"]
    assert 'dispute partial, still to ask challenge: "family should always help"' in sent


async def test_the_options_for_answering_arrive_on_the_line_under_the_question(alice, model):
    """muhammad, 2026-10-22: a reply before the check is the mirror, its question, then the options as a
    question of their own, each on its own line, however the model wrote its text."""
    from mani.models.rows import SupportStyle

    model(Reply(
        text="That long day has left you feeling anxious. What part of it is weighing on you most?",
        options="Is it something that happened, what still needs doing, or the day catching up with you",
    ))
    thread = await _in_style(await start(alice), SupportStyle.DIRECTIVE)
    turn = await send(alice, thread.id, "I had a really long day and i am feeling anxious.")
    assert turn.content == (
        "That long day has left you feeling anxious.\n\nWhat part of it is weighing on you most?\n\n"
        "Is it something that happened, what still needs doing, or the day catching up with you?"
    )


async def test_what_they_add_during_a_framework_is_added_to_the_case_and_nothing_is_lost(alice, model):
    """muhammad, 2026-10-22: what they say ten turns into the framework is added to the problem, core issue
    and feeling, and what was stored stays."""
    from mani.db import pool

    model(Reply(
        text="That makes the deadline feel very real. What would missing it mean for you?",
        stage_answer="not_yet",
        understanding_update=UnderstandingUpdate(
            issue="you need two months and the deadline is this week", feeling="burnt out",
            also="needs about two months, the deadline is this week",
        ),
    ))
    thread = await start(alice)
    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.threads set understanding = $2::jsonb where id = $1", thread.id,
            {"feeling": "anxious", "issue": "overtime to meet deadlines", "core_issue": "the work falls on you"},
        )
    await _land_on(alice, thread.id, "belief")

    await send(alice, thread.id, "i need about 2 months but the deadline is this week")
    stored = (await _thread_row(alice, thread.id)).understanding
    assert stored["issue"] == "overtime to meet deadlines; you need two months and the deadline is this week"
    assert stored["core_issue"] == "the work falls on you"
    assert stored["feeling"] == "anxious, burnt out"
    assert stored["also"] == "needs about two months, the deadline is this week"


# The client's body check-in after a framework (migration 025, spec: somatic cadence). Each tap is the
# label as the person sees it; the model is scripted only for the words code leaves to it.


async def _outcomes(alice, thread_id) -> tuple[str | None, str | None]:
    row = await _offered_row(alice, thread_id)
    return row.physical_response, row.conversation_effect


async def test_answering_the_last_stage_goes_straight_into_step_one_with_its_five_buttons(alice, model):
    """muhammad, 2026-10-22: no question before the client's Step 1; No Tension is the way out."""
    model(Reply(
        text="You'll work on clarifying expectations. Does that feel right?", stage_answer="answered",
        stage_updates=[StageUpdate(stage="effective", said="raise it with my manager", status="known")],
    ))
    thread = await start(alice)
    await _land_on(alice, thread.id, "effective")
    turn = await send(alice, thread.id, "it sits easier now")
    assert turn.content.startswith("You'll work on clarifying expectations.\n\nNow that we've worked through your thoughts")
    assert turn.content.endswith("Where are you noticing any tension or discomfort right now?")
    assert "check in with your body?" not in turn.content
    assert [p.label for p in turn.prompts] == ["Chest", "Stomach", "Head", "Somewhere Else", "No Tension"]
    assert (await _offered_row(alice, thread.id)).phase == "somatic_body"


async def test_the_whole_body_check_in_by_taps_records_each_outcome_apart(alice, model):
    """Chest, Feel Better, Yes It Helped, then Keep Chatting: the client's steps, each reply her words, and the
    continuation after Keep Chatting carries the model's question with its possibilities under it."""
    model(
        Reply(text="ignored", body="chest"),
        Reply(text="ignored", body="better"),
        Reply(text="ignored", body="helped"),
        Reply(text="You chose to clarify expectations with your boss. What feels like the first step to take there?",
              body="keep_chatting",
              options="Is it asking for an example, agreeing what done looks like, or something else"),
    )
    thread = await start(alice)
    await _land_on(alice, thread.id, "somatic_body")

    exercise = await send(alice, thread.id, "Chest")
    assert exercise.content.startswith("Let's bring your attention to your chest for a moment.")
    assert [p.label for p in exercise.prompts] == ["Feel Better", "Feel the Same", "Feel Worse"]

    effect = await send(alice, thread.id, "Feel Better")
    assert effect.content.startswith("I'm glad you're feeling some relief.")
    assert effect.content.endswith("do you feel our conversation helped you?")
    assert await _outcomes(alice, thread.id) == ("better", None)

    closing = await send(alice, thread.id, "Yes, It Helped")
    assert closing.content.startswith("I'm glad our conversation was helpful.")
    assert [(p.label, p.library) for p in closing.prompts] == [
        ("Keep Chatting", None), ("Go to Library", "home"), ("Finish for Now", None),
    ]
    assert await _outcomes(alice, thread.id) == ("better", "helped")

    kept = await send(alice, thread.id, "Keep Chatting")
    assert kept.content == (
        "You chose to clarify expectations with your boss. What feels like the first step to take there?\n\n"
        "Is it asking for an example, agreeing what done looks like, or something else?"
    )
    assert (await _offered_row(alice, thread.id)).phase is None, "the run retired"
    assert await _outcomes(alice, thread.id) == ("better", "helped"), "the outcomes outlive the run"


async def test_keep_chatting_is_sent_where_they_ended_up_and_what_they_told_mani(alice, model):
    """muhammad, 2026-10-22: Keep Chatting answered \"what would you like to talk about now?\"."""
    scripted = model(Reply(text="Okay. What next?", body="keep_chatting"))
    thread = await start(alice)
    await _land_on(alice, thread.id, "somatic_closing")
    from mani.db import pool

    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.thread_technique_state set stages_known = $2::jsonb where thread_id = $1", thread.id,
            {"abcde": {"effective": {"said": "clarify expectations with my boss", "status": "done"}}},
        )
        await conn.execute(
            "update public.threads set understanding = $2::jsonb where id = $1", thread.id,
            {"issue": "rework keeps coming back", "underlying_feeling": "self-doubt about your ability"},
        )
        await conn.execute(
            "insert into public.messages (thread_id, user_id, role, content, prompt_options) values "
            "($1, $2, 'mani', 'I''m glad.', $3::jsonb)", thread.id, ALICE,
            [{"label": "Keep Chatting"}, {"label": "Go to Library", "library": "home"}, {"label": "Finish for Now"}],
        )
    await send(alice, thread.id, "Keep Chatting")
    sent = scripted.last_messages[-1]["content"]
    assert "their_case: " in sent and "self-doubt about your ability" in sent
    assert "landed_on: clarify expectations with my boss" in sent
    assert "\nunderstanding: " not in sent


async def test_no_tension_skips_the_exercise_and_records_it_as_the_physical_response(alice, model):
    model(Reply(text="ignored", body="none"), Reply(text="ignored", body="somewhat"))
    thread = await start(alice)
    await _land_on(alice, thread.id, "somatic_body")

    block = await send(alice, thread.id, "No Tension")
    assert block.content.startswith("That's good to hear.")
    assert [p.label for p in block.prompts] == ["Yes, it helped", "Somewhat", "No, not really"]
    closing = await send(alice, thread.id, "Somewhat")
    assert closing.content == "I'm glad some of our conversation was helpful, even if it didn't address everything you needed."
    assert await _outcomes(alice, thread.id) == ("no_tension", "somewhat")


async def test_feeling_worse_stops_and_pain_ends_the_route_without_asking_whether_it_helped(alice, model):
    model(Reply(text="ignored", body="worse"), Reply(text="ignored", body="pain"))
    thread = await start(alice)
    await _land_on(alice, thread.id, "somatic_practice")
    worse = await send(alice, thread.id, "Feel Worse")
    assert worse.content.startswith("Thank you for telling me. Let's stop here.")
    assert await _outcomes(alice, thread.id) == ("worse", None)

    hurt = await start(alice)
    await _land_on(alice, hurt.id, "somatic_body")
    pain = await send(alice, hurt.id, "my wrist hurts a lot when i do this")
    assert pain.content == "Let's not do a breathing practice then. I'm here with you. What would help right now?"
    assert pain.prompts == []
    assert (await _offered_row(alice, hurt.id)).phase == "somatic_closing"


async def test_an_outcome_is_written_once_per_run_and_a_new_offer_clears_both(alice):
    from mani.db import pool

    thread = await start(alice)
    await _land_on(alice, thread.id, "somatic_practice")
    async with pool.as_user(alice) as conn:
        await threads.apply(conn, thread.id, ALICE, threads.ThreadUpdates(physical_response="better"))
        await threads.apply(conn, thread.id, ALICE, threads.ThreadUpdates(physical_response="worse"))
    assert (await _outcomes(alice, thread.id))[0] == "better"
    async with pool.as_user(alice) as conn:
        await threads.apply(conn, thread.id, ALICE, threads.ThreadUpdates(reset_outcomes=True))
    assert await _outcomes(alice, thread.id) == (None, None)


# The question about a place, asked once after a framework's last stage when what they said before it points to one.


async def _said_before(alice, thread_id, understanding: dict) -> None:
    from mani.db import pool

    async with pool.as_admin() as conn:
        await conn.execute("update public.threads set understanding = $2::jsonb where id = $1", thread_id, understanding)


def _last_stage_answered() -> Reply:
    return Reply(
        text="You'll raise it with your manager. Does that feel right?", stage_answer="answered",
        stage_updates=[StageUpdate(stage="effective", said="raise it with my manager", status="known")],
    )


async def test_after_the_last_stage_a_feeling_that_has_a_place_gets_the_personal_question(alice, model):
    """muhammad, 2026-10-21: the client's introduction, then this in place of the general question."""
    model(_last_stage_answered())
    thread = await start(alice)
    await _said_before(alice, thread.id, {"feeling": "embarrassed, anxious", "issue": "my manager criticised my report"})
    await _land_on(alice, thread.id, "effective")

    turn = await send(alice, thread.id, "it sits easier now")

    assert turn.content.startswith("You'll raise it with your manager.\n\nNow that we've worked through your thoughts")
    assert turn.content.endswith(
        "Earlier you mentioned feeling anxious, and that's often felt in the chest. Is that still the case for you right now?"
    )
    assert "Where are you noticing any tension" not in turn.content
    assert [p.label for p in turn.prompts] == ["Yes", "No"]
    assert (await _offered_row(alice, thread.id)).phase == "somatic_check"


async def test_yes_to_the_personal_question_starts_that_places_exercise_and_the_route_goes_on(alice, model):
    scripted = model(Reply(text="ignored", body="yes"), Reply(text="ignored", body="better"))
    thread = await start(alice)
    await _said_before(alice, thread.id, {"feeling": "stressed"})
    await _land_on(alice, thread.id, "somatic_check")

    exercise = await send(alice, thread.id, "Yes")
    assert exercise.content.startswith("Let's bring your attention to your head.")
    assert [p.label for p in exercise.prompts] == ["Feel Better", "Feel the Same", "Feel Worse"]
    assert (await _offered_row(alice, thread.id)).phase == "somatic_practice"
    effect = await send(alice, thread.id, "Feel Better")
    assert effect.content.endswith("do you feel our conversation helped you?")
    assert scripted.calls == 2


async def test_no_to_the_personal_question_carries_on_with_the_general_check_in(alice, model):
    model(Reply(text="ignored", body="no"))
    thread = await start(alice)
    await _said_before(alice, thread.id, {"feeling": "anxious"})
    await _land_on(alice, thread.id, "somatic_check")

    turn = await send(alice, thread.id, "No")

    assert turn.content == "Where are you noticing any tension or discomfort right now?"
    assert [p.label for p in turn.prompts] == ["Chest", "Stomach", "Head", "Somewhere Else", "No Tension"]
    assert (await _offered_row(alice, thread.id)).phase == "somatic_body"


async def test_a_feeling_with_no_place_gets_the_general_check_in_as_before(alice, model):
    model(_last_stage_answered())
    thread = await start(alice)
    await _said_before(alice, thread.id, {"feeling": "embarrassed"})
    await _land_on(alice, thread.id, "effective")

    turn = await send(alice, thread.id, "it sits easier now")

    assert turn.content.endswith("Where are you noticing any tension or discomfort right now?")
    assert [p.label for p in turn.prompts] == ["Chest", "Stomach", "Head", "Somewhere Else", "No Tension"]
    assert (await _offered_row(alice, thread.id)).phase == "somatic_body"


async def test_a_feeling_word_in_chat_or_inside_a_stage_never_starts_a_body_question(alice, model):
    """muhammad's run, 2026-10-21: "feel embarrassed and anxious" was answered with a question about the chest
    while Mani was still finding out how they feel. The check-in is only ever the end of a framework."""
    from mani.models.rows import SupportStyle

    scripted = model(Reply(text="That sounds like a lot. What part of it is weighing on you most?"),
                     Reply(text="What did you start telling yourself about that?", stage_answer="not_yet"))
    chatting = await _in_style(await start(alice), SupportStyle.SUPPORTIVE)
    asked = await send(alice, chatting.id, "I feel embarrassed and anxious")
    assert asked.content == "That sounds like a lot. What part of it is weighing on you most?"

    inside = await _in_style(await start(alice), SupportStyle.SUPPORTIVE)
    await _land_on(alice, inside.id, "belief")
    stage = await send(alice, inside.id, "I'm so anxious about it")
    assert "chest" not in stage.content and [p.label for p in stage.prompts] == []
    assert scripted.calls == 2
    assert (await _offered_row(alice, inside.id)).phase == "belief"


async def test_a_question_at_d_that_leaves_out_what_they_feel_believe_and_want_is_logged(alice, model):
    """Lolly, 2026-10-22: at D Mani asked only about her belief and the hurt and the missing were gone. D carries
    the case, so a reply with none of it is counted; one that carries any of it is not."""
    from mani.db import pool

    scripted = model(
        Reply(text="Is there anything that makes you question that?", stage_answer="not_yet"),
        Reply(text="You miss her and you want an apology. What makes you question that her silence means you "
                   "don't matter?", stage_answer="not_yet"),
    )
    thread = await start(alice)
    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.threads set understanding = $2::jsonb where id = $1", thread.id,
            {"feeling": "sad", "stack": "you miss her; her silence means you don't matter; you want an apology",
             "issue": "your friend has not spoken to you in three weeks"},
        )
    done = {"said": "x", "status": "done"}
    await _land_on(alice, thread.id, "dispute", {"abcde": {"activate": done, "belief": done, "consequence": done}})

    bare = await send(alice, thread.id, "she is ignoring me for three weeks")
    carried = await send(alice, thread.id, "we used to talk every day")
    assert scripted.calls == 2
    assert bare.checks == ["stack missing"]
    assert carried.checks == []
