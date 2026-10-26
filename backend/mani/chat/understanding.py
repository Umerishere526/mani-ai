# ABOUTME: What Mani understands of the person so far (feelings, issue, core issue, underlying feeling, what else).
# ABOUTME: Pure functions: this turn's reported update merged into the stored record, and its [ctx] value.

from __future__ import annotations

from mani.chat import context
from mani.llm.schema import Check, UnderstandingUpdate

KEYS = ("feeling", "stack", "issue", "core_issue", "underlying_feeling", "comes_down_to", "also")
LIMIT = 200
# What gathers over the conversation instead of being replaced: every feeling they name, the stack of what
# they feel, believe it means and want, the details they raise, and each step of the case (problem, core
# issue, underlying feeling), which grows with everything they say and is never taken away. Each has its
# separator and its size.
GATHERED = {
    "feeling": (", ", LIMIT),
    "stack": ("; ", 3 * LIMIT),
    "issue": ("; ", 3 * LIMIT),
    "core_issue": ("; ", 3 * LIMIT),
    "underlying_feeling": ("; ", 3 * LIMIT),
    "also": ("; ", 2 * LIMIT),
}
# The client's steps before Mani checks its understanding, in order: the problem, the core issue under
# it, the feeling underneath (meeting and cheat sheet, 2026-10-13; the feeling replaced what is in their
# control, muhammad, 2026-10-21). Each is stored whenever they give it, so what they say about it in their
# first message is kept, but counts as found only in order, at most one a turn, so each still gets an
# exchange of its own before the check (muhammad, 2026-10-25: stored out of order, the sister chat was
# checked and offered at her second message).
STEPS = {"issue": "problem", "core_issue": "core_issue", "underlying_feeling": "underlying_feeling"}
# The record's key for the last step counted as found.
FOUND = "found"


def _found(stored: dict[str, str]) -> int:
    """How many steps, in order, count as found."""
    steps = list(STEPS)
    return steps.index(stored[FOUND]) + 1 if stored.get(FOUND) in steps else 0


def next_step(stored: dict[str, str]) -> str | None:
    """The first step not yet found, by its name in [ctx], or None once all three are found."""
    found = _found(stored)
    return list(STEPS.values())[found] if found < len(STEPS) else None


def advance(before: dict[str, str], after: dict[str, str]) -> dict[str, str]:
    """`after`, the record at the end of this turn, with one more step found when it holds the step the
    turn began on (`before`)."""
    found = _found(before)
    if found < len(STEPS) and after.get(list(STEPS)[found]):
        return {**after, FOUND: list(STEPS)[found]}
    return after


def _gathered(stored: str | None, value: str, key: str) -> str:
    """What `stored` holds with the entries of `value` added after it, none twice. When the whole no longer
    fits, the oldest after the first is dropped: the first is what they came with."""
    separator, limit = GATHERED[key]
    entries: list[str] = []
    for entry in [*(stored or "").split(separator.strip()), *value.split(separator.strip())]:
        entry = entry.strip()
        if entry and entry.lower() not in (e.lower() for e in entries):
            entries.append(entry)
    while len(separator.join(entries)) > limit and len(entries) > 2:
        entries.pop(1)
    return separator.join(entries)[:limit].rstrip()


def merge(stored: dict[str, str], update: UnderstandingUpdate | None) -> dict[str, str]:
    """The record after this turn. Per key, a null or blank value keeps what is stored; anything
    else replaces it, on one line (which also keeps it from opening a line of its own in [ctx]) and
    cut to LIMIT characters, except what gathers (GATHERED), which is added to."""
    merged = {key: stored[key] for key in (*KEYS, FOUND) if stored.get(key)}
    for key in KEYS:
        value = " ".join((getattr(update, key, None) or "").split())
        if not value:
            continue
        merged[key] = _gathered(merged.get(key), value, key) if key in GATHERED else value[:LIMIT].rstrip()
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
    """Whether a reply's check says what Mani understands, the problem, what lies under it and the
    feeling underneath, and asks whether it is right. What it comes down to is welcome, not required."""
    return bool(check and all(
        (value or "").strip()
        for value in (check.problem, check.core_issue, check.underlying_feeling, check.question)
    ))


def merge_check(stored: dict[str, str], check: Check) -> dict[str, str]:
    """The record after a stored check: what it came down to, which they confirmed, is kept, since it
    is closer to what they hold than their opening line (live, 2026-10-13). Its problem, core issue and
    feeling sum up what is already stored, so they are not added again."""
    merged = dict(stored)
    came_to = " ".join((check.comes_down_to or "").split())
    if came_to:
        merged["comes_down_to"] = came_to[:LIMIT].rstrip()
    return merged
