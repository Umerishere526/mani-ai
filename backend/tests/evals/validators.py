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
    "a lot to deal with", "so much to carry", "weighing on you", "that is tough",
    "that's tough", "that is hard", "that's hard", "so exhausting", "must be so",
    "such a big", "really significant",
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
        ("added scale", ADDED_SCALE),
    ):
        hits = _hits(reply, phrases)
        if hits:
            findings.append(Finding(rule, f"{hits}"))

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
