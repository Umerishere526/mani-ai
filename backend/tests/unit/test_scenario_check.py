# ABOUTME: The scenario check's own flags, which decide what a run against the real model reports.
# ABOUTME: A flag that misfires sends a fix after a problem the conversation does not have.

import importlib.util
import pathlib
import sys

_PATH = pathlib.Path(__file__).resolve().parents[2] / "scripts" / "scenario_check.py"
_SPEC = importlib.util.spec_from_file_location("scenario_check", _PATH)
scenario_check = importlib.util.module_from_spec(_SPEC)
# Its dataclasses look their own module up by name while the file runs.
sys.modules["scenario_check"] = scenario_check
_SPEC.loader.exec_module(scenario_check)


def test_a_question_made_of_what_they_said_earlier_is_flagged_after_a_short_answer():
    """Asking for what they already said is a check on the whole conversation: their last message
    is often only a yes, and the question repeats something from before it."""
    said = scenario_check._words("what happened with your manager at work") | {"yes"}
    exchange = scenario_check.Exchange(
        person="yes", reply="Okay. What happened with your manager at work?", buttons=[], offered=None,
    )
    scenario_check._check(exchange, None, False, said)
    assert "asks what they already said" in exchange.flags
