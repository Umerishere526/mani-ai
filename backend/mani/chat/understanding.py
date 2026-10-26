# ABOUTME: What Mani understands of the person so far: the feelings they named, where its reading of the heart of it
# ABOUTME: stands, and the case they confirmed. Pure functions: this turn merged into the stored record, and its [ctx] value.

from __future__ import annotations

from mani.chat import context
from mani.llm.schema import Check, UnderstandingUpdate

KEYS = ("feeling", "heart", "case")
LIMIT = 200
# The confirmed case says the conflict, what they want and what is stopping them, a few sentences.
CASE_LIMIT = 3 * LIMIT
# Every feeling word they name gathers over the conversation and is never taken away.
FEELING_SEPARATOR = ", "
# Where the reply last judged its reading of the heart of it: the central conflict not clear yet, said back and
# agreed, or agreed with what they want and what is stopping them also known (muhammad, 2026-10-26). Only a reply
# that judges it ready may check its understanding (R33).
READY = "ready"


def ready(stored: dict[str, str]) -> bool:
    """Whether the last reply judged the heart of it ready to check."""
    return stored.get("heart") == READY


def _gathered(stored: str | None, value: str) -> str:
    """The feelings in `stored` with those in `value` added after them, none twice. When the whole no longer fits,
    the oldest after the first is dropped: the first is what they came with."""
    entries: list[str] = []
    for entry in [*(stored or "").split(FEELING_SEPARATOR.strip()), *value.split(FEELING_SEPARATOR.strip())]:
        entry = entry.strip()
        if entry and entry.lower() not in (e.lower() for e in entries):
            entries.append(entry)
    while len(FEELING_SEPARATOR.join(entries)) > LIMIT and len(entries) > 2:
        entries.pop(1)
    return FEELING_SEPARATOR.join(entries)[:LIMIT].rstrip()


def merge(stored: dict[str, str], update: UnderstandingUpdate | None, heart: str | None) -> dict[str, str]:
    """The record after this turn: the feelings their message names added to those kept, and where the reply
    judged the heart of it, replacing the last judgement. A null or blank value keeps what is stored."""
    merged = {key: stored[key] for key in KEYS if stored.get(key)}
    feeling = " ".join((getattr(update, "feeling", None) or "").split())
    if feeling:
        merged["feeling"] = _gathered(merged.get("feeling"), feeling)
    if heart:
        merged["heart"] = heart
    return merged


def render(stored: dict[str, str]) -> str | None:
    """The record as the value of its [ctx] line, or None when nothing is stored yet."""
    parts = [f"{key}: {context.disarm(stored[key])}" for key in KEYS if stored.get(key)]
    return "; ".join(parts) or None


def usable(check: Check | None) -> bool:
    """Whether a reply's check says the conflict, what they want and what is stopping them, and asks whether
    it is right."""
    return bool(check and all(
        (value or "").strip() for value in (check.conflict, check.want, check.in_the_way, check.question)
    ))


def merge_check(stored: dict[str, str], summary: str) -> dict[str, str]:
    """The record after a stored check: its summary is the case, the conflict, what they want and what is
    stopping them, which a yes makes what the questions are about."""
    return {**stored, "case": " ".join(summary.split())[:CASE_LIMIT].rstrip()}
