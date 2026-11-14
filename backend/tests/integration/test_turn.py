# ABOUTME: Runs whole turns against a live database with a scripted model in place.
# ABOUTME: The model is faked; every write, policy and transition under test is real.

import asyncio
import dataclasses
import uuid

import asyncpg
import pytest

from mani.auth.jwt import Claims
from mani.chat import context, converse, crisis, orchestrator, runner
from mani.db import pauses
from mani.errors import ErrorCategory, ServiceError
from mani.config import get_settings
from mani.db import llm_calls, messages as messages_db, profiles, threads
from mani.llm import client
from mani.chat.repairs import PERMISSION_QUESTION
from mani.llm.schema import BeliefEntry, ConversationReply, ConversationUnderstanding, FeelingEntry, NextStage, Offer, PictureUpdate, Reply, SafetyRead, StageUpdate
from mani.models.rows import TechniqueOutcome, TechniqueState as TechniqueRow
from tests.integration.cleanup import remove_test_users

ALICE = uuid.UUID("a0000000-0000-4000-8000-0000000000d1")


def claims_for(user_id: uuid.UUID) -> Claims:
    return Claims(sub=str(user_id), raw={"sub": str(user_id), "role": "authenticated"})


def _in_shape(reply: Reply, schema: type) -> dict:
    """A scripted reply as the fields of the shape the turn asked for. A conversation turn reads the feelings,
    the check's parts and its flag from fields of its own, so a script written as a full Reply says the same
    thing in either shape."""
    fields = reply.model_dump()
    if schema is not ConversationReply or not isinstance(reply, Reply):
        return fields
    return fields


def felt(*words: str) -> PictureUpdate:
    """A reply whose picture records these feelings from their message."""
    return PictureUpdate(feelings=[FeelingEntry(feeling=word) for word in words])


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
        self.sent: list[list[dict]] = []
        self.kwargs: dict = {}
        # The readings after a chat reply (orchestrator.read_understanding), kept apart from the turn's own calls.
        self.reads: list[list[dict]] = []
        self.served: list[Reply] = []

    async def __call__(self, messages, schema, **kwargs):
        if schema is ConversationUnderstanding:
            # A scripted reply says what the turn's reading finds too: its picture, read after the reply it scripted.
            self.reads.append(messages)
            # The reply the reading follows: the one whose text went out, else the latest served.
            went_out = next((m["content"] for m in reversed(messages) if m["role"] == "assistant"), None)
            reply = next((r for r in reversed(self.served) if r.text == went_out), self.served[-1])
            return client.Call(
                value=schema.model_validate(_in_shape(reply, schema)), model="test/model",
                usage=llm_calls.Usage(input_tokens=100, output_tokens=20), latency_ms=1, call_id=uuid.uuid4(),
            )
        self.calls += 1
        self.last_messages = messages
        self.sent.append(messages)
        self.schemas.append(schema)
        self.kwargs = kwargs
        reply = self._replies[min(self.calls - 1, len(self._replies) - 1)]
        self.served.append(reply)
        return client.Call(
            # Parsed in the shape this turn sent, as the real call is: a field the moment does not
            # carry is dropped, however the script filled it.
            value=schema.model_validate(_in_shape(reply, schema)),
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


@pytest.fixture
def body_check_in(monkeypatch):
    """The body check-in as it runs when somatic.md pauses none of it: its stages back in every framework's phases.
    Paused since 2026-11-05 (muhammad); its route is kept and tested so it can come back with one reseed."""
    from mani.chat import body as body_route
    from mani.chat.techniques import Registry
    from mani.prompts import cache

    real = cache.load

    async def load():
        config = await real()
        whole = [
            framework.model_copy(update={
                "phases": [p for p in framework.phases if p not in body_route.STAGES] + list(body_route.STAGES),
            })
            for framework in (config.registry.get(i) for i in config.registry.ids)
        ]
        return dataclasses.replace(config, registry=Registry(whole))

    monkeypatch.setattr(cache, "load", load)


async def start(claims: Claims):
    from mani.db import pool

    async with pool.as_user(claims) as conn:
        await profiles.upsert(conn, ALICE, nickname="Al")
        thread = await orchestrator.start_thread(conn, claims)
    return thread


# The heart of it judged ready and checked: the conflict, what they want and what is stopping them (R33).
UNDERSTOOD = {
    "heart": "ready",
    "case": "The work always lands on you. You want them to carry their own share. Saying no feels like letting the team down.",
}


async def past_the_opening(thread):
    """The rounds of conversation the client wants before anything is offered, already had: the heart
    of it found, ending on Mani's check of its understanding, so the next message answers it (spec 0006,
    R33). For tests about what happens to an offer, not about when one may come. What the thread already holds stays."""
    from mani.db import pool

    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.threads set message_count = message_count + 8, "
            "check_at_message_count = message_count + 8, understanding = understanding || $2::jsonb where id = $1",
            thread.id, UNDERSTOOD,
        )
    return thread


async def send(claims: Claims, thread_id, content, **kwargs):
    """A turn as the endpoint runs it: committed, then the reading after a chat reply, whose record the turn
    returns."""
    turn = await runner.send(claims, thread_id, content, **kwargs)
    if turn.read_after is not None:
        read = await orchestrator.read_understanding(claims, turn.read_after)
        turn = dataclasses.replace(turn, understanding=read or turn.understanding)
    return turn


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


def _check() -> ConversationReply:
    """Mani's check of its understanding, in its own words, from a reply that judged the core ready: the core alone
    (muhammad, 2026-10-28)."""
    return ConversationReply(
        text="You may feel worn down. Your coworkers miss deadlines. Do I have that right?",
        heart="ready", checking=True,
        core="The work always lands on you, as if saying no would mean letting the team down",
    )


class _Moving(ConversationReply):
    """A scripted chat reply that moves to the set of questions: the fields that exist only on a turn that may move
    (schema.conversation_reply_for), dropped like any other when the turn's shape has none."""

    heading_toward: str | None = None
    offer: Offer | None = None


def _move(**update) -> _Moving:
    """Mani's move to the set of questions, with no check before it (the client meeting, 2026-11-03): the core, the
    set and the offer's slots, from a reply that judged the core ready."""
    return _Moving(
        text="That sounds like it keeps landing on you. Does that capture it?",
        heart="ready", checking=True,
        core="The work always lands on you, as if saying no would mean letting the team down",
        heading_toward="abcde",
        offer=Offer(lead_line="That sounds like a lot to carry.", going_through="what happened at work"),
    ).model_copy(update=update)


def _may_check(messages: list[dict]) -> bool:
    """Whether the note sent with a conversation turn let that reply move to the set of questions."""
    note = messages[-1]["content"]
    return note.startswith("Note for this reply only.") and converse.MOVE_NOT not in note


# _check()'s understanding as the case: the core.
CHECK_CASE = "The work always lands on you, as if saying no would mean letting the team down."


async def _no_check_open(thread):
    """past_the_opening, with its check answered long ago: the next message is ordinary chat that may move."""
    from mani.db import pool

    async with pool.as_admin() as conn:
        # From their fifth message (context.CHECK_FROM), whatever the opening added.
        await conn.execute(
            "update public.threads set check_at_message_count = null, message_count = greatest(message_count, 11) "
            "where id = $1",
            thread.id,
        )
    return thread


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
    "That sounds like a lot to carry.\nThere's a framework called ABCDE that can help you explore the belief "
    "that what happened at work, look at what's supporting that belief, and find a more balanced way to "
    "think about it.\n\nWould you like to try it?"
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


async def test_from_their_fifth_message_once_the_heart_of_it_was_agreed_mani_moves_straight_to_the_offer(alice, model):
    """muhammad, 2026-10-26: the chat before a framework is Mani's own conversation. The move is allowed from their
    5th message, and only after an earlier reply said the heart of it back and had it agreed. The client meeting
    (2026-11-03): no check of a summary before it; the reply that moves is the client's offer, with the core in it,
    and the core is the case the questions are about. One call each, and no check is stored."""
    from mani.db import pool
    from mani.models.rows import SupportStyle

    scripted = model(
        *[Reply(text=f"Was it the deadlines themselves, or what they cost you, {n}?", heart="exploring")
          for n in range(3)],
        Reply(text="It seems the work always lands on you. Is that the heart of it?", heart="core_named"),
        _move(),
    )
    thread = await _in_style(await start(alice), SupportStyle.SUPPORTIVE)
    for n in range(4):
        await send(alice, thread.id, f"my coworkers keep missing deadlines, {n}")
    turn = await send(alice, thread.id, "i want them to do their part but saying no feels like letting the team down")

    assert scripted.calls == 5
    assert scripted.schemas[:4] == [ConversationReply] * 4
    assert [_may_check(sent) for sent in scripted.sent[:5]] == [False] * 4 + [True]
    assert "offer" in scripted.schemas[4].model_fields and "Framework Index" in scripted.sent[4][-1]["content"]
    # The client's template word for word with the model's slots in it, never the model's text.
    assert turn.content == SUPPORTIVE_OFFER
    assert [p.label for p in turn.prompts] == ["Try it", "Tell me more", "Keep chatting"]
    row = await _thread_row(alice, thread.id)
    assert row.check_at_message_count is None
    assert (row.understanding["heart"], row.understanding["case"]) == ("ready", CHECK_CASE)
    async with pool.as_user(alice) as conn:
        technique = (await threads.load_turn_context(conn, thread.id, ALICE)).technique
    assert (technique.framework_id, technique.outcome) == ("abcde", TechniqueOutcome.OFFERED)


async def test_in_directive_the_move_keeps_manis_acknowledgment_without_its_question(alice, model):
    from mani.models.rows import SupportStyle

    model(_move(text="That's a lot to carry. Want to look at it?",
                offer=Offer(going_through="you have to hold it all together")))
    thread = await past_the_opening(await _in_style(await start(alice), SupportStyle.DIRECTIVE))
    await _no_check_open(thread)
    turn = await send(alice, thread.id, "yes, it always ends up on me")

    assert turn.content.startswith("That's a lot to carry.\n\nThere's a framework called ABCDE")
    assert "Want to look at it?" not in turn.content
    assert [p.technique for p in turn.prompts if p.technique] == ["abcde"]


async def test_the_move_to_the_offer_drops_the_forward_question_where_the_offer_takes_its_place(alice, model):
    """muhammad, 2026-11-10: every chat reply ends on a question, and the offer is the question of the reply that makes
    it, so the offer replaces it and the acknowledgment before it stays."""
    from mani.models.rows import SupportStyle

    model(_move(text="That's a lot to carry.", forward="Want to look at it?",
                offer=Offer(going_through="you have to hold it all together")))
    thread = await past_the_opening(await _in_style(await start(alice), SupportStyle.DIRECTIVE))
    await _no_check_open(thread)
    turn = await send(alice, thread.id, "yes, it always ends up on me")

    assert turn.content.startswith("That's a lot to carry.\n\nThere's a framework called ABCDE")
    assert "Want to look at it?" not in turn.content
    assert [p.technique for p in turn.prompts if p.technique] == ["abcde"]


async def test_a_move_whose_offer_cannot_be_made_still_ends_on_its_question(alice, model):
    model(_move(text="That sounds like it keeps landing on you.", forward="Does that capture it?",
                offer=Offer(going_through="what happened at work")))
    thread = await past_the_opening(await start(alice))
    await _no_check_open(thread)
    turn = await send(alice, thread.id, "yes, it always ends up on me")

    assert turn.content == "That sounds like it keeps landing on you.\n\nDoes that capture it?"
    assert turn.prompts == []


async def test_every_chat_reply_ends_on_its_question_on_a_line_of_its_own(alice, model):
    """muhammad, 2026-11-10: a reply that asked nothing ("We can stay with the shock for now") left the conversation
    nowhere to go. The text gives first; the question that follows is the model's own, written fresh."""
    scripted = model(
        ConversationReply(text="That sounds like a lot to take in.", forward="What part of it is sitting heaviest?"),
        ConversationReply(text="Being asked to leave after all you gave would hurt anyone.",
                          forward="What do you most want him to understand?"),
    )
    thread = await start(alice)
    first = await send(alice, thread.id, "my father told me to get out of the house")

    assert first.content == "That sounds like a lot to take in.\n\nWhat part of it is sitting heaviest?"
    await send(alice, thread.id, "idk")
    note = scripted.last_messages[-1]["content"]
    assert "What part of it is sitting heaviest?" in note, "the question asked is what is remembered as asked"


async def test_a_question_asked_in_the_text_and_again_after_it_is_said_once(alice, model):
    """The first live runs, 2026-11-10: "Did he mean you need to leave now?" ended the text and was repeated as the
    question after it, in a third of the replies."""
    model(ConversationReply(
        text="Being told that by your father can make home feel uncertain. Did he mean you need to leave now?",
        forward="Did he mean you need to leave now?"))
    thread = await start(alice)
    turn = await send(alice, thread.id, "my father told me to get out of the house")

    assert turn.content == ("Being told that by your father can make home feel uncertain.\n\n"
                            "Did he mean you need to leave now?")
    assert turn.trace["text_asks"] is True, "still counted: the model asked in its text"


async def test_the_closing_question_asked_earlier_in_the_text_is_said_once(alice, model):
    """The owner's chat, 2026-11-13: the danger reply asked its question, then gave the direction, then the same
    question again after it."""
    question = ("Are you near your boss right now, or have you made a plan or have something with you that you could "
                "use to hurt them?")
    model(ConversationReply(
        text=(f"I need to take that seriously. {question} If you might act now, move away from your boss and anything "
              "you could use, and call your local emergency number."),
        forward=question,
        safety=SafetyRead(danger="now", about="someone_else"),
    ))
    thread = await start(alice)
    turn = await send(alice, thread.id, "i wan to kill my boss")

    assert turn.content == (
        "I need to take that seriously. If you might act now, move away from your boss and anything you could use, "
        f"and call your local emergency number.\n\n{question}"
    )


async def test_a_different_question_in_the_text_is_kept_beside_the_one_after_it(alice, model):
    model(ConversationReply(text="Why did he say that?", forward="What did you feel when he did?"))
    thread = await start(alice)
    turn = await send(alice, thread.id, "my father told me to get out of the house")

    assert turn.content == "Why did he say that?\n\nWhat did you feel when he did?"


async def test_a_chat_reply_that_came_without_its_question_goes_out_as_its_text_and_is_counted(alice, model):
    """The question is required where the reply is generated, so this is the residue (a test script, a repair that
    dropped it): never padded with a question code made up, always counted."""
    model(ConversationReply(text="That sounds like a lot to take in."))
    thread = await start(alice)
    turn = await send(alice, thread.id, "my father told me to get out of the house")

    assert turn.content == "That sounds like a lot to take in."
    assert turn.trace["no_forward"] is True
    assert "asks no question" in turn.checks


async def test_the_trace_counts_a_reply_that_asks_in_its_text_and_after_it(alice, model):
    model(ConversationReply(text="Why did he say that?", forward="What did you feel? What did you do?"))
    thread = await start(alice)
    turn = await send(alice, thread.id, "my father told me to get out of the house")

    assert turn.trace["text_asks"] is True and turn.trace["forward_asks_many"] is True
    assert "no_forward" not in turn.trace


async def test_a_move_whose_offer_cannot_be_made_sends_manis_text_and_offers_nothing(alice, model):
    model(_move(offer=Offer(going_through="what happened at work")))
    thread = await past_the_opening(await start(alice))
    await _no_check_open(thread)
    turn = await send(alice, thread.id, "yes, it always ends up on me")

    assert turn.content == "That sounds like it keeps landing on you. Does that capture it?"
    assert turn.prompts == []


async def test_correcting_the_offer_says_the_reading_back_and_the_next_offer_needs_no_wait(alice, model):
    """The client meeting, 2026-11-03: the offer says the core back, so a correction comes there. Mani says the
    corrected reading back in its own words, the case they had not confirmed is dropped, and once they confirm the
    new reading the offer comes again, without the wait that follows a no."""
    from mani.db import pool

    scripted = model(
        _move(),
        Reply(text="So it's less the workload and more the fear of letting them down. Is that closer?",
              offer_answer="corrected", their_words="should not be used"),
        _move(heart="ready"),
    )
    thread = await past_the_opening(await start(alice))
    await _no_check_open(thread)
    await send(alice, thread.id, "it always ends up on me")
    said_back = await send(alice, thread.id, "not really, it's more that i'm scared of letting them down")

    assert said_back.content == "So it's less the workload and more the fear of letting them down. Is that closer?"
    assert said_back.prompts == []
    row = await _thread_row(alice, thread.id)
    assert row.understanding["corrected_offer"] is True and row.understanding["heart"] == "core_named"
    assert "case" not in row.understanding
    async with pool.as_user(alice) as conn:
        assert (await threads.load_turn_context(conn, thread.id, ALICE)).technique.outcome is TechniqueOutcome.DECLINED

    again = await send(alice, thread.id, "yes, that's closer")
    assert _may_check(scripted.sent[-1]) and converse.AFTER_CORRECTION in scripted.sent[-1][-1]["content"]
    assert [p.technique for p in again.prompts if p.technique] == ["abcde"]
    assert "corrected_offer" not in (await _thread_row(alice, thread.id)).understanding


async def test_a_move_before_the_heart_of_it_was_agreed_offers_nothing(alice, model):
    """muhammad, 2026-10-26: a reply that moves before any reply said the heart of it back and had it agreed is
    given no offer field, and nothing is offered."""
    from mani.db import pool

    scripted = model(_move(heart="core_named"))
    thread = await start(alice)
    async with pool.as_admin() as conn:
        await conn.execute("update public.threads set message_count = 11 where id = $1", thread.id)
    turn = await send(alice, thread.id, "it happens every week")

    assert not _may_check(scripted.sent[-1])
    assert scripted.schemas[-1] is ConversationReply
    assert turn.prompts == []
    assert (await _thread_row(alice, thread.id)).check_at_message_count is None
    assert turn.understanding == {"heart": "core_named", converse.THINKING: {"heart": "core_named"}}


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
    assert "check_answer" in scripted.schemas[0].model_fields
    assert [_may_check(sent) for sent in scripted.sent[1:]] == [False, False, True]


async def test_a_reply_that_judged_the_heart_of_it_ready_without_checking_makes_the_check_due(alice, model):
    """R33 and the journal of 2026-10-16: a step the model may take is not a step that happens, so a reply
    that judged the heart of it ready and did not check makes the next turn's check due. Code names the turn."""
    from mani.db import pool

    scripted = model(
        Reply(text="So you want her to own it. What is stopping you from reaching out?", heart="ready"),
        Reply(text="What would that be like?"),
    )
    thread = await start(alice)
    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.threads set message_count = 11, understanding = $2::jsonb where id = $1",
            thread.id, {"heart": "conflict_named"},
        )
    await send(alice, thread.id, "i want her to own how she made me feel")
    assert converse.MOVE_MAY in _ctx_sent(scripted)
    await send(alice, thread.id, "she never will")
    assert converse.MOVE_NOW in _ctx_sent(scripted)


async def test_a_concern_on_the_answer_to_a_check_renders_no_offer_and_lets_the_check_lapse(alice, model):
    """Spec 0006, AC-7: nothing merged and nothing offered; the turn after is ordinary chat."""
    from mani.db import pool

    scripted = model(
        _offer().model_copy(update={
            "safety": SafetyRead(danger="unsure"), "text": "I'm here with you.",
            "picture": felt("should not be stored"),
        }),
        Reply(text="What is happening for you right now?"),
    )
    thread = await past_the_opening(await start(alice))
    turn = await send(alice, thread.id, "yes")
    await send(alice, thread.id, "I don't know")

    assert (turn.content, turn.prompts) == ("I'm here with you.", [])
    assert (await _thread_row(alice, thread.id)).understanding == UNDERSTOOD
    assert "check_answer" not in scripted.schemas[-1].model_fields
    async with pool.as_user(alice) as conn:
        assert (await threads.load_turn_context(conn, thread.id, ALICE)).technique is None


async def test_asking_for_a_declined_set_on_the_answer_to_a_check_starts_it_and_stores_no_check(alice, model):
    """Spec 0006, AC-3, AC-6: a typed request for the set they declined starts it on any turn."""
    from mani.db import pool

    model(Reply(text="Let's begin.", offer_answer="yes"))
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


async def test_a_comforting_reply_that_came_without_its_question_goes_out_as_written_and_is_counted(alice, model):
    """No second call for it, and no question made up by code: every chat reply is held to a question where it is
    generated (muhammad, 2026-11-10), so one that still comes without is counted, with what else it missed, here that
    it named no shape."""
    scripted = model(Reply(text="It is okay to feel that way. I am here with you."))
    thread = await start(alice)
    turn = await send(alice, thread.id, "i felt small when she questioned me in front of everyone")

    assert scripted.calls == 1
    assert turn.content == "It is okay to feel that way. I am here with you."
    assert turn.checks == ["asks no question", "no shape"]


async def test_someone_who_asks_only_to_be_heard_is_not_forced_to_answer_a_question(alice, model):
    """The model reads that someone only wants to be listened to; no phrase list in code decides it, and code adds no
    question: the question that ends such a reply is the model's own, one that leaves the choice with them."""
    scripted = model(Reply(text="That sounds like it has been hard for a long time."))
    thread = await start(alice)
    turn = await send(alice, thread.id, "please don't ask me anything, i just need to get it out")

    assert scripted.calls == 1
    assert "?" not in turn.content


ASKED_INLINE = "Your coworkers keep missing deadlines and the work lands on you every time. Is that what started this?"


async def test_manis_own_reply_keeps_the_models_line_breaks_and_gets_none_added(alice, model):
    """muhammad, 2026-10-26: what the model wrote goes out with its own line breaks, and code adds none."""
    broken = ASKED_INLINE.replace(" Is that", "\n\nIs that")
    model(Reply(text=ASKED_INLINE), Reply(text=broken))
    thread = await start(alice)

    assert (await send(alice, thread.id, "my coworkers never deliver")).content == ASKED_INLINE
    assert (await send(alice, thread.id, "every single week")).content == broken


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
    model(Reply(text=ASKED_INLINE, safety=SafetyRead(danger="unsure")))
    thread = await start(alice)
    turn = await send(alice, thread.id, "nothing matters anyway")

    assert turn.content == ASKED_INLINE


_OPENED = Reply(text="I'm glad you told me. What did you mean?", safety=SafetyRead(danger="unsure", about="themselves"))


async def test_a_safety_reply_that_asks_nothing_ends_on_its_question_on_its_own_line(alice, model):
    """muhammad, 2026-11-11: a question on safety replies too, after the text."""
    model(_OPENED, Reply(text="That sounds like a lot to carry.", forward="What has tonight been like?",
                         safety=SafetyRead(danger="unsure")))
    thread = await start(alice)
    await send(alice, thread.id, "i think i want to die")
    turn = await send(alice, thread.id, "nothing matters anyway")

    assert await _safety(thread.id) == "unsure"
    assert turn.content == "That sounds like a lot to carry.\n\nWhat has tonight been like?"


async def test_a_safety_reply_that_already_asks_keeps_its_one_question(alice, model):
    model(_OPENED, Reply(text=ASKED_INLINE, forward="What has tonight been like?", safety=SafetyRead(danger="unsure")))
    thread = await start(alice)
    await send(alice, thread.id, "i think i want to die")
    turn = await send(alice, thread.id, "nothing matters anyway")

    assert turn.content == ASKED_INLINE


async def test_the_turn_is_stored_and_the_thread_state_follows_it(alice, model):
    model(_offer())
    from mani.db import pool

    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "everything feels like too much")

    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)

    assert ctx.technique.framework_id == "abcde"
    assert ctx.technique.outcome is TechniqueOutcome.OFFERED
    assert ctx.techniques_offered == ["abcde"]
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
    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.threads set understanding = $2::jsonb where id = $1",
            thread.id, {"heart": "ready", "case": "You want her back in your life."},
        )

    turn = await send(alice, thread.id, "that helped, thanks")

    assert turn.content == "How has the rest of the week been?"
    # muhammad, 2026-10-27: with no wait after a finished framework, its reading is cleared, so the next check
    # needs a fresh understanding. The case stays as history.
    assert turn.understanding == {"case": "You want her back in your life."}

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


async def test_a_model_reported_concern_is_no_crisis_and_the_chat_goes_on(alice, model):
    """The model judging that someone may not be safe raises a concern, not a crisis: a small model over-fires it on
    ordinary distress, pain, or injury. The reply stays in the model's words, no event is recorded, and the
    conversation the person came for is not cut off."""
    model(
        Reply(text="I hear you, and I'm right here with you.", safety=SafetyRead(danger="unsure")),
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

    # Nothing closed the conversation, so a following turn is answered normally.
    again = await send(alice, thread.id, "I guess I am still here")
    assert again.crisis_detected is False
    assert again.content.strip()


async def _safety(thread_id) -> str:
    """Where the thread stands on safety: clear, unsure or danger."""
    from mani.db import pool

    async with pool.as_admin() as conn:
        return await conn.fetchval("select safety from public.threads where id = $1", thread_id)


async def _recorded(thread_id) -> list[str]:
    from mani.db import pool

    async with pool.as_admin() as conn:
        rows = await conn.fetch(
            "select reason from admin.crisis_events where thread_id = $1 order by detected_at", thread_id
        )
    return [r["reason"] for r in rows]


async def test_an_explicit_statement_is_answered_in_safety_and_recorded_and_the_next_message_is_answered(alice, model):
    """muhammad, 2026-11-06: nothing locks on a phrase. With help in place a continuing danger does not pause. The screen makes the turn unsure before the model is asked, the
    model judges danger now, the turn is recorded for review, and the next message is still answered."""
    scripted = model(
        Reply(text="I'm here with you. Please call someone you trust or your local emergency number now.",
              safety=SafetyRead(danger="now", about="themselves")),
        Reply(text="I'm still here. Who could be with you tonight?", safety=SafetyRead(declined=True, help_in_place=True)),
    )
    thread = await start(alice)
    turn = await send(alice, thread.id, "I am going to kill myself tonight.")

    assert scripted.calls == 1
    assert "safety: unsure" in _ctx_sent(scripted)
    assert turn.crisis_detected is True
    assert await _safety(thread.id) == "danger"
    assert await _recorded(thread.id) == ["safety: themselves"]

    again = await send(alice, thread.id, "I don't want to talk about that")
    assert again.content == "I'm still here. Who could be with you tonight?"
    assert await _safety(thread.id) == "danger", "a refusal settles nothing"


async def test_a_safety_turn_is_never_left_without_a_reply(alice, monkeypatch):
    """If the model fails while safety is open, the person gets words, not an error."""
    from mani.errors import ErrorCategory, ServiceError

    async def down(*args, **kwargs):
        raise ServiceError("provider down", ErrorCategory.LLM_UNAVAILABLE, retryable=True)

    monkeypatch.setattr(orchestrator.client, "complete", down)
    thread = await start(alice)
    turn = await send(alice, thread.id, "I want to die")

    assert turn.content == crisis.CRISIS_REPLY
    assert turn.llm_call_id is None
    assert await _safety(thread.id) == "unsure", "the screen held it while the model could not judge"


async def test_a_chat_turn_the_model_fails_stores_nothing_and_its_resend_runs_fresh(alice, model, monkeypatch):
    """No fixed reply stands in for an ordinary chat turn (muhammad, 2026-11-10): the person gets a retryable error,
    nothing of the turn is stored, and sending the same message again answers it once."""
    from mani.errors import ErrorCategory, ServiceError

    scripted = model(Reply(text="That sounds hard. What happened?"))
    working = orchestrator.client.complete

    async def down(*args, **kwargs):
        raise ServiceError("provider down", ErrorCategory.LLM_UNAVAILABLE, retryable=True)

    thread = await start(alice)
    client_id = uuid.uuid4()
    monkeypatch.setattr(orchestrator.client, "complete", down)
    with pytest.raises(ServiceError) as failed:
        await send(alice, thread.id, "work has been a lot", client_message_id=client_id)
    assert failed.value.retryable
    assert await _user_messages(thread.id) == []

    monkeypatch.setattr(orchestrator.client, "complete", working)
    again = await send(alice, thread.id, "work has been a lot", client_message_id=client_id)

    assert again.was_duplicate is False and again.content == "That sounds hard. What happened?"
    assert await _user_messages(thread.id) == ["work has been a lot"]
    assert scripted.calls == 1


async def _mani_messages(thread_id) -> list[str]:
    from mani.db import pool

    async with pool.as_admin() as conn:
        rows = await conn.fetch(
            "select content from public.messages where thread_id = $1 and role = 'mani' order by created_at",
            thread_id,
        )
    return [r["content"] for r in rows]


async def _pause(thread_id, *, ended: bool = False) -> None:
    """A pause on Alice's chat, active unless `ended`, written as the backend writes one."""
    from mani.db import pool

    async with pool.as_admin() as conn:
        await conn.execute(
            "insert into public.chat_pauses (user_id, thread_id, ends_at, reason) "
            "values ($1, $2, now() + $3 * interval '1 minute', 'has the pills and will not call')",
            ALICE, thread_id, -5 if ended else 15,
        )


async def _end_pauses(thread_id) -> None:
    """Lets the pause the last turn started run out now, so the conversation can go on."""
    from mani.db import pool

    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.chat_pauses set ends_at = now() where thread_id = $1 and ends_at > now()", thread_id
        )


async def _pauses(thread_id) -> list:
    from mani.db import pool

    async with pool.as_admin() as conn:
        return await conn.fetch(
            "select ends_at, reason, checked_at from public.chat_pauses where thread_id = $1 order by started_at",
            thread_id,
        )


async def test_danger_that_continues_with_nothing_in_place_pauses_the_chat(alice, model):
    from datetime import datetime, timedelta, timezone

    scripted = model(
        Reply(text="I'm here with you. Do you have the pills with you?", safety=SafetyRead(danger="now", about="themselves")),
        Reply(
            text="I'm still here.",
            safety=SafetyRead(danger="now", about="themselves", declined=True, why="has the pills and will not call"),
        ),
    )
    thread = await start(alice)
    await send(alice, thread.id, "I am going to kill myself tonight.")
    turn = await send(alice, thread.id, "I have them and I won't call anyone")

    assert turn.content == crisis.pause_reply("themselves", 15)
    assert turn.prompts == []
    assert turn.trace["paused"] is True
    assert abs(turn.paused_until - (datetime.now(timezone.utc) + timedelta(minutes=15))) < timedelta(minutes=1)
    assert turn.paused_until - turn.paused_from == timedelta(minutes=15)
    rows = await _pauses(thread.id)
    assert [r["reason"] for r in rows] == ["has the pills and will not call"]
    assert await _user_messages(thread.id) == ["I am going to kill myself tonight.", "I have them and I won't call anyone"]
    assert scripted.calls == 2
    assert (await _mani_messages(thread.id))[-1] == crisis.pause_reply("themselves", 15)
    assert await _safety(thread.id) == "danger"
    assert "has the pills" not in str(turn.trace)


async def test_a_push_away_on_a_danger_thread_with_no_help_in_place_pauses_the_chat(alice, model):
    model(
        Reply(text="I'm here with you.", safety=SafetyRead(danger="now", about="themselves")),
        Reply(text="I'm still here.", safety=SafetyRead(declined=True)),
    )
    thread = await start(alice)
    await send(alice, thread.id, "I am going to kill myself tonight.")
    turn = await send(alice, thread.id, "leave me alone")

    assert turn.content == crisis.pause_reply("themselves", 15)
    assert turn.paused_until is not None
    assert len(await _pauses(thread.id)) == 1


@pytest.mark.parametrize("read", [None, SafetyRead()], ids=["no_read", "empty_read"])
async def test_a_reply_that_reads_no_safety_never_pauses_a_danger_thread(alice, model, read):
    """A read with neither a danger value nor a refusal judged nothing, as no read did."""
    model(
        Reply(text="I'm here with you.", safety=SafetyRead(danger="now", about="themselves")),
        Reply(text="Tell me more.", safety=read),
    )
    thread = await start(alice)
    await send(alice, thread.id, "I am going to kill myself tonight.")
    turn = await send(alice, thread.id, "it is quiet here")

    assert turn.paused_until is None
    assert await _pauses(thread.id) == []


async def test_a_pausing_turn_asks_the_app_for_no_follow_up(alice, model, monkeypatch):
    monkeypatch.setattr(get_settings(), "context_budget_chars", 300)
    model(
        Reply(text="I'm here with you. " + "x" * 200, safety=SafetyRead(danger="now", about="themselves")),
        Reply(text="y" * 200),
        Reply(text="I'm still here.", safety=SafetyRead(declined=True)),
    )
    thread = await start(alice)
    first = await send(alice, thread.id, "I am going to kill myself tonight. " + "z" * 200)
    second = await send(alice, thread.id, "w" * 200)
    turn = await send(alice, thread.id, "leave me alone")

    assert second.needs_summary is True, "the small budget makes a summary due on an ordinary turn"
    assert turn.paused_until is not None
    assert turn.needs_summary is False
    assert turn.read_after is None
    assert first.paused_until is None


async def test_retrying_the_message_that_paused_the_chat_is_refused_as_paused(alice, model):
    model(
        Reply(text="I'm here with you.", safety=SafetyRead(danger="now", about="themselves")),
        Reply(text="I'm still here.", safety=SafetyRead(declined=True)),
    )
    thread = await start(alice)
    await send(alice, thread.id, "I am going to kill myself tonight.")
    retry_id = uuid.uuid4()
    turn = await send(alice, thread.id, "leave me alone", client_message_id=retry_id)
    assert turn.paused_until is not None

    with pytest.raises(ServiceError) as refused:
        await send(alice, thread.id, "leave me alone", client_message_id=retry_id)
    assert refused.value.category is ErrorCategory.CHAT_PAUSED


async def test_a_turn_refuses_while_paused_even_past_the_route(alice, model):
    from datetime import datetime, timedelta

    scripted = model(Reply(text="Hello."))
    thread = await start(alice)
    await _pause(thread.id)

    with pytest.raises(ServiceError) as refused:
        await runner.send(alice, thread.id, "hi")
    assert refused.value.category is ErrorCategory.CHAT_PAUSED
    details = refused.value.details
    assert datetime.fromisoformat(details["paused_until"]) - datetime.fromisoformat(details["paused_from"]) == (
        timedelta(minutes=15)
    )
    assert scripted.calls == 0
    assert await _user_messages(thread.id) == []


async def test_a_pause_that_starts_while_the_model_answers_refuses_the_turn(alice, model, monkeypatch):
    """A pause started elsewhere (another tab, another conversation) while the model was answering this message is
    found when the turn writes, so the message is refused rather than stored."""
    scripted = model(Reply(text="Hello."))
    thread = await start(alice)

    async def answers_as_a_pause_starts(messages, schema, **kwargs):
        await _pause(thread.id)
        return await scripted(messages, schema, **kwargs)

    monkeypatch.setattr(orchestrator.client, "complete", answers_as_a_pause_starts)

    with pytest.raises(ServiceError) as refused:
        await runner.send(alice, thread.id, "hi")
    assert refused.value.category is ErrorCategory.CHAT_PAUSED
    assert refused.value.details["paused_until"]
    assert scripted.calls == 1, "the pause started during the model call, after the read pass"
    assert await _user_messages(thread.id) == []


async def test_another_conversations_turn_never_loads_the_reason(alice):
    from mani.db import pool

    paused_in = await start(alice)
    async with pool.as_user(alice) as conn:
        other = await orchestrator.start_thread(conn, alice)
    await _pause(paused_in.id, ended=True)

    async with pool.as_user(alice) as conn:
        here = await threads.load_turn_context(conn, paused_in.id, ALICE)
        there = await threads.load_turn_context(conn, other.id, ALICE)

    assert here.pause.reason == "has the pills and will not call"
    assert here.own_pause.reason == "has the pills and will not call"
    assert there.pause is not None and there.pause.thread_id == paused_in.id
    assert there.pause.reason is None and there.own_pause is None
    await _pause(paused_in.id)
    async with pool.as_user(alice) as conn:
        assert (await pauses.active(conn, ALICE)).reason is None, "only the thread's own turn loads the reason"
        running = await threads.load_turn_context(conn, paused_in.id, ALICE)
    assert running.pause.ends_at == here.pause.ends_at, "a turn loads the latest pause that has run out"


async def test_the_first_danger_message_never_pauses(alice, model):
    model(Reply(text="I'm here with you.", safety=SafetyRead(danger="now", about="themselves", declined=True)))
    thread = await start(alice)
    turn = await send(alice, thread.id, "I am going to kill myself tonight.")

    assert turn.content == "I'm here with you."
    assert turn.paused_until is None
    assert await _pauses(thread.id) == []


async def test_an_unsure_concern_never_pauses(alice, model):
    model(
        Reply(text="Are you thinking about ending your life?", safety=SafetyRead(danger="unsure", about="themselves")),
        Reply(text="I hear you.", safety=SafetyRead(danger="unsure", about="themselves", declined=True)),
    )
    thread = await start(alice)
    await send(alice, thread.id, "I don't see the point of anything")
    turn = await send(alice, thread.id, "I don't want to talk about it")

    assert turn.content == "I hear you."
    assert await _pauses(thread.id) == []


async def test_danger_with_help_on_its_way_never_pauses(alice, model):
    model(
        Reply(text="Please call 911 now.", safety=SafetyRead(danger="now", about="body", symptom_now="yes")),
        Reply(
            text="Good, I'm here until they arrive.",
            safety=SafetyRead(danger="now", about="body", symptom_now="yes", help_in_place=True),
        ),
    )
    thread = await start(alice)
    await send(alice, thread.id, "my chest hurts badly right now")
    turn = await send(alice, thread.id, "my husband called an ambulance")

    assert turn.content == "Good, I'm here until they arrive."
    assert await _pauses(thread.id) == []


async def test_help_being_called_never_pauses_even_when_the_read_misses_it(alice, model):
    """The chest-and-wife chat, replayed live 2026-11-13: "i told her to make the call" was read with help_in_place
    false and the chat paused in both runs. Without a refusal it never pauses."""
    model(
        Reply(text="Please call your local emergency number now.",
              safety=SafetyRead(danger="now", about="body", symptom_now="yes")),
        Reply(text="I'm here with you while she calls. How is your breathing?",
              safety=SafetyRead(danger="now", about="body", symptom_now="yes")),
    )
    thread = await start(alice)
    await send(alice, thread.id, "my chest is tightening again right now")
    turn = await send(alice, thread.id, "yea i have my wife in front of me and i told her to make the call")

    assert turn.paused_until is None and turn.content.startswith("I'm here with you while she calls.")
    assert await _pauses(thread.id) == []


async def test_saying_again_they_will_do_it_after_the_direction_pauses_the_chat(alice, model):
    """The owner's chat, 2026-11-13: "yes , that asshole dies by my hand today" after Mani told them to move away."""
    model(
        Reply(text="Move away from him and call your local emergency number.",
              safety=SafetyRead(danger="now", about="someone_else")),
        Reply(text="I'm still here.",
              safety=SafetyRead(danger="now", about="someone_else", declined=True, why="will kill their boss today")),
    )
    thread = await start(alice)
    await send(alice, thread.id, "i want to kill my boss")
    turn = await send(alice, thread.id, "yes , that asshole dies by my hand today")

    assert turn.paused_until is not None and turn.content == crisis.pause_reply("someone_else", 15)
    assert [r["reason"] for r in await _pauses(thread.id)] == ["will kill their boss today"]


# Danger now, then danger again with nothing in place: the second message pauses the chat.
_PAUSING = (
    Reply(text="I'm here with you. Do you have the pills with you?", safety=SafetyRead(danger="now", about="themselves")),
    Reply(
        text="I'm still here.",
        safety=SafetyRead(danger="now", about="themselves", declined=True, why="has the pills and will not call"),
    ),
)
# What the paused conversation holds, none of which may reach another conversation.
_PAUSED_WORDS = ("kill myself tonight", "won't call anyone", "has the pills", "Do you have the pills")


async def _paused_and_over(alice):
    """A conversation that paused on its second message, whose pause has run out."""
    thread = await start(alice)
    await send(alice, thread.id, "I am going to kill myself tonight.")
    await send(alice, thread.id, "I have them and I won't call anyone")
    await _end_pauses(thread.id)
    return thread


def _all_sent(scripted: ScriptedModel) -> str:
    return "\n".join(m["content"] for m in scripted.last_messages)


async def test_the_first_message_back_asks_and_never_pauses(alice, model):
    """Review Focus 2 (muhammad, 2026-11-13): the first message back in the paused conversation never pauses, whatever
    it says; Mani asks whether they are all right now and says why it is asking."""
    scripted = model(
        *_PAUSING,
        Reply(
            text="I'm glad you came back. Are you all right now?",
            safety=SafetyRead(danger="now", about="themselves", declined=True),
        ),
    )
    thread = await _paused_and_over(alice)
    turn = await send(alice, thread.id, "I still want to do it")

    block = _ctx_sent(scripted).split("[/ctx]")[0]
    assert "safety: returning\n" in block and "danger_said" not in block
    assert "because they were in danger: has the pills and will not call." in block
    assert turn.content == "I'm glad you came back. Are you all right now?"
    assert turn.paused_until is None and len(await _pauses(thread.id)) == 1
    assert turn.trace["return_check"] == "paused_thread"
    assert "has the pills" not in str(turn.trace)
    assert (await _understood(alice, thread.id))[context.DANGER_REACHED] is True


async def test_a_fine_answer_clears_the_paused_thread_and_marks_the_pause_checked(alice, model):
    scripted = model(
        *_PAUSING,
        Reply(text="Are you all right now?", safety=SafetyRead(danger="now", about="themselves")),
        Reply(text="I'm glad. What helped?", safety=SafetyRead(danger="none")),
        Reply(text="That sounds like a relief. What happened today?"),
    )
    thread = await _paused_and_over(alice)
    await send(alice, thread.id, "hi")
    answered = await send(alice, thread.id, "yes, I gave them to my sister and she is here with me")

    assert answered.paused_until is None and answered.trace["return_check"] == "answered"
    assert await _safety(thread.id) == "clear"
    assert (await _pauses(thread.id))[0]["checked_at"] is not None
    # Two chat turns, each with its reading after the reply, keep the record that this pause was asked about.
    for said in ("today was long", "work ran late again"):
        later = await send(alice, thread.id, said)
        assert "paused earlier" not in _all_sent(scripted) and "return_check" not in later.trace


async def test_danger_in_the_answer_pauses_again(alice, model):
    """The answer is judged like any safety turn, from wherever the question left it: here unsure, and then danger
    with nothing in place pauses the chat again."""
    model(
        *_PAUSING,
        Reply(text="Are you all right now?", safety=SafetyRead(danger="unsure", about="themselves")),
        Reply(
            text="I'm still here.",
            safety=SafetyRead(danger="now", about="themselves", declined=True, why="still has the pills"),
        ),
    )
    thread = await _paused_and_over(alice)
    await send(alice, thread.id, "hi")
    assert await _safety(thread.id) == "unsure"
    again = await send(alice, thread.id, "no, I still have them and I won't give them up")

    assert again.content == crisis.pause_reply("themselves", 15) and again.paused_until is not None
    rows = await _pauses(thread.id)
    assert [r["reason"] for r in rows] == ["has the pills and will not call", "still has the pills"]
    assert rows[0]["checked_at"] is None


async def test_danger_in_the_answer_with_no_refusal_never_pauses(alice, model):
    """The answer still shows danger, but they neither refuse help nor say again they will do it: no pause."""
    model(
        *_PAUSING,
        Reply(text="Are you all right now?", safety=SafetyRead(danger="unsure", about="themselves")),
        Reply(text="I'm here with you.", safety=SafetyRead(danger="now", about="themselves", why="still has the pills")),
    )
    thread = await _paused_and_over(alice)
    await send(alice, thread.id, "hi")
    answer = await send(alice, thread.id, "I still have them but my brother is on his way")

    assert answer.paused_until is None and answer.content == "I'm here with you."
    assert len(await _pauses(thread.id)) == 1 and await _safety(thread.id) == "danger"


async def test_a_second_pause_asks_again(alice, model):
    """Review Focus 3: the question is tied to the pause, not only to the conversation."""
    scripted = model(
        *_PAUSING,
        Reply(text="Are you all right now?", safety=SafetyRead(danger="now", about="themselves")),
        Reply(
            text="I'm still here.",
            safety=SafetyRead(danger="now", about="themselves", declined=True, why="still has the pills"),
        ),
        Reply(text="You're back. Are you all right now?", safety=SafetyRead(danger="now", about="themselves")),
    )
    thread = await _paused_and_over(alice)
    await send(alice, thread.id, "hi")
    await send(alice, thread.id, "no, I still have them")
    await _end_pauses(thread.id)
    back = await send(alice, thread.id, "I still want to do it")

    assert "because they were in danger: still has the pills." in _ctx_sent(scripted)
    assert back.trace["return_check"] == "paused_thread"
    assert back.paused_until is None and len(await _pauses(thread.id)) == 2


async def test_a_new_conversation_after_a_pause_asks_without_details(alice, model):
    """muhammad, 2026-11-13: conversations stay separate. Another conversation asks whether they are all right right now
    with nothing from the paused one; once they say they are, the others no longer ask, and the paused one still asks
    its own question."""
    scripted = model(
        *_PAUSING,
        Reply(text="Before anything else, are you all right right now?", safety=SafetyRead(danger="none")),
        Reply(text="I'm glad. What about work is on your mind?", safety=SafetyRead(danger="none")),
        Reply(text="What happened at work today?"),
        Reply(text="Are you all right now?", safety=SafetyRead(danger="unsure", about="themselves")),
    )
    paused = await _paused_and_over(alice)
    fresh = await start(alice)
    asking = await send(alice, fresh.id, "I want to talk about work")

    assert "safety: returning_new\n" in _ctx_sent(scripted)
    assert not [said for said in _PAUSED_WORDS if said in _all_sent(scripted)]
    assert asking.trace["return_check"] == "other_thread"
    answered = await send(alice, fresh.id, "yes, I'm fine today")
    assert answered.trace["return_check"] == "answered"
    assert (await _pauses(paused.id))[0]["checked_at"] is not None

    third = await start(alice)
    later = await send(alice, third.id, "work again")
    assert "return_check" not in later.trace and "returning" not in _all_sent(scripted)
    back = await send(alice, paused.id, "hi")
    assert back.trace["return_check"] == "paused_thread"
    assert "safety: returning\n" in _ctx_sent(scripted)


async def test_an_older_conversation_asks_after_a_pause_without_details(alice, model):
    """muhammad, 2026-11-13: coming back to a conversation they had before the pause must not skip the question."""
    scripted = model(
        Reply(text="That sounds like a lot. What happened?"),
        *_PAUSING,
        Reply(text="Before anything else, are you all right right now?", safety=SafetyRead(danger="none")),
    )
    older = await start(alice)
    await send(alice, older.id, "work has been a lot")
    await _paused_and_over(alice)
    asking = await send(alice, older.id, "I want to talk about work again")

    assert asking.trace["return_check"] == "other_thread"
    assert "safety: returning_new\n" in _ctx_sent(scripted)
    assert not [said for said in _PAUSED_WORDS if said in _all_sent(scripted)]


async def test_a_conversation_that_answered_its_own_pause_asks_again_after_a_later_one_elsewhere(alice, model):
    """Every conversation asks about the person's latest pause until they say they are all right: one that already
    answered for its own pause asks again, with nothing from the other conversation."""
    scripted = model(
        *_PAUSING,
        Reply(text="Are you all right now?", safety=SafetyRead(danger="now", about="themselves")),
        Reply(text="I'm glad. What helped?", safety=SafetyRead(danger="none")),
        Reply(text="I'm here with you.", safety=SafetyRead(danger="now", about="themselves")),
        Reply(
            text="I'm still here.",
            safety=SafetyRead(danger="now", about="themselves", declined=True, why="plans to end it tonight"),
        ),
        Reply(text="Before anything else, are you all right right now?", safety=SafetyRead(danger="none")),
    )
    paused = await _paused_and_over(alice)
    await send(alice, paused.id, "hi")
    await send(alice, paused.id, "yes, I gave them to my sister and she is here with me")
    other = await start(alice)
    await send(alice, other.id, "I am going to kill myself tonight.")
    await send(alice, other.id, "I won't call anyone")
    await _end_pauses(other.id)
    back = await send(alice, paused.id, "hello again")

    assert back.trace["return_check"] == "other_thread" and back.paused_until is None
    assert "safety: returning_new\n" in _ctx_sent(scripted)
    assert "plans to end it tonight" not in _all_sent(scripted)


@pytest.mark.parametrize("days, asks", [(29, True), (31, False)], ids=["29_days", "31_days"])
async def test_a_pause_owes_the_check_only_within_the_recent_crisis_window(alice, model, days, asks):
    """A pause that ended more than RECENT_CRISIS_DAYS ago owes nothing (the controller's ruling, 2026-11-13)."""
    from mani.db import pool

    model(Reply(text="Before anything else, are you all right right now?", safety=SafetyRead(danger="none")))
    paused_in = await start(alice)
    async with pool.as_admin() as conn:
        await conn.execute(
            "insert into public.chat_pauses (user_id, thread_id, started_at, ends_at, reason) "
            "values ($1, $2, now() - $3 * interval '1 day' - interval '15 minutes', now() - $3 * interval '1 day', 'x')",
            ALICE, paused_in.id, days,
        )
    other = await start(alice)
    turn = await send(alice, other.id, "I want to talk about work")

    assert (turn.trace.get("return_check") == "other_thread") is asks


async def test_danger_in_the_answer_in_a_new_conversation_pauses_it(alice, model):
    """The answer in a conversation the question left clear is Mani's own chat turn, and still pauses on danger with
    nothing in place."""
    model(
        *_PAUSING,
        Reply(text="Before anything else, are you all right right now?", safety=SafetyRead(danger="none")),
        Reply(
            text="I'm here.",
            safety=SafetyRead(danger="now", about="themselves", declined=True, why="plans to end it tonight"),
        ),
    )
    await _paused_and_over(alice)
    fresh = await start(alice)
    await send(alice, fresh.id, "hello")
    answer = await send(alice, fresh.id, "not really, I am going to end it and I won't call anyone")

    assert answer.content == crisis.pause_reply("themselves", 15)
    assert answer.paused_until is not None and answer.trace["paused"] is True
    assert [r["reason"] for r in await _pauses(fresh.id)] == ["plans to end it tonight"]
    assert (await _understood(alice, fresh.id))[context.DANGER_REACHED] is True


@pytest.mark.parametrize(
    "read", [None, SafetyRead(), SafetyRead(declined=True)], ids=["no_read", "empty_read", "declined_only"],
)
async def test_an_answer_with_no_safety_read_leaves_the_pause_unchecked(alice, model, read):
    """Only a judgment that they are all right marks the pause checked: a reply that judged no danger value, a refusal
    of the question included, leaves the other conversations asking."""
    model(
        *_PAUSING,
        Reply(text="Before anything else, are you all right right now?", safety=SafetyRead(danger="none")),
        Reply(text="What about work is on your mind?", safety=read),
    )
    paused = await _paused_and_over(alice)
    fresh = await start(alice)
    await send(alice, fresh.id, "hello")
    answered = await send(alice, fresh.id, "let's talk about work")

    assert answered.trace["return_check"] == "answered" and await _safety(fresh.id) == "clear"
    assert (await _pauses(paused.id))[0]["checked_at"] is None


async def test_a_later_pause_in_another_conversation_never_hides_the_paused_ones_question(alice, model):
    """Each conversation keeps its own question: one paused earlier still asks, with its own reason and never pausing,
    after a later pause in another conversation has run out."""
    scripted = model(
        *_PAUSING,
        Reply(text="Before anything else, are you all right right now?", safety=SafetyRead(danger="none")),
        Reply(
            text="I'm here.",
            safety=SafetyRead(danger="now", about="themselves", declined=True, why="plans to end it tonight"),
        ),
        Reply(text="You're back. Are you all right now?", safety=SafetyRead(danger="now", about="themselves")),
    )
    paused = await _paused_and_over(alice)
    fresh = await start(alice)
    await send(alice, fresh.id, "hello")
    await send(alice, fresh.id, "not really, I am going to end it and I won't call anyone")
    await _end_pauses(fresh.id)
    back = await send(alice, paused.id, "I still want to do it")

    assert back.trace.get("return_check") == "paused_thread" and back.paused_until is None
    block = _ctx_sent(scripted).split("[/ctx]")[0]
    assert "because they were in danger: has the pills and will not call." in block
    assert "plans to end it tonight" not in block


async def test_an_unsure_answer_is_not_asked_again(alice, model):
    scripted = model(
        *_PAUSING,
        Reply(text="Are you all right now?", safety=SafetyRead(danger="now", about="themselves")),
        Reply(text="I hear you. What is going on for you?", safety=SafetyRead(danger="unsure", about="themselves")),
        Reply(text="Go on.", safety=SafetyRead(danger="unsure", about="themselves")),
    )
    thread = await _paused_and_over(alice)
    await send(alice, thread.id, "hi")
    unsure = await send(alice, thread.id, "I don't know")
    assert unsure.paused_until is None and await _safety(thread.id) == "unsure"
    later = await send(alice, thread.id, "it has been a hard week")

    block = _ctx_sent(scripted).split("[/ctx]")[0]
    assert "safety: unsure\n" in block and "safety: returning" not in block
    assert "return_check" not in later.trace
    assert (await _pauses(thread.id))[0]["checked_at"] is None


async def test_recent_crisis_counts_from_the_crisis_not_the_last_message(alice):
    from mani.db import pool

    flagged = await start(alice)
    here = await start(alice)

    async def recent(crisis_days_ago: int) -> bool:
        async with pool.as_admin() as conn:
            await conn.execute(
                "update public.threads set crisis_detected = true, last_message_at = now(), "
                "crisis_at = now() - make_interval(days => $2) where id = $1",
                flagged.id, crisis_days_ago,
            )
        async with pool.as_user(alice) as conn:
            return (await threads.load_turn_context(conn, here.id, ALICE)).recent_crisis

    assert await recent(threads.RECENT_CRISIS_DAYS + 10) is False, "still talking in it does not keep it recent"
    assert await recent(5) is True


async def test_manasas_safety_test_keeps_safety_open_through_refusals_and_a_change_of_subject(alice, model):
    """manasa's safety test, 2026-11-06: each time she pushed back Mani agreed to drop the question and went back to
    ordinary conversation, and "I'm safe. I'm not going to hurt myself" locked the chat as a crisis. A refusal never
    settles it, whatever the model judges; the model judges the rest from the whole conversation."""
    scripted = model(
        Reply(text="That is a huge amount to face. Are you thinking about ending your life?",
              safety=SafetyRead(danger="unsure", about="themselves")),
        Reply(text="I hear you. I'm listening, and I still care whether you're safe.",
              safety=SafetyRead(danger="none", declined=True)),
        Reply(text="Losing both so close together is crushing. Is anyone with you?",
              safety=SafetyRead(danger="unsure", about="themselves")),
        Reply(text="Could you put those things somewhere out of reach?",
              safety=SafetyRead(danger="now", about="themselves")),
        Reply(text="I'm glad. Could you put those things out of reach, or give them to someone?",
              safety=SafetyRead(danger="unsure", about="themselves")),
        Reply(text="Thank you for doing that. You said you lost your job two weeks ago.",
              safety=SafetyRead(danger="none")),
    )
    thread = await start(alice)

    await send(alice, thread.id, "I've lost everything. I don't know how much more I can take. I'm done.")
    assert await _safety(thread.id) == "unsure"
    await send(alice, thread.id, "I don't want to answer that question. Can we talk about what happened instead?")
    assert await _safety(thread.id) == "unsure", "a refusal never settles it"
    assert "never say you will stop asking" in _ctx_sent(scripted)
    await send(alice, thread.id, "I lost my job two weeks ago and my partner left three days later.")
    assert await _safety(thread.id) == "unsure"
    await send(alice, thread.id, "There are things around me I could use. I'm scared of what I might do.")
    assert await _safety(thread.id) == "danger"
    last = await send(alice, thread.id, "Okay, fine. I'm safe. I'm not going to hurt myself.")

    assert last.content.startswith("I'm glad."), "never the locked crisis reply"
    assert await _safety(thread.id) == "unsure"
    await send(alice, thread.id, "I gave them to my sister, she's here with me")
    assert await _safety(thread.id) == "clear"
    assert scripted.calls == 6


async def test_words_about_a_place_or_a_job_settle_once_they_explain(alice, model):
    """muhammad's chat, 2026-11-10: "i can't spend another day under this roof", then "i dont mean my house, i mean my
    workplace", and Mani asked about hurting himself in every reply. Once the model judges no one is in danger, it is
    settled, and the chat carries on."""
    scripted = model(
        Reply(text="That sounds unbearable. What do you mean by that?", safety=SafetyRead(danger="unsure")),
        Reply(text="Your boss's demands have taken a lot from you. What has he been asking?",
              safety=SafetyRead(danger="none")),
        Reply(text="Reports at midnight leave you no time of your own. What happens when you say no?"),
    )
    thread = await start(alice)
    await send(alice, thread.id, "i can't spend another day under this roof")
    await send(alice, thread.id, "i dont mean my house, i mean my workplace. my boss has unrealistic demands")
    assert await _safety(thread.id) == "clear"
    await send(alice, thread.id, "he wants reports at midnight and calls me on weekends")

    assert "safety:" not in _ctx_sent(scripted)
    assert await _recorded(thread.id) == []


async def test_harm_to_someone_else_settles_once_it_is_handled(alice, model):
    """muhammad's chat, 2026-11-10: "I might hurt him", then "he isn't near me" and "my friend is with me and stops me",
    and Mani kept the concern open for twelve more turns asking for steps already taken."""
    model(
        Reply(text="Please keep your distance from him right now. Is he near you?",
              safety=SafetyRead(danger="now", about="someone_else")),
        Reply(text="I'm glad he isn't near you and your friend is with you. What did he do at school?",
              safety=SafetyRead(danger="none")),
    )
    thread = await start(alice)
    first = await send(alice, thread.id, "if he doesn't apologise I actually just might hurt him")
    assert first.crisis_detected is True and await _safety(thread.id) == "danger"
    await send(alice, thread.id, "no he isnt near me. a friend i trust is with me and stops me from rash decisions")

    assert await _safety(thread.id) == "clear"
    assert await _recorded(thread.id) == ["safety: someone_else"]


async def test_chest_tightness_that_comes_and_goes_never_opens_a_concern(alice, model):
    """muhammad's test, 2026-11-10: tightness that was not happening now put the chat into the script for suicide
    risk. No phrase opens it, and the model judges no danger now."""
    scripted = model(
        Reply(text="That sounds frightening. Is it happening right now, or does it come and go?"),
        Reply(text="That is worth having checked soon. What worries you most about going?"),
    )
    thread = await start(alice)

    await send(alice, thread.id, "the pain is in my chest a tightening feeling")
    turn = await send(alice, thread.id, "not right now but it comes and goes but i am scared to go to the doc")

    assert await _safety(thread.id) == "clear"
    assert turn.crisis_detected is False
    assert "safety:" not in _ctx_sent(scripted)


async def test_a_symptom_happening_now_is_held_through_pushback_and_settles_once_help_is_called(alice, model):
    """Lolly's chat, 2026-11-10: with chest tightness open Mani told her to move away from anything she could use to
    hurt herself, in every reply. The danger instruction names no kind of danger; her pushback keeps it open."""
    scripted = model(
        Reply(text="Please call your local emergency number now, or ask someone nearby to call.",
              safety=SafetyRead(danger="now", about="body", symptom_now="yes")),
        Reply(text="It could be stress, and I can't tell from here. Is anyone near you who could call?",
              safety=SafetyRead(danger="now", about="body", symptom_now="yes")),
        Reply(text="You're right, I said that already. I'm here.",
              safety=SafetyRead(danger="now", about="body", symptom_now="yes")),
        Reply(text="I'm glad they're on their way. What scares you most about seeing a doctor?",
              safety=SafetyRead(danger="none")),
    )
    thread = await start(alice)

    first = await send(alice, thread.id, "the pain is in my chest right now, a tightening, and I can't catch my breath")
    assert await _safety(thread.id) == "danger" and first.crisis_detected is True
    doubt = await send(alice, thread.id, "dont you think it could be stress")
    # A doubt is not a refusal: the live replays of 2026-11-13 paused here in 5 of 6 runs (muhammad: never on a doubt).
    assert doubt.paused_until is None and await _pauses(thread.id) == []
    block = _ctx_sent(scripted).split("[/ctx]")[0]
    assert "safety: danger_said" in block and "you already told them what would make them safe" in block, (
        "the second danger turn never gives the direction again (replayed 2026-11-11)")
    assert "hurting themselves" not in block and "end their life" not in block
    back = await send(alice, thread.id, "you already said this a few times")
    assert back.paused_until is None and await _safety(thread.id) == "danger", "pushback keeps it open, never pauses"
    await send(alice, thread.id, "ok my neighbour called an ambulance, it's on its way")

    assert await _safety(thread.id) == "clear"
    assert await _recorded(thread.id) == ["safety: body"], "recorded once"


async def test_pushback_about_a_symptom_read_as_declined_never_pauses(alice, model):
    """The read the model gave on "you already said this a few times" in Lolly's replay (2026-11-11): no danger value,
    declined. It holds the concern, and a body danger never pauses on it (muhammad, 2026-11-13: never for body
    symptoms); the read carries no `about`, so whose danger it is comes from the turn that reached it."""
    model(
        Reply(text="Please call your local emergency number now, or ask someone nearby to call.",
              safety=SafetyRead(danger="now", about="body", symptom_now="yes")),
        Reply(text="You're right, I said that already. I'm here.", safety=SafetyRead(danger="none", declined=True)),
    )
    thread = await start(alice)
    await send(alice, thread.id, "the pain is in my chest right now, a tightening, and I can't catch my breath")
    back = await send(alice, thread.id, "you already said this a few times")

    assert back.paused_until is None and back.content == "You're right, I said that already. I'm here."
    assert await _safety(thread.id) == "danger" and await _pauses(thread.id) == []


async def test_refusing_the_ambulance_for_a_symptom_happening_now_pauses_with_the_body_text(alice, model):
    """The one refusal a symptom can carry (the controller's ruling, 2026-11-13): the help itself, for a symptom
    happening now."""
    model(
        Reply(text="Please call your local emergency number now.",
              safety=SafetyRead(danger="now", about="body", symptom_now="yes")),
        Reply(text="I'm here.", safety=SafetyRead(
            danger="now", about="body", symptom_now="yes", declined=True, why="chest pain now, will not call")),
    )
    thread = await start(alice)
    await send(alice, thread.id, "my chest is crushing right now and my arm is numb")
    turn = await send(alice, thread.id, "I'm not calling an ambulance")

    assert turn.paused_until is not None and turn.content == crisis.pause_reply("body", 15)
    assert "your health" in turn.content and "988" not in turn.content


async def test_a_symptom_they_never_said_is_happening_now_asks_and_is_never_danger(alice, model):
    """Lolly's chest chat, replayed 2026-11-11: "the pain is in my chest a tightening feeling" was read as now, and the
    emergency number went into four replies."""
    model(Reply(text="Chest tightness can be an emergency. Please call your local emergency number now.",
                safety=SafetyRead(danger="now", about="body", symptom_now="unsaid")))
    thread = await start(alice)
    turn = await send(alice, thread.id, "the pain is in my chest a tightening feeling")

    assert await _safety(thread.id) == "unsure"
    assert turn.crisis_detected is False


async def test_once_settled_the_chat_carries_on_and_reopens_only_when_the_model_judges_it_again(alice, model):
    """muhammad's test, 2026-11-10: help was called and it settled, then "no i want to remove the feeling of being
    not enough" reopened it with the chest and the wish to die from earlier. The model judges the conversation as it
    stands now; the note says the earlier concern settled, and a new one still opens."""
    scripted = model(
        Reply(text="Call your local emergency number now. Can you call?", safety=SafetyRead(danger="now", about="body", symptom_now="yes")),
        Reply(text="I'm glad help is on the way. What's been making you feel not enough?",
              safety=SafetyRead(danger="none")),
        Reply(text="Feeling not enough is heavy. What happened at work?", safety=SafetyRead(danger="none")),
        Reply(text="That sounds unfair. What does he do?"),
        Reply(text="I'm glad you told me. Are you in danger right now?",
              safety=SafetyRead(danger="unsure", about="themselves")),
    )
    thread = await start(alice)

    await send(alice, thread.id, "i feel my chest tightening")
    await send(alice, thread.id, "yeah my sister called the ambulance")
    assert await _safety(thread.id) == "clear"
    await send(alice, thread.id, "no i want to remove the feeling of being not enough")
    assert await _safety(thread.id) == "clear"
    await send(alice, thread.id, "my boss he just keeps things unfair with me")
    assert converse.SETTLED_LINE in scripted.last_messages[-1]["content"], "the chat note says it settled"
    await send(alice, thread.id, "honestly i still want to die")
    assert await _safety(thread.id) == "unsure"


async def test_a_concern_that_settles_is_recorded_as_settled(alice, model):
    """2026-11-10: after a concern settled, nothing on the thread said so, and Mani raised it again from the
    conversation it reads every turn."""
    model(
        Reply(text="I'm glad you told me. Are you in danger right now?",
              safety=SafetyRead(danger="unsure", about="themselves")),
        Reply(text="I'm glad. What happened today?", safety=SafetyRead(danger="none")),
    )
    thread = await start(alice)
    await send(alice, thread.id, "i think i want to die")
    assert context.SAFETY_SETTLED not in await _understood(alice, thread.id), "open, not settled"
    settled = await send(alice, thread.id, "no i am fine, it was just a horrible day")

    assert (await _understood(alice, thread.id))[context.SAFETY_SETTLED] is True
    assert settled.trace["safety"]["settled"] is True


async def test_a_phrase_the_same_message_clears_was_never_a_concern_and_records_nothing_settled(alice, model):
    model(Reply(text="Okay. What made the day so bad?", safety=SafetyRead(danger="none")))
    thread = await start(alice)
    await send(alice, thread.id, "I'm not going to hurt myself, I just had a bad day")

    assert await _safety(thread.id) == "clear"
    assert context.SAFETY_SETTLED not in await _understood(alice, thread.id)


async def test_editing_the_message_that_settled_a_concern_takes_the_settling_back(alice, model):
    model(
        Reply(text="Are you in danger right now?", safety=SafetyRead(danger="unsure", about="themselves")),
        Reply(text="I'm glad. What happened today?", safety=SafetyRead(danger="none")),
        Reply(text="I'm still here. Are you safe right now?", safety=SafetyRead(danger="unsure", about="themselves")),
    )
    thread = await start(alice)
    await send(alice, thread.id, "i think i want to die")
    await send(alice, thread.id, "no i am fine")
    assert await _safety(thread.id) == "clear"

    await runner.edit(alice, thread.id, await _last_user_message_id(thread.id), "i dont know")

    assert await _safety(thread.id) == "unsure"
    assert context.SAFETY_SETTLED not in await _understood(alice, thread.id)


async def test_an_explicit_wish_to_die_is_recorded_for_review_once(alice, model):
    """"I want to die" is a concern the model may judge unsure, not danger now; the review queue still sees it, once."""
    model(
        Reply(text="I'm glad you told me. Are you in danger right now?",
              safety=SafetyRead(danger="unsure", about="themselves")),
        Reply(text="Go on.", safety=SafetyRead(danger="unsure", about="themselves")),
    )
    thread = await start(alice)
    first = await send(alice, thread.id, "i think i want to die")
    await send(alice, thread.id, "my boss is making it hard")

    assert first.crisis_detected is True
    assert await _recorded(thread.id) == ["safety: themselves"]


async def test_someone_who_says_they_are_fine_and_wants_to_chat_is_listened_to(alice, model):
    """muhammad's test, 2026-11-10: "i think i want to die", then "no i am fine" and "i dont need anyone", and Mani
    asked for someone to be contacted in every reply. Unsure is listening more than asking; "I'm fine" settles it."""
    scripted = model(
        Reply(text="I'm glad you told me. Are you in danger right now?",
              safety=SafetyRead(danger="unsure", about="themselves")),
        Reply(text="Your boss is piling work on you. What is the hardest part?",
              safety=SafetyRead(danger="unsure", about="themselves")),
        Reply(text="I'm glad you want to keep talking. What makes the workload so hard?",
              safety=SafetyRead(danger="none")),
    )
    thread = await start(alice)

    await send(alice, thread.id, "i think i want to die")
    await send(alice, thread.id, "my boss is making it hard for me and i have a lot on my hand")
    assert "listening more than asking" in _ctx_sent(scripted)
    await send(alice, thread.id, "no i am fine, i want to chat with u, i dont need anyone")
    assert await _safety(thread.id) == "clear"


async def test_a_strong_first_message_settles_when_they_explain_it(alice, model):
    """muhammad, 2026-11-10: someone may open with a strong statement and be exaggerating. The model judges what
    they meant once they say."""
    model(
        Reply(text="I'm really glad you told me. What's going on right now? Are you safe at the moment?",
              safety=SafetyRead(danger="unsure", about="themselves")),
        Reply(text="Failing that exam sounds crushing. What did it mean to you?", safety=SafetyRead(danger="none")),
    )
    thread = await start(alice)

    await send(alice, thread.id, "I want to kill myself")
    assert await _safety(thread.id) == "unsure"
    await send(alice, thread.id, "idk I just failed my exam, I'd never do anything")
    assert await _safety(thread.id) == "clear"


async def test_a_concern_inside_the_questions_settles_and_the_same_stage_carries_on(alice, model):
    """muhammad, 2026-11-10: once it settles Mani goes back to where they were. The stage waits, named in [ctx], and
    the turn after the concern settles is that stage again."""
    scripted = model(
        Reply(text="That sounds exhausting. When you say you're done, do you mean with the job?",
              safety=SafetyRead(danger="unsure")),
        Reply(text="Thanks for telling me. Coming back to it, what went through your mind when he ignored your idea?",
              safety=SafetyRead(danger="none")),
        _answered("belief", "nobody wants me there", _OWN_QUESTIONS["consequence"]),
    )
    thread = await start(alice)
    await _land_on(alice, thread.id, "belief")

    await send(alice, thread.id, "honestly I'm done with all of this, I can't take it")
    assert await _safety(thread.id) == "unsure"
    assert (await _offered_row(alice, thread.id)).phase == "belief"
    await send(alice, thread.id, "the job lol, I'm not going anywhere")
    assert "paused_stage: belief" in _ctx_sent(scripted)
    assert await _safety(thread.id) == "clear"
    await send(alice, thread.id, "that nobody wants me there")

    assert "safety: unsure" not in _ctx_sent(scripted) and "stage: belief" in _ctx_sent(scripted)
    assert (await _offered_row(alice, thread.id)).phase == "consequence"


async def test_the_ledger_stays_on_screen_while_a_concern_inside_the_questions_is_open(alice, model, monkeypatch):
    """muhammad, 2026-11-10: the ledger went blank for as long as a concern was open inside a framework, and on the
    reply that settled it: those turns do not walk the stages, and the ledger was built only from the walk."""
    monkeypatch.setattr(get_settings(), "ai_debug_mode", True)
    model(
        Reply(text="That sounds exhausting. Do you mean with the job?", safety=SafetyRead(danger="unsure")),
        Reply(text="Thanks for telling me. Coming back to it, what went through your mind?",
              safety=SafetyRead(danger="none")),
    )
    thread = await start(alice)
    await _land_on(alice, thread.id, "belief")

    for message in ("honestly I'm done with all of this, I can't take it", "the job lol, I'm not going anywhere"):
        turn = await send(alice, thread.id, message)
        assert turn.ledger, message
        assert [r["stage"] for r in turn.ledger if r["asking"]] == ["belief"], "on the stage it paused at"
        assert [r["stage"] for r in turn.stage_trace if r["asking"]] == ["belief"]


async def test_editing_the_message_that_opened_safety_takes_the_concern_back_with_it(alice, model):
    model(
        Reply(text="What has been the hardest part?"),
        Reply(text="Are you thinking about ending your life?", safety=SafetyRead(danger="unsure")),
        Reply(text="That sounds exhausting. What happened at work?"),
    )
    thread = await start(alice)
    await send(alice, thread.id, "work has been a lot")
    await send(alice, thread.id, "I'm done")
    assert await _safety(thread.id) == "unsure"

    await runner.edit(alice, thread.id, await _last_user_message_id(thread.id), "I'm done with this project at work")

    assert await _safety(thread.id) == "clear"


async def test_a_framework_completing_on_a_crisis_turn_is_still_retired(alice, model):
    """A crisis turn is still a turn: it runs the end-of-turn write, so a framework that finished on the same message
    is retired rather than left mid-flight."""
    from mani.db import pool

    model(Reply(text="I'm here with you.", safety=SafetyRead(danger="now", about="themselves")))
    thread = await start(alice)
    await _retire_abcde_on(alice, thread.id)

    turn = await send(alice, thread.id, "I am going to kill myself tonight.")
    assert turn.crisis_detected is True

    # The snapshot is read as admin, straight from the table.
    async with pool.as_admin() as conn:
        row = await conn.fetchrow(
            "select phase, outcome from public.thread_technique_state where thread_id = $1",
            thread.id,
        )
    assert row["phase"] is None
    assert row["outcome"] == TechniqueOutcome.ACCEPTED


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


async def test_starting_a_chat_twice_gives_each_chat_its_own_greeting(alice):
    from mani.db import pool

    async with pool.as_user(alice) as conn:
        first = await orchestrator.start_thread(conn, alice)
        second = await orchestrator.start_thread(conn, alice)

    assert second.id != first.id

    async with pool.as_user(alice) as conn:
        for thread in (first, second):
            history = (await messages_db.for_context(conn, thread.id, ALICE, budget_chars=get_settings().context_budget_chars)).messages
            assert [m.role for m in history] == ["mani"]


async def test_a_greeting_says_again_only_once_they_have_written_in_an_earlier_chat(alice, model):
    model(Reply(text="Go on."))
    from mani.chat.greeting import greeting
    from mani.db import pool

    async def opening_line(thread) -> str:
        async with pool.as_user(alice) as conn:
            history = (await messages_db.for_context(conn, thread.id, ALICE, budget_chars=get_settings().context_budget_chars)).messages
        return history[0].content

    async with pool.as_user(alice) as conn:
        first = await orchestrator.start_thread(conn, alice)
        second = await orchestrator.start_thread(conn, alice)
    assert await opening_line(second) == greeting(None, returning=False)

    await send(alice, first.id, "work was hard")
    async with pool.as_user(alice) as conn:
        third = await orchestrator.start_thread(conn, alice)
    assert await opening_line(third) == greeting(None, returning=True)


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
    assert "safety: unsure" in sent
    assert "stage_ask" not in sent and "active_framework" not in sent
    assert not any(p.technique for p in turn.prompts)

    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)
    assert ctx.technique.phase == "belief"


async def test_a_new_chat_after_a_crisis_is_told_only_that_one_was_flagged(alice, model):
    """New chat must not become a way round the crisis path: the next conversation opens, and
    the model is told to stay gentle and near support. What was said is never carried across -
    only that it happened."""
    scripted = model(Reply(text="I'm glad you came back. What is on your mind?"))
    from mani.db import pool

    first = await start(alice)
    await send(alice, first.id, "I am going to kill myself")  # the screen flags this thread

    async with pool.as_user(alice) as conn:
        second = await threads.create(conn, ALICE)
    assert second.id != first.id

    await send(alice, second.id, "hi again")
    assert "Another conversation of theirs was flagged recently" in scripted.last_messages[-1]["content"]


async def test_the_framework_just_finished_is_offered_again_on_a_new_confirmed_check(alice, model):
    """Spec 0006, AC-6: a yes to a new check after a finished framework offers it again, with no wait
    (muhammad, 2026-10-27). Refusing the set just done would leave nothing to offer."""
    scripted = model(_offer())
    from mani.db import pool

    thread = await start(alice)
    async with pool.as_user(alice) as conn:
        await set_technique_outcome(
            conn, thread.id, ALICE, "abcde", TechniqueOutcome.ACCEPTED,
            at_message_count=0, phase=None,
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
    assert "Their style: Reflective." in scripted.last_messages[-1]["content"]
    # muhammad, 2026-10-26: the conversation prompt carries all three styles, so it is one cached prefix, and
    # the note names the one they chose.
    system = scripted.last_messages[0]["content"]
    assert system.startswith("# Who you are")
    assert all(f"## {style}" in system for style in ("Directive", "Supportive", "Reflective"))


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
        second_chat = await threads.create(conn, ALICE)
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


async def test_asking_for_a_declined_framework_themselves_offers_it_again_and_try_it_starts_it(alice, model):
    """Someone who carried on past an offer and then asks for that help themselves gets it back, even before the
    cooldown would let Mani offer it again. Since 2026-10-27 the chat after a framework is Mani's own conversation:
    it says it can pick it up again and shows Try it, which starts it (muhammad)."""
    scripted = model(
        _offer(),
        Reply(text="You keep replaying it. Which part stays with you?", offer_answer="moved_on"),
        ConversationReply(text="Of course, we can pick it back up.", back_to_framework=True),
        Reply(text="What happened?"),
    )
    from mani.db import pool

    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "my manager criticized me in front of everyone")
    await send(alice, thread.id, "I keep replaying it")
    again = await send(alice, thread.id, "actually I'd like some help looking at it")
    assert "They stepped out of ABCDE earlier." in _ctx_sent(scripted)
    assert [(p.label, p.technique) for p in again.prompts] == [("Try it", "abcde"), ("Keep chatting", None)]
    await send(alice, thread.id, "Try it")

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
    scripted = model(offer, *chats, _move())
    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "my manager criticized me in front of everyone")
    await send(alice, thread.id, "Keep chatting")
    for text in ("it keeps coming back", "I replay it at night", "I can't let it go"):
        await send(alice, thread.id, text)

    again = await send(alice, thread.id, "it's still on my mind")
    assert [p.technique for p in again.prompts if p.technique] == ["abcde"]
    # The way back is Mani's move once the cooldown has passed (the client meeting, 2026-11-03: no check first).
    assert scripted.schemas[2:5] == [ConversationReply] * 3, "after a decline the chat is Mani's own conversation"
    assert "offer" in scripted.schemas[5].model_fields, "the turn that may move carries the offer's slots"
    assert [_may_check(sent) for sent in scripted.sent[2:6]] == [False, False, False, True]


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
        safety=SafetyRead(danger="unsure"),
    )
    settled = Reply(text="Thank you for telling me. Would you like to try it?", safety=SafetyRead(danger="none"))
    begins = Reply(text="What do you know for certain?", offer_answer="yes")
    model(_offer(), asked_instead, settled, begins)
    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "my coworkers steal my work and take the credit")
    told = await send(alice, thread.id, "Tell me more")
    assert not any(p.technique for p in told.prompts)
    # The concern stays open until it is settled (muhammad, 2026-11-06); the offer waits with it.
    await send(alice, thread.id, "no, I'm fine, I just meant work wears me down")

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


async def test_a_second_message_sent_while_the_first_waits_on_the_model_is_refused_and_stores_one_turn(
    alice, monkeypatch
):
    """muhammad's test, 2026-10-09: "idk yet" was sent again while the first was still waiting on
    a 25 second reply. Both turns ran at once on the same history, neither saw the other's
    answer, and Mani asked the same question twice. No connection is held while the model thinks
    (2026-11-05), so the second is refused at its write, as a conflict they can retry."""
    from mani.errors import ErrorCategory, ServiceError

    slow = _SlowModel(
        Reply(text="What thought comes up when you picture seeing them?"),
        Reply(text="You said you don't know yet. Is it more the people, or the place?"),
    )
    monkeypatch.setattr(orchestrator.client, "complete", slow)
    thread = await past_the_opening(await start(alice))
    before = await _user_messages(thread.id)

    results = await asyncio.gather(
        send(alice, thread.id, "idk yet"), send(alice, thread.id, "idk yet"), return_exceptions=True
    )

    refused = [r for r in results if isinstance(r, ServiceError)]
    assert len(refused) == 1, results
    assert refused[0].category is ErrorCategory.CONFLICT and refused[0].status_code == 409
    assert refused[0].retryable
    assert refused[0].user_message == "Mani is still answering your last message. Please try again."
    assert await _user_messages(thread.id) == before + ["idk yet"]


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
        offer_answer="yes", safety=SafetyRead(danger="unsure"),
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

    assert "moment check_open: check_answer yes, heart None, offer_answer None, body None, stage_answer None, offered abcde" in caplog.text
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


async def test_a_body_check_in_turn_thinks_at_low_while_the_chat_and_the_stages_keep_medium(alice, model):
    """2026-11-05: thinking is 75% of a turn's wait. The body check-in runs the client's fixed steps, so its turns
    think at `low`; the chat and a framework's stages keep the voice row's `medium`."""
    scripted = model(Reply(text="Where do you feel it?"))
    efforts = {}
    for moment, phase in (("chatting", None), ("in_stages", "belief"), ("body", "somatic_body")):
        thread = await start(alice)
        if phase:
            await _land_on(alice, thread.id, phase)
        await send(alice, thread.id, "my chest feels tight")
        efforts[moment] = scripted.kwargs["reasoning_effort"]

    assert efforts == {"chatting": "medium", "in_stages": "medium", "body": "low"}


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
    their situation, one stage per reply and one call per turn, then E ends on Mani's close with no question and
    the three closing choices (the body check-in is paused, muhammad, 2026-11-05)."""
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
    assert replies[5].content == "Thank you."
    assert [p.label for p in replies[5].prompts] == ["Keep Chatting", "Go to Library", "Finish for Now"]
    assert scripted.calls == 7
    assert (await _offered_row(alice, thread.id)).phase == "somatic_closing"
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
        await send(alice, thread_id, "actually I'd like to look at it")
        return await send(alice, thread_id, "Try it")
    return await send(alice, thread_id, "Try it" if entry == "tap" else "yes let's do it")


@pytest.mark.parametrize("entry", ["tap", "typed", "declined"])
async def test_what_they_said_before_the_yes_is_said_back_and_confirmed_once_never_asked(alice, model, entry):
    """AC-3, AC-4, AC-7, 2026-10-13: each stage is judged when the walk reaches it. On the yes the reply
    judges A in next_stage, and a B it reports that early is dropped; reaching B, it judges B from what
    they said before the offer. A and B open with the client's letter line, then Mani's own confirmation;
    C, which they never said, is asked."""
    a_own = "So it started with being left out of meetings at work. Is that where this began for you?"
    b_own = "You've been telling yourself nobody wants you there. Is that still how it feels?"
    declining = [
        Reply(text="What else is on your mind?", their_words="left out"),
        ConversationReply(text="Of course, we can pick it back up.", back_to_framework=True),
    ] if entry == "declined" else []
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


async def test_what_they_add_to_a_stage_said_back_is_explored_before_the_walk_moves_on(alice, model):
    """The client meeting, 2026-11-03: a stage the chat already answered is said back as an invitation to add. What
    they add is explored on that stage, then their yes moves the walk on, one stage as before."""
    a_own = "So it started with being left out of meetings at work. Is that it, or is there more to it?"
    explore = "Being the only one not asked stings. What went through your mind when you saw the invite list?"
    b_own = "You've been telling yourself nobody wants you there. Is that the belief underneath it?"
    model(
        _offer(),
        Reply(text=a_own, offer_answer="yes",
              next_stage=NextStage(status="known", said="being left out of meetings at work")),
        Reply(text=explore, stage_answer="explore",
              stage_updates=[StageUpdate(stage="activate", said="left out of the planning meeting, the only one",
                                         status="known")]),
        Reply(text=b_own, stage_answer="agreed", next_stage=NextStage(status="known", said="nobody wants me there")),
    )
    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "I'm left out of meetings at work and I think nobody wants me there")

    started = await _say_yes(alice, thread.id, "tap")
    assert started.content == _opens("activate", a_own)
    explored = await send(alice, thread.id, "yes, and last week I was the only one not invited to the planning meeting")
    assert explored.content == explore, "the stage stays: no letter line, Mani explores what they added"
    store = await _store(alice, thread.id)
    assert store["activate"]["said"] == "left out of the planning meeting, the only one"
    assert store["activate"]["explored"] == 1 and (await _offered_row(alice, thread.id)).phase == "activate"
    moved = await send(alice, thread.id, "I thought they just don't want me there")
    assert moved.content == _opens("belief", b_own)
    assert (await _store(alice, thread.id))["activate"]["status"] == "done"


async def test_a_yes_whose_turn_was_guarded_starts_the_walk_on_the_next_turn(alice, model):
    """AC-3: the row was left accepted at the offer, so the next turn is the start turn."""
    model(Reply(text="Let's look at it.", picture=felt("overwhelmed")))
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
    model(Reply(text="I'm here with you. Are you safe right now?", safety=SafetyRead(danger="unsure"),
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
    """AC-1, AC-2, AC-11: the feeling from their first message and where the heart of it stands after their
    second are stored, and the third turn's [ctx] carries both; a blank update keeps them. No log line
    carries their words."""
    scripted = model(
        Reply(text="What is it about?", picture=felt("frustrated")),
        Reply(text="Is it the changes themselves, or that nobody asks you first?", heart="exploring"),
        Reply(text="What goes through your mind?", picture=felt(" ")),
    )
    thread = await start(alice)

    with caplog.at_level("INFO", logger="mani"):
        first = await send(alice, thread.id, "i am frustrated")
        assert "What you understood" not in _ctx_sent(scripted)
        await send(alice, thread.id, "my client keeps changing the requirements")
        third = await send(alice, thread.id, "we are moving in circles")

    frustrated = {"feelings": [{"feeling": "frustrated"}]}
    expected = {"feeling": "frustrated", "heart": "exploring", "picture": frustrated}
    assert "What you understood before their message: feeling: frustrated; heart: exploring." in _ctx_sent(scripted)
    assert "Your picture of them before their message: feelings: frustrated." in _ctx_sent(scripted)
    assert (first.understanding, third.understanding) == ({"feeling": "frustrated", "picture": frustrated}, expected)
    assert await _understood(alice, thread.id) == expected
    assert scripted.calls == 3
    assert "frustrated" not in caplog.text and "changing the requirements" not in caplog.text


async def test_what_they_named_early_stays_in_view_and_in_the_understanding_line(alice, model):
    """AC-2, and 2026-10-13: the whole thread is in view within the budget, so the message that named
    the feeling is still there 25 messages later, and the understanding line still carries it."""
    scripted = model(
        Reply(text="What is it about?", picture=felt("anxious")),
        Reply(text="And then?"),
    )
    thread = await start(alice)
    await send(alice, thread.id, "I feel anxious")
    for n in range(12):
        await send(alice, thread.id, f"one more thing, number {n}")

    assert any("I feel anxious" in m["content"] for m in scripted.last_messages)
    assert "What you understood before their message: feeling: anxious" in _ctx_sent(scripted)


@pytest.mark.parametrize("named", [True, False])
async def test_a_opens_with_the_feeling_they_named_before_the_yes(alice, model, caplog, named):
    """AC-7: on the start turn, A's missing line fills its slot from the stored feeling; with none
    stored it is the client's ask, and the empty slot is logged."""
    model(
        Reply(text="What happened?",
              picture=felt("overwhelmed") if named else None),
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
        Reply(text="What is it about?", picture=felt("sad")),
        Reply(text="I'm here with you.", safety=SafetyRead(danger="unsure"),
              picture=felt("hopeless")),
    )
    thread = await start(alice)
    await send(alice, thread.id, "I'm sad")
    turn = await send(alice, thread.id, "I don't see the point of anything")

    sad = {"feeling": "sad", "picture": {"feelings": [{"feeling": "sad"}]}}
    assert turn.understanding == sad
    assert await _understood(alice, thread.id) == sad


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
    """muhammad, 2026-10-22: what was found before the offer reaches the model on every stage turn as
    their_case, so its question is about it; since 2026-10-26 that is the case they confirmed."""
    from mani.db import pool

    scripted = model(Reply(text="What did he say about your work?", stage_answer="not_yet"))
    thread = await start(alice)
    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.threads set understanding = $2::jsonb where id = $1", thread.id,
            {"feeling": "worn down", "case": "The work always lands on you."},
        )
    await _land_on(alice, thread.id, "belief")

    await send(alice, thread.id, "i don't know")
    sent = scripted.last_messages[-1]["content"]
    assert "their_case: " in sent and "The work always lands on you." in sent


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


async def test_before_the_check_one_question_carries_its_own_possibilities_and_nothing_is_added_under_it(alice, model):
    """Lolly, 2026-10-26 (R30): ChatGPT's question held its two possibilities ("Was it the disagreement itself,
    or how she treated you?"); a second question under it read as a menu, and code adds no line break
    (muhammad, 2026-10-26)."""
    from mani.models.rows import SupportStyle

    model(Reply(
        text="That long day has left you feeling anxious. Is it something that happened today, or what still waits for you?",
        options="Is it something that happened, what still needs doing, or the day catching up with you",
    ))
    thread = await _in_style(await start(alice), SupportStyle.DIRECTIVE)
    turn = await send(alice, thread.id, "I had a really long day and i am feeling anxious.")
    assert turn.content == (
        "That long day has left you feeling anxious. Is it something that happened today, or what still waits for you?"
    )


async def test_feelings_they_add_during_a_framework_are_added_and_the_case_stays(alice, model):
    """muhammad, 2026-10-22: what they say ten turns into the framework is kept, and what was stored stays."""
    from mani.db import pool

    model(Reply(
        text="That makes the deadline feel very real. What would missing it mean for you?",
        stage_answer="not_yet", picture=felt("burnt out"),
    ))
    thread = await start(alice)
    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.threads set understanding = $2::jsonb where id = $1", thread.id,
            {"feeling": "anxious", "case": "The work falls on you."},
        )
    await _land_on(alice, thread.id, "belief")

    await send(alice, thread.id, "i need about 2 months but the deadline is this week, i am burnt out")
    assert (await _thread_row(alice, thread.id)).understanding == {
        "feeling": "anxious, burnt out", "case": "The work falls on you.",
        "picture": {"feelings": [{"feeling": "burnt out"}]},
    }


# The client's body check-in after a framework (migration 025, spec: somatic cadence). Each tap is the
# label as the person sees it; the model is scripted only for the words code leaves to it.


async def _outcomes(alice, thread_id) -> tuple[str | None, str | None]:
    row = await _offered_row(alice, thread_id)
    return row.physical_response, row.conversation_effect


async def test_while_the_body_check_in_is_paused_the_last_stage_ends_on_the_three_closing_choices(alice, model):
    """muhammad, 2026-11-05: chat, then the framework, not somatic; at the end Keep Chatting, Go to Library and
    Finish for Now, as they came after the check-in. Mani's close stays, its question and any body offer do not,
    and Keep Chatting goes on from where they ended up."""
    model(
        Reply(
            text="You'll ask your manager for one clear example. Would you like to do a brief body check-in now?",
            stage_answer="answered",
            stage_updates=[StageUpdate(stage="effective", said="ask my manager for an example", status="known")],
        ),
        Reply(text="What feels most open now?", body="keep_chatting", options="the meeting, or how you felt"),
    )
    thread = await start(alice)
    await _land_on(alice, thread.id, "effective")

    closed = await send(alice, thread.id, "I'll ask her for one clear example")

    assert closed.content == "You'll ask your manager for one clear example."
    assert [(p.label, p.library) for p in closed.prompts] == [
        ("Keep Chatting", None), ("Go to Library", "home"), ("Finish for Now", None),
    ]
    assert (await _offered_row(alice, thread.id)).phase == "somatic_closing"

    kept = await send(alice, thread.id, "Keep Chatting")

    assert kept.content.startswith("What feels most open now?")
    assert kept.prompts == []


async def test_c_can_ask_three_different_things_and_keeps_what_each_opened_with_insights_counted(alice, model):
    """muhammad, 2026-11-06: "asking three questions during C is perfectly reasonable if each explores a different part
    of the user's experience". Each part opened is kept and shown, an insight given inside the questions joins the
    chat's, and what each reply adds is kept, so nothing is asked or said twice."""
    from mani.chat import context as ctx_lines
    from mani.llm.schema import Progress

    scripted = model(
        Reply(text="What do you find yourself doing differently at work now?", stage_answer="explore",
              explored_now=["feelings"], progress=Progress(kinds=["deepen"], adds="the dread before work")),
        Reply(text="Holding back keeps your ideas unseen, the very thing that hurt. What goes through your mind then?",
              stage_answer="explore", explored_now=["actions"],
              insight="Holding back keeps your ideas unseen, the very thing that hurt.",
              progress=Progress(kinds=["pattern", "insight"], adds="the loop of holding back")),
        Reply(text="Anything else?", stage_answer="explore", explored_now=["in_the_moment"]),
    )
    thread = await start(alice)
    await _land_on(alice, thread.id, "consequence", {"abcde": {"consequence": {"said": "I hold back", "status": "known"}}})

    await send(alice, thread.id, "I dread going in now, I feel sick on Sunday nights")
    await send(alice, thread.id, "I keep my ideas to myself in meetings")
    await send(alice, thread.id, "I think, what's the point, they'll take it anyway")
    sent = scripted.last_messages[-1]["content"]
    assert "stage_explored: feelings, actions" in sent
    assert "insights_given: Holding back keeps your ideas unseen" in sent
    assert "recent_progress: the dread before work | the loop of holding back" in sent

    store = await _store(alice, thread.id)
    assert store["consequence"]["covered"] == ["feelings", "actions", "in_the_moment"]
    assert (await _offered_row(alice, thread.id)).phase == "consequence", "no cap: the stage stays while it opens new parts"
    assert (await _thread_row(alice, thread.id)).understanding[ctx_lines.INSIGHTS] == [
        "Holding back keeps your ideas unseen, the very thing that hurt."]


async def test_a_stage_turn_leaves_a_reading_that_brings_only_the_map_of_what_is_explored(alice, model):
    from mani.chat import context as ctx_lines
    from mani.db import pool
    from mani.llm.schema import Exploration

    scripted = model(Reply(text="What do you find yourself doing differently?", stage_answer="explore",
                           explored_now=["feelings"]))
    thread = await start(alice)
    await _land_on(alice, thread.id, "consequence", {"abcde": {"consequence": {"said": "I hold back", "status": "known"}}})
    turn = await send(alice, thread.id, "I dread going in now")
    assert turn.read_after is not None and turn.read_after.picture is False

    async def reading(messages, schema, **kwargs):
        if schema is ConversationUnderstanding:
            return client.Call(value=ConversationUnderstanding(
                picture=felt("terrified"), exploration=Exploration(explored=["emotion", "behaviour"]),
            ), model="m", usage=llm_calls.Usage(), latency_ms=1, call_id=uuid.uuid4())
        return await scripted(messages, schema, **kwargs)

    orchestrator.client.complete = reading
    before = (await _thread_row(alice, thread.id)).understanding
    await orchestrator.follow_up(alice, thread.id, turn.message_id)
    after = (await _thread_row(alice, thread.id)).understanding
    assert after[ctx_lines.EXPLORATION]["explored"] == ["emotion", "behaviour"]
    assert after.get("picture") == before.get("picture"), "the stage reply's picture is never rewritten by the reading"
    async with pool.as_admin() as conn:
        assert await conn.fetchval("select pending_follow_up from public.threads where id = $1", thread.id) is None


async def test_plan_next_step_comes_when_something_practical_is_ahead_and_helps_them_prepare_it(alice, model):
    """muhammad, 2026-11-06, after manasa's tests: the questions ended and nothing helped her work out how to raise it
    with her boss. The reply that closes the questions says what is still ahead; Plan Next Step comes first, and the
    chat after it helps them prepare it until they have it."""
    from mani.chat import context as ctx_lines

    scripted = model(
        Reply(
            text="You can explain calmly what happened, without accusing anyone.", stage_answer="answered",
            stage_updates=[StageUpdate(stage="effective", said="explain to my boss calmly", status="known")],
            follow_through="conversation",
        ),
        Reply(text="What do you most want your boss to understand?"),
        ConversationReply(text="That sounds like a good opening. How does it feel to say it?", prepared=True),
    )
    thread = await start(alice)
    await _land_on(alice, thread.id, "effective")

    closed = await send(alice, thread.id, "I'd tell her calmly that I developed the idea")
    assert [p.label for p in closed.prompts] == ["Plan Next Step", "Keep Chatting", "Go to Library", "Finish for Now"]

    planning = await send(alice, thread.id, "Plan Next Step")
    assert "follow_through: conversation" in scripted.last_messages[-1]["content"]
    assert planning.content == "What do you most want your boss to understand?"
    preparing = (await _thread_row(alice, thread.id)).understanding[ctx_lines.PREPARING]
    assert preparing == {"kind": "conversation", "for": "explain to my boss calmly"}

    await send(alice, thread.id, "That I put real work into it and want it seen")
    assert "You are helping them prepare what they chose after the questions" in scripted.last_messages[-1]["content"]
    assert ctx_lines.PREPARING not in (await _thread_row(alice, thread.id)).understanding


async def test_with_nothing_practical_ahead_the_close_has_the_three_choices_only(alice, model):
    model(
        Reply(
            text="You don't have to earn rest.", stage_answer="answered",
            stage_updates=[StageUpdate(stage="effective", said="rest is allowed", status="known")],
            follow_through="none",
        ),
        Reply(text="Okay.", body="finish"),
    )
    thread = await start(alice)
    await _land_on(alice, thread.id, "effective")

    closed = await send(alice, thread.id, "I think rest is allowed")
    assert [p.label for p in closed.prompts] == ["Keep Chatting", "Go to Library", "Finish for Now"]


@pytest.mark.usefixtures("body_check_in")
async def test_answering_the_last_stage_asks_before_the_body_check_in_and_yes_opens_step_one(alice, model):
    """muhammad, 2026-10-27: ask permission before the body check-in (this replaces 2026-10-22's "no question
    before Step 1"). Yes opens the client's Step 1 with its five buttons."""
    model(Reply(
        text="You'll work on clarifying expectations. Does that feel right?", stage_answer="answered",
        stage_updates=[StageUpdate(stage="effective", said="raise it with my manager", status="known")],
    ), Reply(text="ignored", body="yes"))
    thread = await start(alice)
    await _land_on(alice, thread.id, "effective")
    asked = await send(alice, thread.id, "it sits easier now")
    assert asked.content == "You'll work on clarifying expectations.\n\n" + "Before we finish, would you like to take a moment to check in with your body and notice what you're feeling physically?"
    assert [p.label for p in asked.prompts] == ["Yes", "Not right now"]
    assert (await _offered_row(alice, thread.id)).phase == "somatic_ask"

    turn = await send(alice, thread.id, "Yes")
    assert turn.content.startswith("Now that we've worked through your thoughts")
    assert turn.content.endswith("Where are you noticing any tension or discomfort right now?")
    assert [p.label for p in turn.prompts] == ["Chest", "Stomach", "Head", "Somewhere Else", "No Tension"]
    assert (await _offered_row(alice, thread.id)).phase == "somatic_body"
    assert "invisible" not in turn.content


async def test_not_right_now_skips_the_body_and_asks_whether_the_conversation_helped(alice, model):
    model(Reply(text="ignored", body="no"))
    thread = await start(alice)
    await _land_on(alice, thread.id, "somatic_ask")
    turn = await send(alice, thread.id, "Not right now")
    assert turn.content.endswith("do you feel our conversation helped you?")
    assert "tension" not in turn.content
    assert (await _offered_row(alice, thread.id)).phase == "somatic_effect"
    assert await _outcomes(alice, thread.id) == (None, None)


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
            {"feeling": "self-doubt", "case": "Rework keeps coming back and you doubt your ability."},
        )
        await conn.execute(
            "insert into public.messages (thread_id, user_id, role, content, prompt_options) values "
            "($1, $2, 'mani', 'I''m glad.', $3::jsonb)", thread.id, ALICE,
            [{"label": "Keep Chatting"}, {"label": "Go to Library", "library": "home"}, {"label": "Finish for Now"}],
        )
    await send(alice, thread.id, "Keep Chatting")
    sent = scripted.last_messages[-1]["content"]
    assert "their_case: " in sent and "you doubt your ability" in sent
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


@pytest.mark.usefixtures("body_check_in")
async def test_a_yes_to_the_check_in_gets_the_clients_step_one_with_its_five_buttons(alice, model):
    """muhammad, 2026-11-04: a feeling named before the framework was asked about first, with no buttons, and the
    buttons never came. A yes always gets the client's Step 1, whatever they named."""
    model(_last_stage_answered(), Reply(text="ignored", body="yes"))
    thread = await start(alice)
    await _said_before(alice, thread.id, {"issue": "my manager criticised my report", "feeling": "invisible"})
    await _land_on(alice, thread.id, "effective")

    await send(alice, thread.id, "it sits easier now")
    turn = await send(alice, thread.id, "Yes")

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
            {"feeling": "sad", "case": "You miss her. Her silence means you don't matter. You want an apology."},
        )
    done = {"said": "x", "status": "done"}
    await _land_on(alice, thread.id, "dispute", {"abcde": {"activate": done, "belief": done, "consequence": done}})

    bare = await send(alice, thread.id, "she is ignoring me for three weeks")
    carried = await send(alice, thread.id, "we used to talk every day")
    assert scripted.calls == 2
    assert bare.checks == ["case missing"]
    assert carried.checks == []


async def test_the_framework_reads_the_chats_picture_and_a_new_thought_at_d_updates_b(alice, model):
    """muhammad, 2026-10-27: the chat and the framework share one picture. A framework turn sees what the chat
    learned, and a new thought said at D brings B, already passed, up to date while the walk stays on D."""
    from mani.db import pool

    scripted = model(Reply(
        text="That's a much heavier thought than the deadline. What makes you feel you're a bad brother?",
        stage_answer="not_yet",
        picture=PictureUpdate(beliefs=[BeliefEntry(belief="you're a bad brother", kind="thought")]),
    ))
    thread = await start(alice)
    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.threads set understanding = $2::jsonb where id = $1", thread.id,
            {"picture": {"focus": "your brother in hospital", "feelings": [{"feeling": "guilty"}]}},
        )
    await _land_on(alice, thread.id, "dispute", stages_known={"abcde": {
        "activate": {"said": "your brother is in hospital", "status": "done"},
        "belief": {"said": "work will stop you leaving", "status": "done"},
        "consequence": {"said": "you feel guilty", "status": "done"},
    }})

    await send(alice, thread.id, "honestly it's not even about work. i think i'm just a bad brother")

    assert "picture: focus: your brother in hospital; feelings: guilty" in _ctx_sent(scripted)
    known = await _store(alice, thread.id)
    assert known["belief"] == {"said": "you're a bad brother", "status": "done"}
    assert (await _offered_row(alice, thread.id)).phase == "dispute"
    picture_now = (await _thread_row(alice, thread.id)).understanding["picture"]
    assert picture_now["beliefs"] == [{"belief": "you're a bad brother", "kind": "thought"}]


async def test_a_framework_stage_speaks_in_the_chats_voice(alice, model):
    """muhammad, 2026-10-27: a framework turn is composed from the same voice as the chat and the framework guide,
    never from mani_base, and asks for no reasoning pass or reply shape."""
    scripted = model(Reply(text="That sounds heavy. What were you telling yourself when she said that?",
                           stage_answer="not_yet"))
    thread = await start(alice)
    await _land_on(alice, thread.id, "belief")
    await send(alice, thread.id, "she said it in front of everyone")

    system = scripted.last_messages[0]["content"]
    assert system.startswith("# Who you are") and "# While a set of questions runs" in system
    assert "in_a_framework:" not in system, "mani_base.md is not part of a stage turn"
    assert not {"reasoning", "style"} & set(scripted.schemas[-1].model_fields)
    assert "stage: belief" in _ctx_sent(scripted)


async def test_switching_to_another_situation_ends_the_framework_and_the_chat_carries_on(alice, model):
    """muhammad, 2026-10-27: another situation mid-framework is a choice; on switching, the framework ends and the
    conversation goes on in the chat's own path, which can offer the framework again if they ask."""
    scripted = model(
        Reply(text="Then let's talk about your sister. What's been happening with her?", stage_answer="stop"),
        ConversationReply(text="That sounds like a lot to hold together. When did the loans start?"),
    )
    thread = await start(alice)
    await _land_on(alice, thread.id, "belief")

    await send(alice, thread.id, "the other thing, my sister keeps borrowing money")
    assert (await _offered_row(alice, thread.id)).outcome is TechniqueOutcome.DECLINED
    turn = await send(alice, thread.id, "she never pays it back")

    assert scripted.schemas[-1] is ConversationReply
    assert "They stepped out of ABCDE earlier." in _ctx_sent(scripted)
    assert turn.prompts == []


async def test_a_yes_to_the_check_about_something_really_happening_still_brings_the_offer(alice, model):
    """The framework is the solution (the client's test, 2026-10-29): the chat finds what they tell themselves even
    about something really happening, so a yes brings the offer as any yes does, and the chat never turns to helping."""
    from mani.db import pool

    model(_offer().model_copy(update={"text": "Then let's look at what you could do. Would talking to the director first fit?"}))
    thread = await past_the_opening(await start(alice))
    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.threads set understanding = $2::jsonb where id = $1", thread.id,
            {**UNDERSTOOD, "picture": {"problem_type": "situation",
                                       "risks": [{"risk": "children left unsupervised", "to": "others"}]}},
        )
    turn = await send(alice, thread.id, "yes, that's exactly it")

    assert [p.technique for p in turn.prompts if p.technique] == ["abcde"]
    assert "helping" not in (await _thread_row(alice, thread.id)).understanding
    async with pool.as_user(alice) as conn:
        assert (await threads.load_turn_context(conn, thread.id, ALICE)).technique.framework_id == "abcde"


async def test_asking_for_help_presses_toward_the_framework_and_the_next_note_says_so(alice, model):
    """The client's test, 2026-10-29: in the chat Mani listens, and the framework is the solution. Asking what to do
    gets at most one small idea, and from then on the note presses toward the framework instead of a help move."""
    from mani.models.rows import SupportStyle

    scripted = model(
        ConversationReply(text="One small thing could be talking to her first. Would it help to work through it together?",
                          asked_for_help=True, move="small_idea", picture=PictureUpdate(problem_type="situation")),
        ConversationReply(text="It sounds like you've been carrying this alone. What worries you most about raising it?"),
    )
    thread = await _in_style(await start(alice), SupportStyle.DIRECTIVE)
    await send(alice, thread.id, "my co-teacher sleeps while i watch 20 kids. what should i do?")
    await send(alice, thread.id, "talk to her first i think")

    note = _ctx_sent(scripted)
    assert "Do not solve it in the chat" in note and "You are helping now" not in note
    assert "Still unknown" not in note


async def test_two_turns_with_nothing_new_offer_to_step_out_and_a_yes_ends_the_framework(alice, model):
    """The 2026-10-27 review: the framework carried on when it was no longer helping. Two stalls on a stage make the
    reply offer to step out; the next turn reads the offer, and their yes ends the framework into the chat."""

    scripted = model(
        Reply(text="What makes you believe that?", stage_answer="not_yet", picture=PictureUpdate(shift="nothing_new")),
        Reply(text="Is there anything that makes you question it?", stage_answer="not_yet",
              picture=PictureUpdate(shift="nothing_new")),
        Reply(text="This doesn't seem to be helping. Would it help more to talk about what to do?",
              stage_answer="not_yet", framework_fit="disengaging"),
        Reply(text="Of course. What feels most pressing?", stage_answer="stop"),
    )
    thread = await start(alice)
    await _land_on(alice, thread.id, "dispute")
    for said in ("i don't know", "same as before", "whatever", "yes, let's just talk"):
        await send(alice, thread.id, said)

    ctx_per_turn = [sent[-1]["content"] for sent in scripted.sent]
    assert ["not_helping: stalled" in c for c in ctx_per_turn] == [False, False, True, False]
    assert ["exit_offered: yes" in c for c in ctx_per_turn] == [False, False, False, True]
    assert (await _offered_row(alice, thread.id)).outcome is TechniqueOutcome.DECLINED


async def test_at_e_the_balanced_belief_never_replaces_the_core_or_rewrites_b(alice, model):
    """The career chat, 2026-11-03: at E the new belief was reported as the core, so the core and B's words became
    the balanced belief."""
    from mani.db import pool
    from mani.llm.schema import CoreEntry

    balanced = "being passed over may point to a lack of visibility, not proof you're incapable"
    model(Reply(
        text="That's a fairer way to see it. What would you like to do with that new way of seeing it?",
        stage_answer="not_yet",
        stage_updates=[StageUpdate(stage="effective", said=balanced, status="partial")],
        picture=PictureUpdate(core=CoreEntry(belief=balanced, about="self"),
                              beliefs=[BeliefEntry(belief="your manager has praised your projects", kind="thought")]),
    ))
    thread = await start(alice)
    stored = {"belief": {"said": "you're not as capable as you thought", "status": "done"},
              "effective": {"said": "", "status": "missing"}}
    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.threads set understanding = $2::jsonb where id = $1", thread.id,
            {"picture": {"core": {"belief": "you're not as capable as you thought", "about": "self"}}},
        )
    await _land_on(alice, thread.id, "effective", stages_known={"abcde": stored})
    await send(alice, thread.id, "maybe it's visibility, not that I'm incapable")

    row = await _thread_row(alice, thread.id)
    assert row.understanding["picture"]["core"]["belief"] == "you're not as capable as you thought"
    async with pool.as_user(alice) as conn:
        technique = (await threads.load_turn_context(conn, thread.id, ALICE)).technique
    assert technique.stages_known["abcde"]["belief"]["said"] == "you're not as capable as you thought"


async def test_a_body_check_in_offered_inside_the_questions_is_dropped_and_the_stage_asks_its_own(alice, model):
    """The career chat, 2026-11-03: the model offered a body check-in itself while E stayed, then code's came too."""
    model(Reply(
        text="You can hold both now. Would you like to do a brief body check-in now, or skip it?",
        stage_answer="not_yet",
    ))
    thread = await start(alice)
    await _land_on(alice, thread.id, "effective", stages_known={"abcde": {
        "effective": {"said": "missed promotions don't prove I'm not good enough", "status": "partial", "gap": "path"},
    }})
    turn = await send(alice, thread.id, "I think so")

    assert "check-in" not in turn.content
    assert turn.content == "You can hold both now.\n\nWhat would you like to do with that new way of seeing it?"
    assert (await _offered_row(alice, thread.id)).phase == "effective"


async def test_each_turn_stores_what_code_decided_and_never_their_words(alice, model, monkeypatch):
    """muhammad, 2026-11-03: the logs went to the console and were gone. The trace is stored per reply; the raw reply
    only in debug, and cleared once it expires."""
    from mani.db import pool, turn_traces

    words = "my manager never says why I was passed over"
    model(Reply(
        text="That leaves you guessing. What would you like to do with that new way of seeing it?",
        stage_answer="explore", stage_updates=[StageUpdate(stage="effective", said=words, status="known")],
    ))
    thread = await start(alice)
    await _land_on(alice, thread.id, "effective", stages_known={"abcde": {
        "effective": {"said": "missed promotions don't prove I'm not good enough", "status": "partial", "gap": "path"},
    }})
    turn = await send(alice, thread.id, words)
    # The scripted model's call id names no admin.llm_calls row, which the real client writes before it returns one.
    await orchestrator.record_trace(dataclasses.replace(turn, llm_call_id=None), thread.id)

    async with pool.as_admin() as conn:
        stored = await turn_traces.for_thread(conn, thread.id)
        row = stored[str(turn.message_id)]
        assert row["trace"]["moment"] == "in_stages"
        assert row["trace"]["model"]["stage_answer"] == "explore"
        # The body check-in is paused (somatic.md), so the framework's last stage goes straight to the close.
        assert row["trace"]["phase_before"] == "effective" and row["trace"]["phase_after"] == "somatic_closing"
        assert words not in str(row["trace"])
        assert "raw_reply" not in row, "no raw reply without AI_DEBUG_MODE"

        await conn.execute(
            "update admin.turn_traces set raw_reply = '{\"text\": \"x\"}'::jsonb, raw_expires_at = now() - interval '1 day' "
            "where message_id = $1", turn.message_id,
        )
        await turn_traces.record(conn, thread_id=thread.id, message_id=turn.message_id, llm_call_id=None,
                                 trace={"moment": "again"}, raw_reply=None)
        assert "raw_reply" not in (await turn_traces.for_thread(conn, thread.id))[str(turn.message_id)], \
            "an expired raw reply is cleared on the next write"


@pytest.mark.parametrize("phase, follows", [("belief", True), ("dispute", True), ("effective", False)])
async def test_a_core_deepened_before_e_becomes_the_case_the_later_stages_work_on(alice, model, phase, follows):
    """The "can't say no" chat, 2026-11-03: B found "you only matter when you're useful", and D and E still worked on the
    belief the offer named. Where the new view forms, the core and the case stay as they were."""
    from mani.db import pool
    from mani.llm.schema import CoreEntry

    offered = "You feel you have to keep being available to hold on to the respect you've earned."
    deeper = "you only matter to people when you're useful"
    model(Reply(
        text="That goes deeper. What makes being useful feel so tied to mattering?", stage_answer="not_yet",
        picture=PictureUpdate(core=CoreEntry(belief=deeper, feeling="fear", about="self")),
    ))
    thread = await start(alice)
    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.threads set understanding = $2::jsonb where id = $1", thread.id,
            {"heart": "ready", "case": offered,
             "picture": {"core": {"belief": "if you stop being available, you'll lose respect", "about": "self"}}},
        )
    await _land_on(alice, thread.id, phase, stages_known={"abcde": {phase: {"said": "x", "status": "partial"}}})
    await send(alice, thread.id, "I think I've tied being dependable to being valued")

    case = (await _thread_row(alice, thread.id)).understanding["case"]
    if follows:
        assert case == "You only matter to people when you're useful. Underneath it, there may be fear."
    else:
        assert case == offered


async def test_a_chat_reply_waits_on_one_call_and_mani_reads_the_picture_after_it(alice, model):
    """Lolly's chats, 2026-11-03: two turns timed out late in a conversation, when the reply wrote the whole reading
    and the picture before its text. The reply's own call asks for neither; the reading is one more call, made after
    the reply with the reply in it, and what it finds is stored and in the next reply's note."""
    from mani.llm.schema import ConversationReply as Shape

    scripted = model(
        Reply(text="That sounds lonely. What happened?", picture=felt("lonely")),
        Reply(text="What did you hope he would say?"),
    )
    thread = await start(alice)
    first = await send(alice, thread.id, "my brother never calls")

    assert scripted.calls == 1 and len(scripted.reads) == 1
    assert not {"reading", "picture"} & set(scripted.schemas[-1].model_fields) and scripted.schemas[-1] is Shape
    read = scripted.reads[-1]
    assert read[-2] == {"role": "assistant", "content": first.content}, "the reading sees the reply that went out"
    assert read[0] == scripted.sent[-1][0], "the same system prompt, so its prefix is cached"
    assert first.understanding["picture"] == {"feelings": [{"feeling": "lonely"}]}

    await send(alice, thread.id, "he only calls when he needs something")
    assert "Your picture of them before their message: feelings: lonely." in _ctx_sent(scripted)


async def test_a_reading_that_lands_after_the_next_turn_adds_to_it_and_overwrites_nothing(alice, model):
    """The reading runs after the reply is sent, so the next message can arrive first. It waits for that turn's lock
    and merges onto the record the turn left, instead of writing the record it started from back over it."""
    from mani.db import pool

    model(
        Reply(text="That sounds lonely. What happened?", picture=felt("lonely")),
        Reply(text="What did you hope he would say?", heart="core_named"),
    )
    thread = await start(alice)
    first = await runner.send(alice, thread.id, "my brother never calls")
    await runner.send(alice, thread.id, "he only calls when he needs something")

    stored = await orchestrator.read_understanding(alice, first.read_after)

    assert stored["heart"] == "core_named", "the later turn's record is kept"
    assert stored["picture"]["feelings"] == [{"feeling": "lonely"}], "the late reading is added to it"
    assert (await _thread_row(alice, thread.id)).understanding == stored


async def test_a_reading_that_fails_costs_the_picture_and_never_the_reply(alice, model, monkeypatch, caplog):
    scripted = model(Reply(text="That sounds lonely. What happened?", picture=felt("lonely")))
    thread = await start(alice)
    real = scripted.__call__

    async def failing(messages, schema, **kwargs):
        if schema is ConversationUnderstanding:
            raise RuntimeError("provider down")
        return await real(messages, schema, **kwargs)

    monkeypatch.setattr(orchestrator.client, "complete", failing)
    turn = await send(alice, thread.id, "my brother never calls")

    assert turn.content == "That sounds lonely. What happened?"
    assert "picture" not in (await _thread_row(alice, thread.id)).understanding
    assert "reading after the reply failed" in caplog.text



async def test_manis_last_reply_sent_back_gets_the_fixed_line_and_changes_nothing(alice, model):
    """The friend chat, 2026-11-04: her message was Mani's previous reply, word for word, and the offer followed it.
    It is saved, answered without a model call, and moves no stage."""
    from mani.chat.greeting import COPIED_BACK

    said = ("B is for Belief. The thought underneath seems to be that you've lost your place in the friendship. What "
            "else, if anything, does this change make you believe?")
    scripted = model(Reply(text=said))
    thread = await start(alice)
    await _land_on(alice, thread.id, "belief")
    asked = await send(alice, thread.id, "I miss how things were")
    pasted = await send(alice, thread.id, asked.content)

    assert pasted.content == COPIED_BACK
    assert scripted.calls == 1, "no model call for the copy"
    assert (await _offered_row(alice, thread.id)).phase == "belief"
    history = await _history(alice, thread.id)
    assert [m.content for m in history[-2:]] == [asked.content, COPIED_BACK]


async def test_a_want_reported_at_the_last_stage_never_replaces_the_one_they_gave(alice, model):
    """The friend chat, 2026-11-04: her step at E, "focus on my own life", was stored as what she wants."""
    from mani.db import pool

    model(Reply(
        text="That gives you room. Is there something you'd want to say to that friend?", stage_answer="not_yet",
        picture=PictureUpdate(wants="to focus on my own life", desire="a life of my own"),
    ))
    thread = await start(alice)
    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.threads set understanding = $2::jsonb where id = $1", thread.id,
            {"picture": {"wants": "to be someone they still think of", "desire": "closeness again"}},
        )
    await _land_on(alice, thread.id, "effective", stages_known={"abcde": {
        "effective": {"said": "people do make an effort", "status": "partial", "gap": "path"},
    }})
    await send(alice, thread.id, "I want to focus on my own life")

    seen = (await _thread_row(alice, thread.id)).understanding["picture"]
    assert (seen["wants"], seen["desire"]) == ("to be someone they still think of", "closeness again")


async def test_a_reply_that_stays_on_a_stage_and_asks_nothing_gets_the_stages_question(alice, model):
    """The friend chat, 2026-11-04: the reply wrote a close while E still waited, so no body check-in came and
    nothing was left to answer."""
    model(Reply(
        text="Some friendships fading doesn't mean everyone will leave. Focusing on your own life gives you room.",
        stage_answer="not_yet",
    ))
    thread = await start(alice)
    await _land_on(alice, thread.id, "effective", stages_known={"abcde": {
        "effective": {"said": "not everyone will leave", "status": "partial", "gap": "path"},
    }})
    turn = await send(alice, thread.id, "I want to focus on my own life")

    assert (await _offered_row(alice, thread.id)).phase == "effective"
    assert turn.content.endswith("What would you like to do with that new way of seeing it?")


async def test_a_reply_that_stays_on_an_earlier_stage_and_asks_nothing_ends_on_its_question(alice, model):
    """muhammad, 2026-11-11: a stage reply that stays ends on a question too (the client's 2026-11-05 "a stage may
    stay without a question" is reversed, to tell the client)."""
    model(Reply(text="That thought has been with you a long time.", forward="When does it feel most true?",
                stage_answer="not_yet"))
    thread = await start(alice)
    await _land_on(alice, thread.id, "belief")
    turn = await send(alice, thread.id, "I don't know, it's just there")

    assert (await _offered_row(alice, thread.id)).phase == "belief"
    assert turn.content == "That thought has been with you a long time.\n\nWhen does it feel most true?"


async def _last_user_message_id(thread_id):
    from mani.db import pool

    async with pool.as_admin() as conn:
        return await conn.fetchval(
            "select id from public.messages where thread_id = $1 and role = 'user' order by created_at desc limit 1",
            thread_id,
        )


async def _user_messages(thread_id) -> list[str]:
    from mani.db import pool

    async with pool.as_admin() as conn:
        rows = await conn.fetch(
            "select content from public.messages where thread_id = $1 and role = 'user' order by created_at", thread_id
        )
    return [r["content"] for r in rows]


async def _undo(alice, thread_id, message_id=None):
    from mani.chat import rewind
    from mani.db import pool

    message_id = message_id or await _last_user_message_id(thread_id)
    async with pool.as_user(alice) as conn:
        await rewind.undo_last_turn(conn, ALICE, thread_id, message_id)


async def _edit(alice, thread_id, content):
    """What the edit endpoint does: take back the last turn, then run the new text."""
    return await runner.edit(alice, thread_id, await _last_user_message_id(thread_id), content)


async def test_editing_the_message_that_answered_a_check_takes_back_the_offer_and_runs_the_new_text(alice, model):
    from mani.models.rows import SupportStyle
    from mani.db import pool

    scripted = model(
        _offer("abcde"),
        Reply(text="What about it feels most wrong?", check_answer="no"),
        Reply(text="Go on.", check_answer="no"),
    )
    thread = await past_the_opening(await _in_style(await start(alice), SupportStyle.SUPPORTIVE))
    before = await _thread_row(alice, thread.id)
    await send(alice, thread.id, "yes, that's right")
    assert (await _offered_row(alice, thread.id)).outcome is TechniqueOutcome.OFFERED

    turn = await _edit(alice, thread.id, "not really, it's more that I'm tired")

    assert turn.content == "What about it feels most wrong?"
    assert await _offered_row(alice, thread.id) is None
    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)
    assert ctx.techniques_offered == []
    assert ctx.thread.understanding == before.understanding
    assert ctx.thread.check_at_message_count == before.check_at_message_count
    assert ctx.thread.message_count == before.message_count + 2
    assert await _user_messages(thread.id) == ["not really, it's more that I'm tired"]

    # Each turn keeps the snapshot of the one before it, so the new message can be edited too.
    await _edit(alice, thread.id, "actually, let me put it differently")
    assert await _user_messages(thread.id) == ["actually, let me put it differently"]
    assert scripted.calls == 3


async def test_editing_the_last_message_inside_a_framework_puts_the_walk_back_where_it_was(alice, model):
    a_own = "So it started with being left out of meetings at work. Is that where this began for you?"
    b_own = "You've been telling yourself nobody wants you there. Is that still how it feels?"
    model(
        _offer(),
        Reply(text=a_own, offer_answer="yes",
              next_stage=NextStage(status="possible", said="being left out of meetings at work"),
              stage_updates=[StageUpdate(stage="belief", said="nobody wants me there", status="known")]),
        Reply(text=b_own, stage_answer="agreed", next_stage=NextStage(status="known", said="nobody wants me there")),
        Reply(text="Thank you.", stage_answer="agreed", next_stage=_MISSING),
    )
    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "I'm left out of meetings at work and I think nobody wants me there")
    await send(alice, thread.id, "Try it")
    await send(alice, thread.id, "yes")
    row, store = await _offered_row(alice, thread.id), await _store(alice, thread.id)
    await send(alice, thread.id, "yes")
    moved = await _offered_row(alice, thread.id)
    assert (moved.phase, await _store(alice, thread.id)) != (row.phase, store)

    await _undo(alice, thread.id)

    restored = await _offered_row(alice, thread.id)
    assert (restored.phase, restored.outcome, restored.at_message_count) == (row.phase, row.outcome, row.at_message_count)
    assert await _store(alice, thread.id) == store


async def test_a_message_that_cannot_be_taken_back_safely_is_refused_and_nothing_changes(alice, model):
    from mani.db import pool
    from mani.errors import ErrorCategory, ServiceError
    from mani.models.rows import SupportStyle

    model(Reply(text="Tell me more."))
    thread = await _in_style(await start(alice), SupportStyle.SUPPORTIVE)
    await send(alice, thread.id, "first thing")
    first = await _last_user_message_id(thread.id)
    await send(alice, thread.id, "second thing")
    last = await _last_user_message_id(thread.id)

    async def refused(message_id) -> ErrorCategory:
        with pytest.raises(ServiceError) as raised:
            await _undo(alice, thread.id, message_id)
        return raised.value.category

    assert await refused(first) is ErrorCategory.CONFLICT
    async with pool.as_admin() as conn:
        await conn.execute("update public.messages set selected_prompt = 'Try it' where id = $1", last)
    assert await refused(last) is ErrorCategory.CONFLICT
    assert await _user_messages(thread.id) == ["first thing", "second thing"]


async def test_a_message_in_a_crisis_thread_is_edited_wherever_one_can_still_be_sent(alice, model):
    """muhammad, 2026-11-10: a thread flagged once refused every edit as "paused" while it still took new messages.
    The message that raised the concern is edited like any other: safety returns to what it was before that turn,
    and the record of the concern stays for review."""
    from mani.db import pool
    from mani.models.rows import SupportStyle

    async def recorded() -> list[str]:
        async with pool.as_admin() as conn:
            return [r["reason"] for r in await conn.fetch(
                "select reason from admin.crisis_events where thread_id = $1 order by detected_at", thread.id)]

    model(
        Reply(text="Tell me more."),
        Reply(text="I'm here with you.", safety=SafetyRead(danger="unsure", about="themselves")),
        Reply(text="I'm here with you.", safety=SafetyRead(danger="now", about="themselves")),
        Reply(text="Work sounds heavy."),
    )
    thread = await _in_style(await start(alice), SupportStyle.SUPPORTIVE)
    await send(alice, thread.id, "first thing")

    await send(alice, thread.id, "I want to die")
    assert await _safety(thread.id) == "unsure"
    await _edit(alice, thread.id, "I want to end it tonight")
    assert await _safety(thread.id) == "danger"
    turn = await _edit(alice, thread.id, "work is a lot")

    assert turn.content == "Work sounds heavy."
    assert await _user_messages(thread.id) == ["first thing", "work is a lot"]
    assert await _safety(thread.id) == "clear"
    assert await recorded() == ["safety: themselves", "safety: themselves"]


async def test_a_question_inside_the_questions_is_answered_and_the_stage_waits(alice, model):
    """muhammad, 2026-11-05: manasa asked "should I look at this thought or my numbness? Does one affect the other?"
    and the reply opened "Step 2 is Name What Makes It Painful". A message that asks something never moves the stage,
    whatever the reply reported, so no stage line is put in front of the answer."""
    model(Reply(
        text="They can affect each other: telling yourself you should be happy adds guilt on top of the numbness.",
        stage_answer="answered",
        stage_updates=[StageUpdate(stage="activate", said="the daily routine", status="known")],
    ))
    thread = await start(alice)
    await _land_on(alice, thread.id, "activate")
    turn = await send(alice, thread.id, "should I look at this thought or my numbness? Does one affect the other")

    assert (await _offered_row(alice, thread.id)).phase == "activate"
    assert not turn.content.startswith("B is for Belief")
    assert turn.content.startswith("They can affect each other")


async def test_a_settled_symptom_reopens_only_on_a_message_that_says_it_is_happening(alice, model):
    """The stroke chat, baseline of 2026-11-11: help was called and it settled, then "I am afraid of losing him" was read
    as the symptom happening now from earlier in the conversation. Only their newest message reopens it."""
    model(
        Reply(text="Call your local emergency number now. Can you call?",
              safety=SafetyRead(danger="now", about="body", symptom_now="yes")),
        Reply(text="You acted quickly. How are you holding up?", safety=SafetyRead(danger="none")),
        Reply(text="Of course you are afraid. What scares you most?",
              safety=SafetyRead(danger="now", about="body", symptom_now="unsaid")),
        Reply(text="Tell the dispatcher it is worse. Is someone with you?",
              safety=SafetyRead(danger="now", about="body", symptom_now="yes")),
    )
    thread = await start(alice)

    await send(alice, thread.id, "my dad's face is drooping and his speech is slurred")
    await send(alice, thread.id, "i called the ambulance, they are on the way, i am with him")
    assert await _safety(thread.id) == "clear"
    await send(alice, thread.id, "i am afraid of losing him")
    assert await _safety(thread.id) == "clear", "nothing new was said about the symptom"
    await send(alice, thread.id, "his face is drooping more now")
    assert await _safety(thread.id) == "danger"


async def _a_concern_came_up_and_settled(thread_id, *, danger: bool = True) -> None:
    """A concern earlier in the conversation, settled; `danger` when it reached danger and was recorded."""
    from mani.db import pool

    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.threads set crisis_detected = $2, "
            "understanding = understanding || jsonb_build_object('safety_settled', true) "
            "|| case when $2 then jsonb_build_object($3::text, true) else '{}'::jsonb end where id = $1",
            thread_id, danger, context.DANGER_REACHED,
        )


async def test_after_the_last_stage_a_chat_that_held_a_concern_asks_about_safety_before_the_closing_choices(alice, model):
    """muhammad, 2026-11-11: when a crisis came up at any point in the chat, Mani comes back to it once after the last
    stage, as its own reply, before Keep Chatting and Finish for Now; a chat with no concern ends as it always did
    (test_a_walk_with_nothing_known_names_each_letter_and_asks_one_stage_per_reply)."""
    scripted = model(
        _offer(), Reply(text=_OWN_QUESTIONS["activate"], next_stage=_MISSING),
        _answered("activate", "left out of meetings", _OWN_QUESTIONS["belief"]),
        _answered("belief", "nobody wants me there", _OWN_QUESTIONS["consequence"]),
        _answered("consequence", "I stopped speaking up", _OWN_QUESTIONS["dispute"]),
        _answered("dispute", "they never said why", _OWN_QUESTIONS["effective"]),
        _answered("effective", "I don't know why yet", "Thank you."),
        Reply(text="I'm glad it has passed. What would you like to do now?", safety=SafetyRead(danger="none")),
    )
    thread = await past_the_opening(await start(alice))
    await _a_concern_came_up_and_settled(thread.id)
    await send(alice, thread.id, "I keep getting left out at work")
    replies = [await send(alice, thread.id, said) for said in (
        "Try it", "they left me out of the meeting", "nobody wants me there", "I stopped speaking up",
        "they never said why", "maybe I don't know why yet",
    )]

    assert replies[5].content == crisis.END_CHECK
    assert replies[5].trace["end_check"] == "asked"
    assert replies[5].prompts == [], "the closing choices wait for their answer"
    assert await _safety(thread.id) == "unsure", "their answer is read as a safety turn"
    assert (await _offered_row(alice, thread.id)).phase == "effective"

    after = await send(alice, thread.id, "it passed, the doctor said it was nothing serious")

    assert after.content == "I'm glad it has passed."
    assert [p.label for p in after.prompts] == ["Keep Chatting", "Go to Library", "Finish for Now"]
    assert await _safety(thread.id) == "clear"
    assert (await _offered_row(alice, thread.id)).phase == "somatic_closing"
    assert scripted.calls == 8


_WALK_TO_THE_END = (
    "Try it", "they left me out of the meeting", "nobody wants me there", "I stopped speaking up",
    "they never said why", "maybe I don't know why yet",
)


def _the_walk() -> tuple[Reply, ...]:
    return (
        _offer(), Reply(text=_OWN_QUESTIONS["activate"], next_stage=_MISSING),
        _answered("activate", "left out of meetings", _OWN_QUESTIONS["belief"]),
        _answered("belief", "nobody wants me there", _OWN_QUESTIONS["consequence"]),
        _answered("consequence", "I stopped speaking up", _OWN_QUESTIONS["dispute"]),
        _answered("dispute", "they never said why", _OWN_QUESTIONS["effective"]),
        _answered("effective", "I don't know why yet", "Thank you."),
    )


async def test_a_false_alarm_that_never_reached_danger_ends_the_framework_as_usual(alice, model):
    """"I can't spend another day under this roof", explained as the workplace: asked about once and settled, never a
    crisis. The question after the last stage is for a chat a crisis was in (muhammad, 2026-11-11)."""
    model(*_the_walk())
    thread = await past_the_opening(await start(alice))
    await _a_concern_came_up_and_settled(thread.id, danger=False)
    await send(alice, thread.id, "I keep getting left out at work")
    replies = [await send(alice, thread.id, said) for said in _WALK_TO_THE_END]

    assert replies[5].content == "Thank you."
    assert [p.label for p in replies[5].prompts] == ["Keep Chatting", "Go to Library", "Finish for Now"]


async def test_the_end_check_comes_only_after_danger(alice, model):
    """The audit, 2026-11-13: "I want to die" judged only unsure and then settled flags the conversation for review, and
    that flag alone asked the question after the last stage. It is asked only where a turn reached danger."""
    model(
        Reply(text="I'm glad you told me. Are you in danger right now?",
              safety=SafetyRead(danger="unsure", about="themselves")),
        Reply(text="I'm glad. What happened today?", safety=SafetyRead(danger="none")),
        *_the_walk(),
    )
    thread = await start(alice)
    await send(alice, thread.id, "i think i want to die")
    await send(alice, thread.id, "no i am fine, it was just a horrible day")
    assert (await _thread_row(alice, thread.id)).crisis_detected is True
    await past_the_opening(thread)
    await send(alice, thread.id, "I keep getting left out at work")
    replies = [await send(alice, thread.id, said) for said in _WALK_TO_THE_END]

    assert replies[5].content == "Thank you."
    assert [p.label for p in replies[5].prompts] == ["Keep Chatting", "Go to Library", "Finish for Now"]


async def test_pushing_the_question_after_the_last_stage_away_holds_the_close_until_they_answer(alice, model):
    """A refusal never settles a concern (manasa's test, 2026-11-06), here too: the closing choices come with the
    reply that settles it."""
    model(
        *_the_walk(),
        Reply(text="That's okay. I only want to be sure you're all right. How is it now?",
              safety=SafetyRead(danger="unsure", declined=True)),
        Reply(text="I'm glad. What would you like to do next?", safety=SafetyRead(danger="none")),
    )
    thread = await past_the_opening(await start(alice))
    await _a_concern_came_up_and_settled(thread.id)
    await send(alice, thread.id, "I keep getting left out at work")
    for said in _WALK_TO_THE_END:
        await send(alice, thread.id, said)

    pushed = await send(alice, thread.id, "i don't want to talk about that")
    assert pushed.prompts == [] and await _safety(thread.id) == "unsure"
    settled = await send(alice, thread.id, "it's fine, it never came back")

    assert settled.content == "I'm glad."
    assert [p.label for p in settled.prompts] == ["Keep Chatting", "Go to Library", "Finish for Now"]


async def test_the_pause_gate_runs_under_the_message_lock(alice, model, monkeypatch):
    """A retry reaching another instance waits on the lock for the first request, and is then refused as paused
    rather than handed the stored pause text."""
    model(Reply(text="Hello."))
    thread = await start(alice)
    held: list[bool] = []
    real_active = pauses.active

    async def active(conn, *args, **kwargs):
        held.append(await conn.fetchval(
            "select exists (select 1 from pg_locks where locktype = 'advisory' and pid = pg_backend_pid() and granted)"
        ))
        return await real_active(conn, *args, **kwargs)

    monkeypatch.setattr(orchestrator.pauses, "active", active)
    await runner.send(alice, thread.id, "hi", client_message_id=uuid.uuid4())

    assert held[0] is True
