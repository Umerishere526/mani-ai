# ABOUTME: Checks on the model's reply that cost no model call: what it missed that code cannot fix.
# ABOUTME: Pure functions, so each check is a unit test; the orchestrator logs the misses.

from __future__ import annotations

import re

from mani.llm.schema import NO_QUESTION_SHAPES, Reply

_QUESTION = re.compile(r"[^.!?\n]*\?")
REPEAT_OVERLAP = 0.7


def _last_question_words(text: str) -> set[str]:
    questions = _QUESTION.findall(text)
    return set(re.findall(r"[a-z']{4,}", questions[-1].lower())) if questions else set()


def repeats(text: str, last_mani_text: str | None) -> bool:
    """Whether a reply's closing question is, by its words, the question Mani asked last turn.
    A person who answers a question and gets it back unchanged is stuck, however it is reworded."""
    now, before = _last_question_words(text), _last_question_words(last_mani_text or "")
    return bool(now and before and len(now & before) / min(len(now), len(before)) >= REPEAT_OVERLAP)


def misses(
    reply: Reply,
    *,
    offered: str | None,
    offer_dropped: str | None,
    offer_due: bool,
    needs_question: bool,
    last_mani_text: str | None,
) -> list[str]:
    """What the draft got wrong that code cannot fix, named for the log. Empty when it stands.
    None of these costs a second call: they are counted, so how often each happens is known.
    `offered` is the set the sent reply offers, as code rendered it."""
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
    if not technique and offer_due and reply.heading_toward:
        notes.append("offer due and not made")
    return notes
