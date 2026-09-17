# ABOUTME: Deterministic checks for the failures every framework specification names.
# ABOUTME: Pattern assertions on a reply's text - no model call, so these can gate CI.

from __future__ import annotations

import re
from dataclasses import dataclass

# The feeling words the specifications are strict about: a reply may use one only if the
# person used it first. "MANI never introduces a feeling word the user did not use."
FEELING_WORDS = frozenset(
    {
        "abandoned", "afraid", "angry", "anxious", "ashamed", "betrayed", "broken",
        "crushed", "defeated", "dejected", "depressed", "desperate", "devastated",
        "disappointed", "distressed", "embarrassed", "exhausted", "fearful", "frustrated",
        "furious", "guilty", "helpless", "hopeless", "humiliated", "hurt", "insecure",
        "isolated", "lonely", "lost", "miserable", "overwhelmed", "panicked", "rejected",
        "resentful", "sad", "scared", "stressed", "terrified", "trapped", "unloved",
        "unwanted", "upset", "worried", "worthless",
        # The adjectival forms, which describe the situation rather than the person and are
        # the shape a capsule label usually takes: "It's frustrating", "It's exhausting".
        "depressing", "devastating", "draining", "embarrassing", "exhausting",
        "frustrating", "humiliating", "isolating", "overwhelming", "terrifying",
        "upsetting", "worrying",
    }
)

# Clinical vocabulary. The specifications forbid naming the user's thinking, in every
# framework: "MANI does not use clinical language with the user."
CLINICAL_TERMS = (
    "catastrophizing", "catastrophising", "cognitive distortion", "distorted thinking",
    "mind-reading", "mind reading", "irrational belief", "maladaptive",
    "black-and-white thinking", "all-or-nothing thinking", "cognitive bias",
    "negative self-talk", "rumination",
)

# Reassurance the user has not earned from their own evidence, and outcomes MANI cannot
# promise. Listed in every framework's "responses to avoid" table.
FORCED_POSITIVITY = (
    "everything will be fine", "everything will be okay", "it will all work out",
    "things will get better", "i am sure they", "i'm sure they", "you are talented",
    "you're talented", "you are amazing", "you're amazing", "don't be so hard on yourself",
    "do not be so hard on yourself",
)

# Claims about another person's intention. "MANI cannot know his intention."
ASSUMED_MOTIVE = (
    "he probably", "she probably", "they probably", "he didn't mean", "he did not mean",
    "she didn't mean", "she did not mean", "they didn't mean", "they did not mean",
    "was trying to help", "were trying to help", "did not intend", "didn't intend",
)

# Scale and weight the person did not put there themselves. This one is already a rule in
# response_format.md's own constraints, which is why it belongs in the same set.
ADDED_SCALE = (
    "a lot", "so much", "weighing on you", "that is tough", "that's tough",
    "that is hard", "that's hard", "so exhausting", "must be so", "such a big",
    "really significant", "so heavy", "overwhelming",
)

_WORD = re.compile(r"[a-z']+")
_INTERROGATIVE = re.compile(r"\b(what|how|why|when|where|which|who)\b", re.IGNORECASE)

# "2-4 short sentences typical", from response_format.md's own length constraint. Past
# this a reply is teaching rather than responding, which every framework forbids.
MAX_WORDS = 80

# Three interrogatives inside one question mark is the specification's own example of
# stacking - "What happened, what did you think, how did you feel, and what evidence
# challenges it?" is one '?' and four questions.
MAX_INTERROGATIVES = 3


@dataclass(frozen=True)
class Finding:
    """One rule a reply broke, named the way the specifications name it."""

    rule: str
    detail: str

    def __str__(self) -> str:
        return f"{self.rule}: {self.detail}"


def _words(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


def _hits(text: str, phrases: tuple[str, ...]) -> list[str]:
    lowered = text.lower()
    return [phrase for phrase in phrases if phrase in lowered]


def introduced_feelings(reply: str, user_message: str) -> list[str]:
    """Feeling words the reply uses that the person did not.

    Present in the reply and absent from the message - which is the shape that matters.
    Checking the reply alone would flag the mirroring the same prompt asks for.
    """
    said = _words(user_message)
    return sorted(w for w in _words(reply) & FEELING_WORDS if w not in said)


def question_count(reply: str) -> int:
    return reply.count("?")


# Two shared leading words is an opening, not a coincidence: "I'm here", "You said", "I hear".
# One is - "What" begins a great many different questions.
SHARED_OPENER_WORDS = 2


def _shared_prefix(first: str, second: str) -> list[str]:
    """The words two replies begin with in common.

    A prefix rather than a fixed-width slice, because the repetition that matters is not a
    fixed length: "I'm here." and "I'm here with you." share an opening, and comparing the
    first three words of each would call them different.
    """
    a, b = _WORD.findall(first.lower()), _WORD.findall(second.lower())
    shared: list[str] = []
    for x, y in zip(a, b, strict=False):
        if x != y:
            break
        shared.append(x)
    return shared


def repeated_openers(replies: list[str]) -> list[Finding]:
    """Replies that begin the same way as the one before them.

    The prompt states this rule, but the model cannot reliably self-police it: it has no
    count of what it has already said, and on the first turn of a conversation there is no
    history to check against at all. Every reply here is fine read on its own - the fault
    only exists in the sequence, which is why it needs checking here and not per reply.
    """
    findings: list[Finding] = []
    for previous, current in zip(replies, replies[1:], strict=False):
        shared = _shared_prefix(previous, current)
        if len(shared) >= SHARED_OPENER_WORDS:
            findings.append(
                Finding("repeated opener", f"two replies in a row open {' '.join(shared)!r}")
            )
    return findings


# Judgments a person may hold about themselves but must never be handed as a button to press.
# Observed live: a reply offered "I'm overthinking it" as a capsule.
SELF_JUDGMENTS = (
    "overthinking", "over thinking", "being dramatic", "too sensitive", "overreacting",
    "over reacting", "being silly", "being stupid", "my fault", "i'm weak", "i am weak",
    "i'm broken", "i am broken", "not enough", "being needy", "being difficult",
)

MAX_CAPSULES = 3
MAX_CAPSULE_WORDS = 4


def check_capsules(labels: list[str], user_message: str) -> list[Finding]:
    """The buttons under a reply, which are a separate surface from its text.

    A label is the one thing in a reply the person may send back as their own words, so it
    carries a stricter rule than the prose does: it may not name a feeling, characterise the
    situation, or judge them. Checking only the reply text misses it entirely.
    """
    findings: list[Finding] = []
    said = _words(user_message)

    for label in labels:
        introduced = sorted(w for w in _words(label) & FEELING_WORDS if w not in said)
        if introduced:
            findings.append(
                Finding("capsule puts feelings in their mouth", f"{label!r}: {introduced}")
            )
        judgments = [p for p in SELF_JUDGMENTS if p in label.lower()]
        if judgments:
            findings.append(
                Finding("capsule judges them", f"{label!r}: {judgments}")
            )
        if len(label.split()) > MAX_CAPSULE_WORDS:
            findings.append(
                Finding("capsule too long", f"{label!r} is {len(label.split())} words")
            )

    if len(labels) > MAX_CAPSULES:
        findings.append(Finding("too many capsules", f"{len(labels)} offered"))

    lowered = [label.strip().lower() for label in labels]
    if len(set(lowered)) != len(lowered):
        findings.append(Finding("duplicate capsule", f"{labels}"))

    return findings


def check(reply: str, user_message: str, *, in_framework: bool = False) -> list[Finding]:
    """Every rule this reply broke. Empty means it passed.

    `in_framework` turns on the rules that only apply once a framework is running: inside
    one, every mirror must carry a question and exactly one question is allowed. Outside
    one, `mani_base` explicitly permits a reply with no question at all.
    """
    findings: list[Finding] = []

    introduced = introduced_feelings(reply, user_message)
    if introduced:
        findings.append(Finding("labelling", f"feeling words the user did not use: {introduced}"))

    for rule, phrases in (
        ("clinical label", CLINICAL_TERMS),
        ("forced positivity", FORCED_POSITIVITY),
        ("assumed motive", ASSUMED_MOTIVE),
    ):
        hits = _hits(reply, phrases)
        if hits:
            findings.append(Finding(rule, f"{hits}"))

    # Scale gets the same treatment as feeling words: the rule is "if they did not describe
    # the scale, neither do you", so a phrase the person used first is theirs to mirror.
    said = user_message.lower()
    added = [p for p in _hits(reply, ADDED_SCALE) if p not in said]
    if added:
        findings.append(Finding("added scale", f"{added}"))

    questions = question_count(reply)
    interrogatives = len(_INTERROGATIVE.findall(reply))
    if questions > 1:
        findings.append(Finding("multiple questions", f"{questions} questions in one reply"))
    elif questions == 1 and interrogatives >= MAX_INTERROGATIVES:
        # One question mark, several questions inside it - the specification's own example
        # of rushing the process reads as a single sentence.
        findings.append(
            Finding("multiple questions", f"{interrogatives} questions under one '?'")
        )

    if in_framework and questions == 0:
        findings.append(Finding("standalone mirror", "no question, inside a framework"))

    words = len(reply.split())
    if words > MAX_WORDS:
        findings.append(Finding("long explanation", f"{words} words, teaching not responding"))

    return findings
