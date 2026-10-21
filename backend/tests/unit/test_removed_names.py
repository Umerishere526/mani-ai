# ABOUTME: Fails if a name from the old framework ending comes back: Chat More, its questions, the exercise pick.
# ABOUTME: The client's body check-in (spec: somatic cadence) replaced them, so none is left behind to be called.

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).parents[2]

REMOVED = [
    "CHAT_MORE_LABEL", "AFTER_FRAMEWORK_QUESTIONS", "after_framework_question", "_after_framework_question",
    "library_offered_since", "library_pending", "choose_exercise", "_offer_exercise", "StartExercise",
    "list_for_framework", "EXERCISE_SELECT", "PLACE_LABELS", "body_reply", "body_answer_fits", "_awaiting_place",
    "_offered_handoff", "build_tool_choice", "_closing_unanswered", "somatic_checkin", "CHECKIN",
]


@pytest.mark.parametrize("name", REMOVED)
def test_a_name_from_the_old_ending_does_not_come_back(name):
    sources = [*ROOT.glob("mani/**/*.py"), *ROOT.glob("scripts/*.py")]
    found = [str(p.relative_to(ROOT)) for p in sources if re.search(rf"\b{re.escape(name)}\b", p.read_text())]
    assert not found, f"{name} is back in {found}"
