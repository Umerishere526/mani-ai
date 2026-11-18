# ABOUTME: Checks the rule that decides when a chat pauses on danger, and when a turn after a pause asks whether they are
# ABOUTME: all right: once per pause, in the paused conversation and in every other, with what the pause rested on.

import datetime as dt
import uuid
from itertools import product

from mani.chat import pause, record, safety
from mani.chat.safety import State
from mani.db.threads import TurnContext
from mani.models.rows import Pause, Thread


def test_the_chat_pauses_when_danger_continues_with_nothing_in_place_and_a_body_danger_only_on_a_refusal():
    """muhammad, 2026-11-14: a production chat said "i want to kill myself", was about to act, was alone and had called
    no one, and never paused in 11 turns because it never refused. Danger to themselves, to someone else or from
    someone that goes on after the direction with nothing in place pauses. A symptom in the body pauses only on an
    outright refusal of the help for a symptom happening now (2026-11-13), and a read whose danger has no kind needs a
    refusal too, so it cannot pause a body chat by accident. muhammad, 2026-11-16: after Mani only asked what they
    meant, an answer that says it again pauses, and one held as danger without saying it gets Mani's reply first; the
    first message back after a pause never pauses, and their answer to how things are pauses only when the read
    reports that it says the danger is still there."""
    for before, after, in_place, declined, after_check, is_check, still_there, about, danger, symptom_now, asked in product(
        State, State, (True, False), (True, False), (True, False), (True, False), (True, False),
        ("themselves", "someone_else", "from_someone", "body", None), ("now", "unsure", "none", None),
        ("yes", "unsaid", None), (True, False),
    ):
        if about == "body":
            settled_on_it = declined and danger == "now" and symptom_now == "yes"
        else:
            settled_on_it = declined or about is not None
        if is_check:
            goes_on = False
        elif after_check:
            goes_on = still_there
        elif before is State.UNSURE:
            goes_on = asked and danger == "now"
        else:
            goes_on = before is State.DANGER
        expected = after is State.DANGER and settled_on_it and not in_place and goes_on
        got = pause.pauses_now(
            before, after, help_in_place=in_place, declined=declined, about=about, danger=danger,
            symptom_now=symptom_now, after_return_check=after_check, is_return_check=is_check, still_there=still_there,
            asked=asked,
        )
        assert got is expected, (
            before, after, in_place, declined, after_check, is_check, still_there, about, danger, symptom_now, asked)


def test_the_cases_the_live_replays_and_the_production_chat_got_wrong_and_right():
    def pauses(
        *, declined: bool = False, in_place: bool = False, after_check: bool = False, is_check: bool = False,
        about: str | None = "themselves", danger: str | None = "now", symptom_now: str | None = None,
        still_there: bool = False,
    ) -> bool:
        return pause.pauses_now(
            State.UNSURE if after_check or is_check else State.DANGER, State.DANGER, help_in_place=in_place,
            declined=declined, about=about, danger=danger, symptom_now=symptom_now,
            after_return_check=after_check, is_return_check=is_check, still_there=still_there, asked=True,
        )

    assert pauses(), "\"no\" (nobody is with them) after the direction, about to act (production, 2026-11-14)"
    assert pauses(about="someone_else"), "danger to someone else goes on with nothing in place"
    assert pauses(about="from_someone"), "danger from someone goes on with nothing in place"
    assert pauses(about="someone_else", declined=True), "\"yes I'll kill him\" after the direction"
    assert not pauses(in_place=True), "\"someone is with me\""
    assert not pauses(declined=True, in_place=True), "help in place guards a refusal too"
    assert pauses(after_check=True, still_there=True), "the answer to the return check says the danger is still there"
    assert not pauses(after_check=True), (
        "muhammad's local chat, 2026-11-16: asked how things were after a pause he answered \"fine\", the read "
        "held the earlier words against it as danger now, and the chat paused again; only an answer that itself "
        "says the danger is still there pauses")
    assert not pauses(declined=True, is_check=True), "the first message back is asked how things are"
    assert not pauses(is_check=True, still_there=True), (
        "muhammad, 2026-11-16, after the held-back run: the first message back always gets Mani's reply, whatever "
        "the read reports. \"nobody knows where i am\" and \"my dad would pick up\" were read as still there and "
        "paused again with no word from Mani, three pauses in a row")
    assert not pauses(after_check=True, still_there=True, in_place=True), "their answer: someone is with them"
    assert not pauses(about=None), "a danger of no known kind needs a refusal"
    assert pauses(about=None, declined=True), "\"leave me alone\", danger of no known kind"
    assert not pauses(about="body", symptom_now="yes"), "a doubt about a symptom now (\"could it be stress?\")"
    assert not pauses(about="body", symptom_now="yes"), "\"my wife is calling\" read with help_in_place false"
    assert pauses(declined=True, about="body", symptom_now="yes"), (
        "refusing the help for a symptom happening now (\"I'm not calling an ambulance\")")
    assert not pauses(declined=True, about="body", symptom_now="unsaid"), "a symptom not said to be happening now"
    assert not pauses(declined=True, about="body", danger="none"), "Lolly's read: declined only, on a body thread"


def test_once_they_were_asked_an_answer_that_means_danger_pauses_at_once_and_a_first_danger_message_does_not():
    """muhammad, 2026-11-16: Mani asks or points to help, they say "I just want to die", and that is the answer: no
    further question, the help screen comes, every time. Before, the screen needed two danger turns in a row, so it
    came one reply late or not at all. A first message that is danger out of a clear conversation still gets Mani's
    own reply with what keeps them safe; the screen follows if the danger goes on."""
    def pauses(before: State, about: str | None = "themselves", **read) -> bool:
        return pause.pauses_now(
            before, State.DANGER, help_in_place=read.get("in_place", False), declined=read.get("declined", False),
            about=about, danger="now", symptom_now=read.get("symptom_now"), after_return_check=False,
            is_return_check=False, asked=before is State.UNSURE,
        )

    assert pauses(State.UNSURE), "asked what they meant, and their answer is that they want to die"
    assert not pause.pauses_now(
        State.UNSURE, State.DANGER, help_in_place=False, declined=False, about="themselves", danger="unsure",
        symptom_now=None, after_return_check=False, is_return_check=False, asked=True,
    ), "asked, and \"I don't know, maybe\": held as danger, and Mani says how to reach help before any screen"
    assert pauses(State.DANGER), "danger that goes on after the direction"
    assert not pauses(State.CLEAR), "the first danger message gets Mani's own reply first"
    assert not pauses(State.UNSURE, in_place=True), "someone is with them"
    assert not pauses(State.UNSURE, about="body", symptom_now="yes"), "a symptom in the body still needs a refusal"


USER = uuid.UUID("a0000000-0000-4000-8000-0000000000e1")
PAUSED_IN = uuid.UUID("b0000000-0000-4000-8000-0000000000e1")
OTHER = uuid.UUID("b0000000-0000-4000-8000-0000000000e2")
PAUSE = uuid.UUID("c0000000-0000-4000-8000-0000000000e1")
STARTED = dt.datetime(2026, 11, 13, 12, 0, tzinfo=dt.UTC)
ENDED = STARTED + dt.timedelta(minutes=15)
LATER = ENDED + dt.timedelta(minutes=1)


def _pause(**update) -> Pause:
    return Pause(
        id=PAUSE, user_id=USER, thread_id=PAUSED_IN, started_at=STARTED, ends_at=ENDED, reason="has the pills",
    ).model_copy(update=update)


_UNSET = object()


def _turn(
    thread_id: uuid.UUID, held: Pause | None, *, own=_UNSET, created_at=STARTED, asked: str | None = None,
) -> TurnContext:
    """A turn whose person's latest pause is `held`; its conversation's own is `own`, by default `held` when it began
    there, as threads.load_turn_context loads them."""
    understanding = {record.RETURN_CHECK: {"pause": asked, "state": "answered"}} if asked else {}
    thread = Thread(
        id=thread_id, user_id=USER, created_at=created_at, last_message_at=created_at, understanding=understanding,
    )
    if own is _UNSET:
        own = held if held is not None and held.thread_id == thread_id else None
    return TurnContext(thread=thread, profile=None, technique=None, pause=held, own_pause=own)


def test_a_turn_after_a_pause_asks_once_per_pause_in_the_paused_conversation_and_in_every_other():
    assert pause.return_check(_turn(PAUSED_IN, _pause())) == pause.ReturnCheck(PAUSE, "paused_thread", "has the pills")
    assert pause.return_check(_turn(PAUSED_IN, _pause(checked_at=LATER))).kind == "paused_thread", (
        "an answer in another conversation never stops the paused one asking")
    assert pause.return_check(_turn(PAUSED_IN, _pause(), asked=str(uuid.uuid4()))).kind == "paused_thread", (
        "a second pause asks again")
    elsewhere = _pause()
    assert pause.return_check(_turn(OTHER, elsewhere, created_at=LATER)) == (
        pause.ReturnCheck(PAUSE, "other_thread", "has the pills")
    ), "muhammad, 2026-11-16: another conversation asks with what the pause rested on"
    assert pause.return_check(_turn(OTHER, elsewhere, created_at=STARTED - dt.timedelta(days=1))) == (
        pause.ReturnCheck(PAUSE, "other_thread", "has the pills")), "muhammad, 2026-11-13: an older conversation asks too"

    for asks_nothing in (
        _turn(PAUSED_IN, None),
        _turn(PAUSED_IN, _pause(), asked=str(PAUSE)),
        _turn(OTHER, elsewhere, created_at=LATER, asked=str(PAUSE)),
        _turn(OTHER, _pause(checked_at=LATER, reason=None), created_at=LATER),
        _turn(OTHER, _pause(checked_at=LATER, reason=None), created_at=STARTED - dt.timedelta(days=1)),
    ):
        assert pause.return_check(asks_nothing) is None, asks_nothing


SECOND = uuid.UUID("c0000000-0000-4000-8000-0000000000e2")


def test_a_later_pause_elsewhere_is_asked_about_in_a_conversation_that_answered_its_own():
    """The paused conversation answered its own question; a later pause in another conversation has run out. That one is
    owed in every conversation, this one too, with what that later pause rested on."""
    later = _pause(
        id=SECOND, thread_id=OTHER, reason="plans to end it", started_at=LATER, ends_at=LATER + dt.timedelta(minutes=15),
    )
    turn = _turn(PAUSED_IN, later, own=_pause(), asked=str(PAUSE))

    assert pause.return_check(turn) == pause.ReturnCheck(SECOND, "other_thread", "plans to end it")


def test_a_conversation_with_its_own_pause_unasked_asks_once_with_its_reason_for_the_latest_pause():
    """Its own pause has never been asked about, and a later one elsewhere has run out: it asks once, with its own
    reason, tied to the latest pause, so the next message answers it rather than being asked again."""
    later = _pause(id=SECOND, thread_id=OTHER, reason=None, started_at=LATER, ends_at=LATER + dt.timedelta(minutes=15))

    asking = pause.return_check(_turn(PAUSED_IN, later, own=_pause()))
    assert asking == pause.ReturnCheck(SECOND, "paused_thread", "has the pills")
    assert pause.return_check(_turn(PAUSED_IN, later, own=_pause(), asked=str(SECOND))) is None
    third = later.model_copy(update={"id": uuid.uuid4()})
    assert pause.return_check(_turn(PAUSED_IN, third, own=_pause(), asked=str(SECOND))) == (
        pause.ReturnCheck(third.id, "other_thread")), "its old reason is said once, not again for every later pause"


def test_a_question_about_one_worry_does_not_count_as_asked_about_another():
    """The held-back run, 2026-11-16: asked whether their parents might hurt them ("my parents are going to kill me"),
    a student then said "sometimes I just want to disappear for good" and was paused at once, never asked about it
    and with no word from Mani. Having asked about one kind of danger is not having asked about another, so that
    message gets Mani's reply first, as a first danger message does."""
    assert safety.asked_about_this(State.UNSURE, "from_someone", "from_someone")
    assert not safety.asked_about_this(State.UNSURE, "from_someone", "themselves")
    assert safety.asked_about_this(State.UNSURE, None, "themselves"), "a question whose kind was not stored"
    assert safety.asked_about_this(State.UNSURE, "themselves", None), "an answer whose read names no kind"
    assert not safety.asked_about_this(State.CLEAR, "themselves", "themselves"), "nothing was asked"

    def pauses(asked: bool) -> bool:
        return pause.pauses_now(
            State.UNSURE, State.DANGER, help_in_place=False, declined=False, about="themselves", danger="now",
            symptom_now=None, after_return_check=False, is_return_check=False, asked=asked,
        )

    assert pauses(asked=True), "asked about this, and they say it again (muhammad, 2026-11-16)"
    assert not pauses(asked=False), "asked about something else: Mani answers this first"
