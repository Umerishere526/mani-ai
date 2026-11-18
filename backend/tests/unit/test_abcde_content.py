# ABOUTME: Checks the seeded frameworks carry what the turn reads from them: the letters in order, each letter's line,
# ABOUTME: the five steps in every style and the worked example, and when each stage counts as answered. No database needed.

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


LIST = (
    "- A: Activating event (what happened)\n"
    "- B: Belief (what did your mind start saying)\n"
    "- C: Consequences (what did you feel or do)\n"
    "- D: Dispute (how can you challenge this belief)\n"
    "- E: Effective new belief (What kind of belief could you hold instead)"
)
STEPS = {
    "directive": f"The ABCDE technique can really help. It breaks down thoughts into five steps:\n\n{LIST}\n\n"
                 "Ready to dive into a real life situation?",
    "reflective": f"The ABCDE technique can help reflect on these thoughts by breaking them down:\n\n{LIST}\n\n"
                  "Are you ready to dive into a real life situation?",
    "supportive": f"The ABCDE technique is a kind way to help break these thoughts down:\n\n{LIST}\n\n"
                  "Would you like to try diving into a real life situation together?",
}


def test_the_five_steps_are_the_clients_in_every_style(abcde):
    """The client's sequence document, 2026-11-18, minus the openers that answer only Not sure."""
    from mani.chat.techniques import steps_text

    for style, text in STEPS.items():
        assert steps_text(as_framework(abcde), style) == text, style


def test_the_worked_example_runs_a_to_e(abcde):
    from mani.chat.techniques import example_text

    example = example_text(as_framework(abcde))
    assert "my child is sick" in example and "one step at a time" in example


def test_when_a_stage_counts_as_answered_keeps_the_clients_reading(abcde):
    """Lolly, 2026-10-22: A counts only what happened as the event. E is the new belief alone (2026-11-18)."""
    stages = abcde["stages"]
    assert "rather than as their interpretation of it" in stages["activate"]["ready_when"]
    assert "is not the new belief" in stages["effective"]["ready_when"], (
        "muhammad, 2026-11-18: E ends on the new belief, as the client's sequence document does")
    assert "path" not in stages["effective"]["ready_when"]
