# ABOUTME: Checks the seeded frameworks carry what the turn reads from them: the letters in order, each letter's line,
# ABOUTME: the Tell me more explanation in every style, and when each stage counts as answered. No database needed.

import pytest

from mani.chat.facts import framework_guide
from mani.chat.techniques import Registry
from mani.models.rows import Framework
from scripts.seed import FRAMEWORKS_DIR, parse_framework

STYLES = ("directive", "supportive", "reflective")


@pytest.fixture(scope="module")
def abcde() -> dict:
    return parse_framework(FRAMEWORKS_DIR / "abcde.md")


def as_framework(parsed: dict) -> Framework:
    return Framework(
        id=parsed["id"], name=parsed["name"], summary=parsed["summary"], body="b",
        phases=parsed["phases"], activation=parsed["activation"], stages=parsed["stages"],
    )


def test_abcde_and_thought_reframe_are_the_frameworks_seeded():
    assert sorted(p.stem for p in FRAMEWORKS_DIR.glob("*.md")) == ["abcde", "thought_reframe"]


def test_abcde_runs_a_to_e(abcde):
    assert abcde["phases"] == ["offering", "activate", "belief", "consequence", "dispute", "effective"]


def test_each_letter_line_reaches_the_guide_in_order(abcde):
    """The client asked for each letter to be named as it is reached, so the person knows which step they are on;
    the model says the line, and the guide is where it reads it."""
    guide = framework_guide(Registry([as_framework(abcde)]))
    lines = ["A is for Activating Event.", "B is for Belief.", "C is for Consequences.", "D is for Dispute.",
             "E is for Effective New Belief."]
    positions = [guide.index(line) for line in lines]
    assert positions == sorted(positions)


def test_tell_me_more_has_the_clients_explanation_in_every_style(abcde):
    explain = abcde["stages"]["offering"]["explain"]
    assert set(explain) == set(STYLES)
    for text in explain.values():
        assert "A: Activating Event" in text and "E: Effective New Belief" in text


def test_when_a_stage_counts_as_answered_keeps_the_clients_reading(abcde):
    """Lolly, 2026-10-22: A counts only what happened as the event, and E accepts a commitment for next time."""
    stages = abcde["stages"]
    assert "rather than as their interpretation of it" in stages["activate"]["ready_when"]
    assert "commitment for next time counts as the path" in stages["effective"]["ready_when"]
