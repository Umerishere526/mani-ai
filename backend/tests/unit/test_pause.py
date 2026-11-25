# ABOUTME: Checks when a turn in the conversation a pause began in asks whether they are all right: once per pause, with
# ABOUTME: what the pause rested on.

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


def _pause(**update) -> Pause:
    return Pause(
        id=PAUSE, user_id=USER, thread_id=PAUSED_IN, started_at=STARTED, ends_at=ENDED, reason="has the pills",
    ).model_copy(update=update)


def _turn(latest: Pause | None, *, asked: str | None = None) -> TurnContext:
    """A turn in the conversation whose latest pause that has run out is `latest`, having asked about the pause `asked`,
    if any, as threads.load_turn_context loads them."""
    understanding = {record.RETURN_CHECK: {"pause": asked, "state": "answered"}} if asked else {}
    thread = Thread(id=PAUSED_IN, user_id=USER, created_at=STARTED, last_message_at=STARTED, understanding=understanding)
    return TurnContext(thread=thread, profile=None, technique=None, pause=latest)


def test_the_paused_conversation_asks_once_per_pause_with_what_the_pause_rested_on():
    """muhammad, 2026-11-19: the first message back is read for safety in the conversation the pause began in; a later
    pause there asks again with its own reason."""
    assert pause.return_check(_turn(_pause())) == pause.ReturnCheck(PAUSE, "has the pills")
    later = _pause(id=SECOND, reason="plans to end it")
    assert pause.return_check(_turn(later, asked=str(PAUSE))) == pause.ReturnCheck(SECOND, "plans to end it")

    for asks_nothing in (_turn(None), _turn(_pause(), asked=str(PAUSE))):
        assert pause.return_check(asks_nothing) is None, asks_nothing


def test_the_message_after_the_question_answers_it():
    asked = Thread(id=OTHER, user_id=USER, created_at=STARTED, last_message_at=STARTED,
                   understanding=record.return_check({}, str(PAUSE), "asked"))
    assert pause.answering(TurnContext(thread=asked, profile=None, technique=None)) == str(PAUSE)
    assert pause.answering(_turn(_pause(), asked=str(PAUSE))) is None
