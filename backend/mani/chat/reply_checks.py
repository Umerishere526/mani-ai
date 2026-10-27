# ABOUTME: Checks on the model's reply that cost no model call: what it missed that code cannot fix.
# ABOUTME: Pure functions, so each check is a unit test; the orchestrator logs the misses.

from __future__ import annotations

import re

from mani.llm.schema import Reply

_QUESTION = re.compile(r"[^.!?\n]*\?")
REPEAT_OVERLAP = 0.7
# Figures of speech people have named as artificial (2026-10), counted in the log, never fixed. Matched as whole
# phrases in a reply.
FIGURES = re.compile(
    r"\b(?:hold(?:ing)? (?:onto|on to|space|you|this|that)|carry(?:ing)? (?:this|that)|sit(?:ting)? with"
    r"|weigh(?:s|ing)? on you)\b",
    re.IGNORECASE,
)
# Words that say nothing about a case, so sharing them is no sign a question carries it.
_COMMON = frozenset({
    "that", "this", "with", "they", "them", "what", "your", "have", "from", "been", "about", "feel", "feels",
    "want", "wants", "means", "mean", "like", "when", "does", "were", "would", "there", "their", "because",
})


def _last_question_words(text: str) -> set[str]:
    questions = _QUESTION.findall(text)
    return set(re.findall(r"[a-z']{4,}", questions[-1].lower())) if questions else set()


def repeats(text: str, last_mani_text: str | None) -> bool:
    """Whether a reply's closing question is, by its words, the question Mani asked last turn.
    A person who answers a question and gets it back unchanged is stuck, however it is reworded."""
    now, before = _last_question_words(text), _last_question_words(last_mani_text or "")
    return bool(now and before and len(now & before) / min(len(now), len(before)) >= REPEAT_OVERLAP)


def figures(text: str) -> list[str]:
    """The figures of speech in a reply, lower-cased, in the order they appear."""
    return [match.group(0).lower() for match in FIGURES.finditer(text)]


def lacks_case(text: str, case: str | None) -> bool:
    """Whether a reply that should carry the case shares no word of substance with it. With no case
    stored there is nothing to carry."""
    wanted = set(re.findall(r"[a-z']{4,}", (case or "").lower())) - _COMMON
    return bool(wanted) and not wanted & set(re.findall(r"[a-z']{4,}", text.lower()))


def misses(
    reply: Reply,
    *,
    offered: str | None,
    offer_dropped: str | None,
    needs_question: bool,
    last_mani_text: str | None,
    reach_unjudged: bool = False,
    case: str | None = None,
) -> list[str]:
    """What the draft got wrong that code cannot fix, named for the log. Empty when it stands.
    None of these costs a second call: they are counted, so how often each happens is known.
    `offered` is the set the sent reply offers, as code rendered it. `reach_unjudged` is a stage the walk reached that the reply left without a
    next_stage judgement. `case` is what they feel and the case they confirmed, given only where the
    stage the reply asks carries the case."""
    notes: list[str] = []
    technique = offered
    if offer_dropped:
        notes.append(f"offer unusable: {offer_dropped}")
    if not technique and repeats(reply.text, last_mani_text):
        notes.append("repeats the last question")
    if needs_question and not technique and "?" not in reply.text:
        notes.append("asks no question")
    if reach_unjudged:
        notes.append("reach unjudged")
    if case is not None and lacks_case(reply.text, case):
        notes.append("case missing")
    if found := figures(reply.text):
        notes.append(f"figure of speech: {', '.join(found)}")
    return notes
