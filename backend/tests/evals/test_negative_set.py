# ABOUTME: The specifications' own "responses MANI must avoid" examples, as assertions.
# ABOUTME: Labelled data from the specs themselves - no model call, so it runs every time.

from __future__ import annotations

import pathlib

import pytest

from tests.evals import validators

FRAMEWORKS_DIR = pathlib.Path(__file__).resolve().parents[2] / "frameworks"

# Transcribed from the "Responses MANI must avoid" table in each framework file, with the
# user message that preceded them in that framework's worked example. The rule named is
# the specification's own label for the failure.
FORBIDDEN = [
    (
        "labelling",
        "You felt ashamed, rejected, and anxious. What did you do next?",
        "She questioned two of my recommendations in front of the team.",
    ),
    (
        "clinical label",
        "You are catastrophizing. What evidence contradicts that distortion?",
        "I keep thinking I am incompetent.",
    ),
    (
        "multiple questions",
        "What happened, what did you think, how did you feel, and what evidence "
        "challenges it?",
        "My manager criticized my presentation.",
    ),
    (
        "forced positivity",
        "You are talented and successful. Why are you being so hard on yourself?",
        "I keep thinking I am incompetent.",
    ),
    (
        "assumed motive",
        "Your manager was trying to help you improve. Can you see that?",
        "She said my recommendations were not supported.",
    ),
    (
        "labelling",
        "You feel abandoned and insecure. What evidence supports that?",
        "My friend has not answered all day.",
    ),
    (
        "clinical label",
        "You are catastrophizing and mind-reading. What is a more rational thought?",
        "She clearly does not care.",
    ),
    (
        "labelling",
        "You are depressed, isolated, and unmotivated. What could you do today?",
        "I have stopped answering people.",
    ),
    (
        "added scale",
        "That is a lot to deal with. What have you stopped doing?",
        "I have been in bed all day.",
    ),
    (
        "assumed motive",
        "He probably did not mean to disrespect you. What do you want to do?",
        "I wrote a message telling him exactly what I think.",
    ),
]

# From the worked examples in the same files - the conversations the specifications hold
# up as correct. A validator that flags these is worse than no validator.
PERMITTED = [
    (
        "She questioned the support for two recommendations. What did that come to mean "
        "for you?",
        "She said two of my recommendations did not have enough supporting information.",
    ),
    (
        "You stopped speaking and avoided her. What supports the belief that you do not "
        "know what you are doing?",
        "I stopped speaking and avoided her afterward.",
    ),
    (
        "Her silence does not prove that she does not care. What changes when you see it "
        "this way?",
        "She has not answered, but that does not prove she does not care.",
    ),
    (
        "You have stopped answering messages. Which person matters most to respond to?",
        "I have ignored everyone's messages for a week.",
    ),
    (
        "The message remains unsent. Can you stop before sending it?",
        "I wrote a message telling him exactly what I think.",
    ),
    (
        "Their approval is outside your control. What is showing up for you when you "
        "think about that?",
        "I cannot control whether they approve.",
    ),
    # The person used the feeling word first, so the reply may use it back. This is the
    # collision that made an earlier forbidden-word list unusable: mirroring is required.
    (
        "You felt embarrassed. What were you telling yourself at that point?",
        "I felt embarrassed in front of everyone.",
    ),
]


@pytest.mark.parametrize("rule, reply, user_message", FORBIDDEN)
def test_a_forbidden_response_is_caught(rule: str, reply: str, user_message: str):
    findings = validators.check(reply, user_message, in_framework=True)
    assert rule in {f.rule for f in findings}, f"{rule} not caught in: {reply!r} -> {findings}"


@pytest.mark.parametrize("reply, user_message", PERMITTED)
def test_a_correct_response_is_not_flagged(reply: str, user_message: str):
    findings = validators.check(reply, user_message, in_framework=True)
    assert findings == [], f"false positive on a specification example: {findings}"


def test_a_standalone_mirror_is_caught_only_inside_a_framework():
    """`mani_base` explicitly allows a reply with no question outside a framework -
    "presence only" is one of its six shapes. Inside one, every mirror carries a question."""
    mirror = "You stopped speaking and avoided her."

    assert "standalone mirror" in {
        f.rule for f in validators.check(mirror, "I avoided her.", in_framework=True)
    }
    assert validators.check(mirror, "I avoided her.", in_framework=False) == []


def test_a_long_explanation_is_caught():
    lecture = " ".join(
        ["People sometimes take criticism as evidence that they are not competent."] * 12
    )
    assert "long explanation" in {f.rule for f in validators.check(lecture, "", in_framework=True)}


def test_every_framework_still_carries_its_negative_set():
    """The examples above are transcribed from these tables. If a framework file loses
    its table, this set silently stops reflecting the specification it came from."""
    for path in sorted(FRAMEWORKS_DIR.glob("*.md")):
        body = path.read_text()
        assert "Responses MANI must avoid" in body, f"{path.name} has no negative set"
