# ABOUTME: Checks the rule that decides when a chat pauses on danger, and when a turn after a pause asks whether they are
# ABOUTME: all right: once per pause, in the paused conversation with its reason and in every other with none.

import datetime as dt
import uuid
from itertools import product

from mani.chat import context, pause
from mani.chat.safety import State
from mani.db.threads import TurnContext
from mani.models.rows import Pause, Thread


def test_the_chat_pauses_when_danger_continues_with_nothing_in_place_and_a_body_danger_only_on_a_refusal():
    """muhammad, 2026-11-14: a production chat said "i want to kill myself", was about to act, was alone and had called
    no one, and never paused in 11 turns because it never refused. Danger to themselves, to someone else or from
    someone that goes on after the direction with nothing in place pauses. A symptom in the body pauses only on an
    outright refusal of the help for a symptom happening now (2026-11-13), and a read whose danger has no kind needs a
    refusal too, so it cannot pause a body chat by accident."""
    for before, after, in_place, declined, after_check, is_check, about, danger, symptom_now in product(
        State, State, (True, False), (True, False), (True, False), (True, False),
        ("themselves", "someone_else", "from_someone", "body", None), ("now", "none", None), ("yes", "unsaid", None),
    ):
        if about == "body":
            settled_on_it = declined and danger == "now" and symptom_now == "yes"
        else:
            settled_on_it = declined or about is not None
        expected = (
            after is State.DANGER and settled_on_it and not in_place and not is_check
            and (before is State.DANGER or after_check)
        )
        got = pause.pauses_now(
            before, after, help_in_place=in_place, declined=declined, about=about, danger=danger,
            symptom_now=symptom_now, after_return_check=after_check, is_return_check=is_check,
        )
        assert got is expected, (before, after, in_place, declined, after_check, is_check, about, danger, symptom_now)


def test_the_cases_the_live_replays_and_the_production_chat_got_wrong_and_right():
    def pauses(
        *, declined: bool = False, in_place: bool = False, after_check: bool = False, is_check: bool = False,
        about: str | None = "themselves", danger: str | None = "now", symptom_now: str | None = None,
    ) -> bool:
        return pause.pauses_now(
            State.UNSURE if after_check or is_check else State.DANGER, State.DANGER, help_in_place=in_place,
            declined=declined, about=about, danger=danger, symptom_now=symptom_now,
            after_return_check=after_check, is_return_check=is_check,
        )

    assert pauses(), "\"no\" (nobody is with them) after the direction, about to act (production, 2026-11-14)"
    assert pauses(about="someone_else"), "danger to someone else goes on with nothing in place"
    assert pauses(about="from_someone"), "danger from someone goes on with nothing in place"
    assert pauses(about="someone_else", declined=True), "\"yes I'll kill him\" after the direction"
    assert not pauses(in_place=True), "\"someone is with me\""
    assert not pauses(declined=True, in_place=True), "help in place guards a refusal too"
    assert pauses(after_check=True), "the answer to the return check, danger and nothing in place"
    assert not pauses(declined=True, is_check=True), "the return check itself"
    assert not pauses(about=None), "a danger of no known kind needs a refusal"
    assert pauses(about=None, declined=True), "\"leave me alone\", danger of no known kind"
    assert not pauses(about="body", symptom_now="yes"), "a doubt about a symptom now (\"could it be stress?\")"
    assert not pauses(about="body", symptom_now="yes"), "\"my wife is calling\" read with help_in_place false"
    assert pauses(declined=True, about="body", symptom_now="yes"), (
        "refusing the help for a symptom happening now (\"I'm not calling an ambulance\")")
    assert not pauses(declined=True, about="body", symptom_now="unsaid"), "a symptom not said to be happening now"
    assert not pauses(declined=True, about="body", danger="none"), "Lolly's read: declined only, on a body thread"


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
    understanding = {context.RETURN_CHECK: {"pause": asked, "state": "answered"}} if asked else {}
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
    elsewhere = _pause(reason=None)
    assert pause.return_check(_turn(OTHER, elsewhere, created_at=LATER)) == pause.ReturnCheck(PAUSE, "other_thread"), (
        "another conversation carries none of its reason")
    assert pause.return_check(_turn(OTHER, elsewhere, created_at=STARTED - dt.timedelta(days=1))) == (
        pause.ReturnCheck(PAUSE, "other_thread")), "muhammad, 2026-11-13: an older conversation asks too"

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
    owed in every conversation, this one too, without the other's reason."""
    later = _pause(id=SECOND, thread_id=OTHER, reason=None, started_at=LATER, ends_at=LATER + dt.timedelta(minutes=15))
    turn = _turn(PAUSED_IN, later, own=_pause(), asked=str(PAUSE))

    assert pause.return_check(turn) == pause.ReturnCheck(SECOND, "other_thread")


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
