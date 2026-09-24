# ABOUTME: Deterministic checks for the failures every framework specification names.
# ABOUTME: Pattern assertions on a reply's text - no model call, so these can gate CI.

from __future__ import annotations

import re
from dataclasses import dataclass

# The capsule vocabulary lives beside the code that enforces it, so the eval and the runtime
# cannot drift into disagreeing about which words are which.
from mani.chat.repairs import (
    FEELING_WORDS,
    MAX_CAPSULE_WORDS,
    SELF_JUDGMENTS,
    WORD,
    words,
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
    "really significant", "so heavy", "overwhelming", "burden",
)

# A question start, not any occurrence of the word: the specification's own bad example
# ("What happened, what did you think, how did you feel, and what evidence challenges it?")
# is a comma-separated stack of clauses each beginning with one of these words. Matching
# every occurrence anywhere in the sentence also caught "who" as a relative pronoun inside
# a clause ("the people who messaged you") and "when" opening a single lead-in clause before
# one real question - neither is a second question. Requiring the word to sit at the very
# start of the reply, or right after a clause-separating comma, is the same shape the
# specification's own example has and excludes both false positives.
_INTERROGATIVE = re.compile(
    r"(?:^|,\s*(?:and\s+)?)\s*(what|how|why|when|where|which|who)\b", re.IGNORECASE
)

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


def _hits(text: str, phrases: tuple[str, ...]) -> list[str]:
    lowered = text.lower()
    return [phrase for phrase in phrases if phrase in lowered]


def introduced_feelings(reply: str, user_message: str) -> list[str]:
    """Feeling words the reply uses that the person did not.

    Present in the reply and absent from the message - which is the shape that matters.
    Checking the reply alone would flag the mirroring the same prompt asks for.
    """
    said = words(user_message)
    return sorted(w for w in words(reply) & FEELING_WORDS if w not in said)


# Places the client's own wording asks two questions in one reply, so a second "?" there is
# the specification, not Mani stacking questions: the Supportive body check-in, and the check
# plus "what next" that ends every framework (docs/specs/conversational-styles.md).
_CLIENT_DOUBLE_QUESTIONS = (
    re.compile(r"can we check in for a moment\?", re.IGNORECASE),
    re.compile(r"\?[^?]*what would you like to do next\?", re.IGNORECASE),
)


def question_count(reply: str) -> int:
    allowed = sum(1 for pattern in _CLIENT_DOUBLE_QUESTIONS if pattern.search(reply))
    return max(reply.count("?") - allowed, min(reply.count("?"), 1))


# Two shared leading words is an opening, not a coincidence: "I'm here", "You said", "I hear".
# One is - "What" begins a great many different questions.
SHARED_OPENER_WORDS = 2


def _shared_prefix(first: str, second: str) -> list[str]:
    """The words two replies begin with in common.

    A prefix rather than a fixed-width slice, because the repetition that matters is not a
    fixed length: "I'm here." and "I'm here with you." share an opening, and comparing the
    first three words of each would call them different.
    """
    a, b = WORD.findall(first.lower()), WORD.findall(second.lower())
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


MAX_CAPSULES = 3


def check_capsules(labels: list[str], user_message: str) -> list[Finding]:
    """The buttons under a reply, which are a separate surface from its text.

    A label is the one thing in a reply the person may send back as their own words, so it
    carries a stricter rule than the prose does: it may not name a feeling, characterise the
    situation, or judge them. Checking only the reply text misses it entirely.
    """
    findings: list[Finding] = []
    said = words(user_message)

    for label in labels:
        introduced = sorted(w for w in words(label) & FEELING_WORDS if w not in said)
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

    word_count = len(reply.split())
    if word_count > MAX_WORDS:
        findings.append(
            Finding("long explanation", f"{word_count} words, teaching not responding")
        )

    return findings


_ANNOUNCED_PRESENCE = ("i'm here", "i am here", "i'm listening", "i am listening",
                       "i'm not going anywhere")


def style_findings(reply: str, style: str) -> list[Finding]:
    """The rules in mani_base's "The three styles" that a reply can be checked against.

    Saying presence out loud is a Supportive move only. Reflective shows it listened by what it
    reflects, never by "I hear you". Direct may open on "I" - the client's own Direct lines are
    "I'm sorry you're feeling this way" and "I have a structured approach" - just not on
    announcing that it is there, which the presence rule already catches.
    """
    findings: list[Finding] = []
    lowered = reply.lower().replace("\u2019", "'")
    if style != "supportive":
        announced = [p for p in _ANNOUNCED_PRESENCE if p in lowered]
        if announced:
            findings.append(Finding("off-style", f"presence announced outside Supportive: {announced}"))
    if style == "reflective" and "i hear you" in lowered:
        findings.append(Finding("off-style", "a Reflective reply used \"I hear you\""))
    return findings


_INVITES = re.compile(r"\b(tell me|say more|walk me through)\b", re.IGNORECASE)


def unasked_before_offer(replies: list[tuple[str, bool]]) -> list[Finding]:
    """Replies that ask nothing while Mani is still understanding the issue.

    The client's cadence spends the first two to four exchanges asking, checking and
    confirming. `replies` pairs each reply with whether it offered a framework; every reply up
    to and including the first offer must carry a question - the offer's own being its
    permission question.
    """
    findings: list[Finding] = []
    for text, offered in replies:
        # An invitation asks too: the client's own "Tell me what is happening right now."
        if "?" not in text and not _INVITES.search(text):
            findings.append(Finding("stalled", f"no question before an offer: {text[:60]!r}"))
        if offered:
            break
    return findings


HANDOFF_BUTTONS = ("chat more", "go to library")


def missing_handoff(turns: list[tuple[str | None, list[str]]], messages: list[str] | None = None) -> list[Finding]:
    """The reply that closes a framework must offer Chat More and Go to Library.

    `turns` pairs the framework phase after each reply with that reply's button labels. The
    closing reply is the one after the body check-in: the phase goes from `somatic` to cleared.
    `messages` are what the person sent; if they had already chosen one of the two, the
    closing reply rightly carries neither.
    """
    findings: list[Finding] = []
    sent = messages or [""] * len(turns)
    for index, ((before, _), (after, buttons)) in enumerate(zip(turns, turns[1:], strict=False), 1):
        if sent[index].strip().lower() in HANDOFF_BUTTONS:
            continue
        if before == "somatic" and after is None:
            have = {b.strip().lower() for b in buttons}
            missing = [b for b in HANDOFF_BUTTONS if b not in have]
            if missing:
                findings.append(Finding("no hand-off", f"framework ended without {missing}"))
    return findings


_EARLIER_CHAT = re.compile(
    r"\b(last time|you mentioned before|earlier you said|you told me before|"
    r"previous conversation|last conversation|remember when you)\b",
    re.IGNORECASE,
)


def references_other_chat(reply: str, markers: list[str], said_here: str) -> list[Finding]:
    """A new chat may be shaped by memory but must never cite the old one.

    `markers` are words only the earlier chat used; one appearing here when the person has
    not said it in this chat means Mani brought it across.
    """
    findings: list[Finding] = []
    if _EARLIER_CHAT.search(reply):
        findings.append(Finding("cites another chat", _EARLIER_CHAT.search(reply).group(0)))
    lowered, said = reply.lower(), said_here.lower()
    carried = [m for m in markers if m.lower() in lowered and m.lower() not in said]
    if carried:
        findings.append(Finding("cites another chat", f"brought across {carried}"))
    return findings


_QUESTION = re.compile(r"[^.!?\n]*\?")


def _last_question_words(reply: str) -> set[str]:
    questions = _QUESTION.findall(reply)
    return set(re.findall(r"[a-z']+", questions[-1].lower())) if questions else set()


def repeated_question(replies: list[str], overlap: float = 0.8) -> list[Finding]:
    """The same question asked in consecutive replies - how a stalled stage looks to the
    person. Compared by word overlap, so a light rewording still counts as the same question."""
    findings: list[Finding] = []
    for before, after in zip(replies, replies[1:], strict=False):
        a, b = _last_question_words(before), _last_question_words(after)
        if a and b and len(a & b) / len(a | b) >= overlap:
            findings.append(Finding("repeated question", " ".join(sorted(a & b))[:80]))
    return findings
