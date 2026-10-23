# ABOUTME: Checks on the model's reply that cost no model call: what it missed that code cannot fix.
# ABOUTME: Pure functions, so each check is a unit test; the orchestrator logs the misses.

from __future__ import annotations

import re

from mani.llm.schema import NO_QUESTION_SHAPES, Reply

_QUESTION = re.compile(r"[^.!?\n]*\?")
REPEAT_OVERLAP = 0.7
# Figures of speech Mani is told never to use (mani_base.md, how_you_talk): the ones people have named as
# artificial. Matched as whole phrases in a reply.
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


def lacks_stack(text: str, stack: str | None) -> bool:
    """Whether a reply that should carry the stack shares no word of substance with it. With no stack
    stored there is nothing to carry."""
    wanted = set(re.findall(r"[a-z']{4,}", (stack or "").lower())) - _COMMON
    return bool(wanted) and not wanted & set(re.findall(r"[a-z']{4,}", text.lower()))


def misses(
    reply: Reply,
    *,
    offered: str | None,
    offer_dropped: str | None,
    needs_question: bool,
    last_mani_text: str | None,
    check_unusable: bool = False,
    check_too_early: bool = False,
    no_check_by: int | None = None,
    reach_unjudged: bool = False,
    stack: str | None = None,
) -> list[str]:
    """What the draft got wrong that code cannot fix, named for the log. Empty when it stands.
    None of these costs a second call: they are counted, so how often each happens is known.
    `offered` is the set the sent reply offers, as code rendered it. `check_unusable` is a check that
    lacked one of its parts, `check_too_early` one sent before the three steps were found, and
    `no_check_by` their message number when it passes with no check ever made (spec 0006).
    `reach_unjudged` is a stage the walk reached that the reply left without a next_stage judgement.
    `stack` is what they feel, believe it means and want, given only where the stage the reply asks
    carries the case."""
    notes: list[str] = []
    technique = offered
    if offer_dropped:
        notes.append(f"offer unusable: {offer_dropped}")
    if not technique and repeats(reply.text, last_mani_text):
        notes.append("repeats the last question")
    chose_to_ask_nothing = bool(
        reply.style and reply.style.shape.strip().lower() in NO_QUESTION_SHAPES
    )
    if needs_question and not technique and "?" not in reply.text and not chose_to_ask_nothing:
        notes.append("asks no question")
    if check_unusable:
        notes.append("check unusable")
    if check_too_early:
        notes.append("check before the three steps")
    if no_check_by is not None:
        notes.append(f"no check by message {no_check_by}")
    if reach_unjudged:
        notes.append("reach unjudged")
    if stack is not None and lacks_stack(reply.text, stack):
        notes.append("stack missing")
    if found := figures(reply.text):
        notes.append(f"figure of speech: {', '.join(found)}")
    return notes
