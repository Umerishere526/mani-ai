# ABOUTME: Checks when a turn after a pause asks whether they are all right: once per pause, in every conversation, with
# ABOUTME: what the pause rested on, and never again once they have said, in any conversation, that they are.

import datetime as dt
import uuid

from mani.chat import pause, record
from mani.db.threads import TurnContext
from mani.models.rows import Pause, Thread

USER = uuid.UUID("a0000000-0000-4000-8000-0000000000e1")
PAUSED_IN = uuid.UUID("b0000000-0000-4000-8000-0000000000e1")
OTHER = uuid.UUID("b0000000-0000-4000-8000-0000000000e2")
PAUSE = uuid.UUID("c0000000-0000-4000-8000-0000000000e1")
SECOND = uuid.UUID("c0000000-0000-4000-8000-0000000000e2")
STARTED = dt.datetime(2026, 11, 13, 12, 0, tzinfo=dt.UTC)
ENDED = STARTED + dt.timedelta(minutes=15)
LATER = ENDED + dt.timedelta(minutes=1)


def _pause(**update) -> Pause:
    return Pause(
        id=PAUSE, user_id=USER, thread_id=PAUSED_IN, started_at=STARTED, ends_at=ENDED, reason="has the pills",
    ).model_copy(update=update)


def _turn(thread_id: uuid.UUID, latest: Pause | None, *, asked: str | None = None) -> TurnContext:
    """A turn whose person's latest pause that has run out is `latest`, in a conversation that has asked about the pause
    `asked`, if any, as threads.load_turn_context loads them."""
    understanding = {record.RETURN_CHECK: {"pause": asked, "state": "answered"}} if asked else {}
    thread = Thread(id=thread_id, user_id=USER, created_at=STARTED, last_message_at=STARTED, understanding=understanding)
    return TurnContext(thread=thread, profile=None, technique=None, pause=latest)


def test_every_conversation_asks_once_per_pause_with_what_the_pause_rested_on():
    """muhammad, 2026-11-13: the paused conversation and every other, new or older, so nobody bypasses it by opening
    another. 2026-11-16: with what they faced, wherever they come back."""
    asking = pause.ReturnCheck(PAUSE, "has the pills")
    assert pause.return_check(_turn(PAUSED_IN, _pause())) == asking
    assert pause.return_check(_turn(OTHER, _pause())) == asking
    assert pause.return_check(_turn(PAUSED_IN, _pause(), asked=str(uuid.uuid4()))) == asking, "a second pause asks again"

    for asks_nothing in (_turn(PAUSED_IN, None), _turn(PAUSED_IN, _pause(), asked=str(PAUSE)),
                         _turn(OTHER, _pause(), asked=str(PAUSE))):
        assert pause.return_check(asks_nothing) is None, asks_nothing


def test_nothing_asks_once_they_have_said_in_any_conversation_that_they_are_all_right():
    """muhammad, 2026-11-19: until they say they are all right, in any conversation, as the decision of 2026-11-13 reads.
    The conversation the pause began in used to keep asking after the answer was given elsewhere."""
    checked = _pause(checked_at=LATER)
    assert pause.return_check(_turn(PAUSED_IN, checked)) is None
    assert pause.return_check(_turn(OTHER, checked)) is None


def test_a_later_pause_is_asked_about_with_its_own_reason_in_every_conversation():
    """A conversation that answered the first pause's question is asked again once a later pause has run out, with what
    that one rested on; each conversation asks about the latest pause, so its own older one adds nothing."""
    later = _pause(id=SECOND, thread_id=OTHER, reason="plans to end it", started_at=LATER,
                   ends_at=LATER + dt.timedelta(minutes=15))
    assert pause.return_check(_turn(PAUSED_IN, later, asked=str(PAUSE))) == pause.ReturnCheck(SECOND, "plans to end it")
    assert pause.return_check(_turn(PAUSED_IN, later)) == pause.ReturnCheck(SECOND, "plans to end it")


def test_the_message_after_the_question_answers_it():
    asked = Thread(id=OTHER, user_id=USER, created_at=STARTED, last_message_at=STARTED,
                   understanding=record.return_check({}, str(PAUSE), "asked"))
    assert pause.answering(TurnContext(thread=asked, profile=None, technique=None)) == str(PAUSE)
    assert pause.answering(_turn(OTHER, _pause(), asked=str(PAUSE))) is None
