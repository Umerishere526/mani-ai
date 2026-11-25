# ABOUTME: Checks what an edit puts back of the conversation's safety: never less than the danger it reached.
# ABOUTME: Pure: the snapshot an edit restores, against the thread as the edited turn left it.

import datetime as dt
import uuid

from mani.chat import record as rec
from mani.chat import rewind
from mani.db.threads import TurnContext
from mani.models.rows import Thread

SAID = dt.datetime(2026, 11, 25, 12, 0, tzinfo=dt.UTC)


def _left(safety: str, understanding: dict) -> TurnContext:
    thread = Thread(id=uuid.uuid4(), user_id=uuid.uuid4(), created_at=SAID, last_message_at=SAID, safety=safety,
                    understanding=understanding)
    return TurnContext(thread=thread, profile=None, technique=None)


def test_an_edit_never_lowers_the_danger_the_conversation_reached():
    """S8 (PROVISIONAL: clinician sign-off required before deploy): an edit restored the state before the first danger
    message, so each rewrite of it was a first danger message again, never paused, and wrote another crisis event."""
    before = {"title": None, "understanding": {rec.NOTES: "work", rec.CALM: 1}, "safety": "unsure", "technique": None}
    left = _left("danger", {rec.NOTES: "pills", rec.ABOUT: "themselves", rec.DANGER_REACHED: True})

    kept = rewind.held(before, left)

    assert kept["safety"] == "danger"
    assert kept["understanding"] == {rec.NOTES: "work", rec.ABOUT: "themselves", rec.DANGER_REACHED: True}


def test_an_edit_after_the_danger_settled_keeps_that_it_was_reached_and_restores_the_rest():
    before = {"title": None, "understanding": {rec.NOTES: "work"}, "safety": "clear", "technique": None}
    kept = rewind.held(before, _left("clear", {rec.DANGER_REACHED: True, rec.SAFETY_SETTLED: True}))
    assert kept["safety"] == "clear" and kept["understanding"] == {rec.NOTES: "work", rec.DANGER_REACHED: True}
    assert rewind.held(before, _left("unsure", {rec.ABOUT: "themselves"})) == before
