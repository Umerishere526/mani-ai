# ABOUTME: The specifications' own "responses MANI must avoid" examples, as assertions.
# ABOUTME: Labelled data from the specs themselves - no model call, so it runs every time.

from __future__ import annotations

import pathlib
import re

import pytest

from mani.chat import repairs
from tests.evals import validators

CONTENT_DIR = pathlib.Path(__file__).resolve().parents[2] / "content"
FRAMEWORKS_DIR = CONTENT_DIR / "frameworks"
PROMPTS_DIR = CONTENT_DIR / "prompts"

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


def test_a_lead_in_clause_is_not_counted_as_a_second_question():
    """Observed live in the eval harness: 'who' inside a relative clause and the lead-in
    'When' were both counted as separate questions, flagging a single real question."""
    reply = (
        "When you think about the people who messaged you, what is the most prominent "
        "thought that comes to mind?"
    )
    assert validators.check(reply, "", in_framework=True) == []


def test_a_comma_separated_stack_of_questions_is_still_caught():
    """The specification's own forbidden example - kept as an explicit regression alongside
    the parametrized FORBIDDEN case, since this is exactly the shape the fix must not lose."""
    reply = (
        "What happened, what did you think, how did you feel, and what evidence "
        "challenges it?"
    )
    findings = validators.check(reply, "My manager criticized my presentation.", in_framework=True)
    assert "multiple questions" in {f.rule for f in findings}


def test_a_long_explanation_is_caught():
    lecture = " ".join(
        ["People sometimes take criticism as evidence that they are not competent."] * 12
    )
    assert "long explanation" in {f.rule for f in validators.check(lecture, "", in_framework=True)}


def test_consecutive_replies_that_open_the_same_way_are_caught():
    """Observed live: all three styles opened with "I'm here." A formula forming is exactly
    the drift a person notices by eye and no per-reply check can see, since each reply is
    fine on its own."""
    findings = validators.repeated_openers([
        "I'm here. What happened?",
        "I'm here with you. What was it about the text?",
    ])
    assert [f.rule for f in findings] == ["repeated opener"]


def test_replies_that_start_differently_are_left_alone():
    assert validators.repeated_openers([
        "I'm here. What happened?",
        "She was short with you. What did that mean to you?",
        "You keep replaying it. Which part comes back?",
    ]) == []


def test_presence_may_be_said_in_any_style_while_openers_still_vary():
    """muhammad, 2026-09-24: presence may be said in any style when the moment calls for it.
    What stays forbidden is opening the same way twice, the failure that once had all three
    styles opening with "I'm here." """
    base = (PROMPTS_DIR / "mani_base.md").read_text()
    response_format = (PROMPTS_DIR / "response_format.md").read_text()
    assert "say it simply, in any style" in base
    assert "Do not open your new reply the same way." in " ".join(response_format.split())


def test_every_style_value_the_schema_allows_is_taught():
    """The schema asks the model to declare the shape it used. Any value it can return and was
    never taught is one it will either avoid entirely or use without meaning. Shapes are
    taught in a table, so each is pinned to the row that defines it."""
    from mani.llm.schema import SHAPES

    base = (PROMPTS_DIR / "mani_base.md").read_text().lower()

    for name in SHAPES:
        assert f"| {name} |" in base, f"schema allows shape {name!r}, prompt never teaches it"


def test_a_capsule_that_judges_the_person_is_caught():
    """Observed live: a reply offered "I'm overthinking it" as a button. A label is the one
    thing in a reply the person may send back as their own words, so it cannot hand them a
    judgment about themselves to press."""
    findings = validators.check_capsules(
        ["Tell me more", "I'm overthinking it"], "She was short with me."
    )
    assert "capsule judges them" in {f.rule for f in findings}


def test_a_capsule_naming_a_feeling_they_did_not_use_is_caught():
    findings = validators.check_capsules(
        ["It's frustrating", "Not sure yet"], "She ended the conversation."
    )
    assert "capsule puts feelings in their mouth" in {f.rule for f in findings}


def test_neutral_capsules_pass():
    """The replacements the specification itself gives for the bad examples above."""
    assert validators.check_capsules(
        ["Tell me more", "Not sure yet", "Something else"], "She was short with me."
    ) == []


def test_a_capsule_mirroring_their_own_word_is_allowed():
    """Same rule as the prose: their word is theirs to reflect back."""
    assert validators.check_capsules(["Still hurt"], "it still hurt afterwards") == []


def test_every_framework_still_carries_its_negative_set():
    """The examples above are transcribed from these tables. If a framework file loses
    its table, this set silently stops reflecting the specification it came from."""
    for path in sorted(FRAMEWORKS_DIR.glob("*.md")):
        body = path.read_text()
        assert "Responses MANI must avoid" in body, f"{path.name} has no negative set"


# The words a stage's ask may not carry. Every ask is sent into every conversation that
# reaches its stage, so a person or detail from a framework's worked example ("her silence",
# "your manager") is handed to people it has nothing to do with, and an author's note to
# the writer ("- use X only if ...") can be read back to them.
_EXAMPLE_PEOPLE = re.compile(
    r"\b(she|her|he|him|his|manager|boss|sister|brother|mother|father|partner|friend)\b",
    re.IGNORECASE,
)
_AUTHOR_NOTE = re.compile(r" - use | only if | only when ", re.IGNORECASE)


def _asks():
    from scripts.seed import parse_framework

    for path in sorted(FRAMEWORKS_DIR.glob("*.md")):
        framework = parse_framework(path)
        for stage, body in framework["stages"].items():
            for style, text in body["ask"].items():
                yield f"{path.stem}.{stage}.{style}", text


@pytest.mark.parametrize("where,text", list(_asks()))
def test_a_stage_ask_carries_nothing_from_a_worked_example(where, text):
    assert not _EXAMPLE_PEOPLE.search(text), f"{where} names someone: {text}"
    assert not _AUTHOR_NOTE.search(text), f"{where} carries an author note: {text}"
    feelings = sorted(repairs.words(text) & repairs.FEELING_WORDS)
    assert not feelings, f"{where} hands them a feeling they may not have named: {feelings}"


def test_staying_on_a_stage_is_not_told_to_repeat_the_same_wording():
    """Observed live (2026-09-24): ABCDE's activate stage asked for 'the literal words your
    manager used' three times in a row, near-verbatim, while the person kept answering with
    something else. The prompt now says explicitly not to do that."""
    base = (PROMPTS_DIR / "mani_base.md").read_text()
    assert "never ask twice for the same thing the same way" in base
