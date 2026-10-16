# ABOUTME: What Mani understands of the person so far (feeling, body, issue, core issue, what is in their control).
# ABOUTME: Pure functions: this turn's reported update merged into the stored record, and its [ctx] value.

from __future__ import annotations

from mani.chat import context
from mani.llm.schema import Check, UnderstandingUpdate

KEYS = ("feeling", "body", "issue", "core_issue", "in_their_control", "comes_down_to")
LIMIT = 200
# The client's steps before Mani checks its understanding, in order: the problem, the core issue under
# it, what is in their control (meeting and cheat sheet, 2026-10-13). Each is taken only once the one
# before it was stored on an earlier turn, so each gets an exchange of its own (spec 0006).
STEPS = {"issue": "problem", "core_issue": "core_issue", "in_their_control": "control"}


def _in_order(key: str, before: dict[str, str]) -> bool:
    """Whether `key` may be stored this turn: it is not a step, or every step before it was stored."""
    if key not in STEPS:
        return True
    earlier = list(STEPS)[: list(STEPS).index(key)]
    return all(before.get(step) for step in earlier)


def next_step(stored: dict[str, str]) -> str | None:
    """The first step still missing, by its name in [ctx], or None once all three are stored."""
    return next((name for key, name in STEPS.items() if not stored.get(key)), None)


def merge(
    stored: dict[str, str], update: UnderstandingUpdate | None, *, before: dict[str, str] | None = None,
) -> dict[str, str]:
    """The record after this turn. Per key, a null or blank value keeps what is stored; anything
    else replaces it, on one line (which also keeps it from opening a line of its own in [ctx]) and
    cut to LIMIT characters. A step is taken only in order, judged on `before`, the record as this
    turn began (`stored` when not given)."""
    before = stored if before is None else before
    merged = {key: stored[key] for key in KEYS if stored.get(key)}
    for key in KEYS:
        value = " ".join((getattr(update, key, None) or "").split())
        if value and _in_order(key, before):
            merged[key] = value[:LIMIT].rstrip()
    return merged


def render(stored: dict[str, str]) -> str | None:
    """The record as the value of its [ctx] line, each step named even while it is missing, or None
    when nothing is stored yet."""
    if not any(stored.get(key) for key in KEYS):
        return None
    parts = [
        f"{key}: {context.disarm(stored[key])}" if stored.get(key) else f"{key}: missing"
        for key in KEYS if stored.get(key) or key in STEPS
    ]
    return "; ".join(parts)


def usable(check: Check | None) -> bool:
    """Whether a reply's check holds what Mani understands, the problem, what lies under it and what is
    in their control, and says what it all comes down to, the only part sent, with its question."""
    return bool(check and all(
        (value or "").strip()
        for value in (check.problem, check.core_issue, check.in_their_control, check.comes_down_to,
                      check.question)
    ))


def merge_check(stored: dict[str, str], check: Check) -> dict[str, str]:
    """The record after a stored check: its problem is the issue they are dealing with, and what it
    came down to, which they confirmed, is kept too, since it is closer to what they hold than their
    opening line (live, 2026-10-13)."""
    merged = merge(stored, UnderstandingUpdate(
        issue=check.problem, core_issue=check.core_issue, in_their_control=check.in_their_control,
    ))
    came_to = " ".join((check.comes_down_to or "").split())
    if came_to:
        merged["comes_down_to"] = came_to[:LIMIT].rstrip()
    return merged
