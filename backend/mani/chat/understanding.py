# ABOUTME: What Mani understands of the person so far (feelings, issue, core issue, underlying feeling, what else).
# ABOUTME: Pure functions: this turn's reported update merged into the stored record, and its [ctx] value.

from __future__ import annotations

from mani.chat import context
from mani.llm.schema import Check, UnderstandingUpdate

KEYS = ("feeling", "issue", "core_issue", "underlying_feeling", "comes_down_to", "also")
LIMIT = 200
# What gathers over the conversation instead of being replaced: every feeling they name, and the new
# problems and details they raise after the case was found. Each has its separator and its size.
GATHERED = {"feeling": (", ", LIMIT), "also": ("; ", 2 * LIMIT)}
# The client's steps before Mani checks its understanding, in order: the problem, the core issue under
# it, the feeling underneath (meeting and cheat sheet, 2026-10-13; the feeling replaced what is in their
# control, muhammad, 2026-10-21). Each is taken only once the one
# before it was stored on an earlier turn, so each gets an exchange of its own (spec 0006).
STEPS = {"issue": "problem", "core_issue": "core_issue", "underlying_feeling": "underlying_feeling"}


def _in_order(key: str, before: dict[str, str]) -> bool:
    """Whether `key` may be stored this turn: it is not a step, or every step before it was stored."""
    if key not in STEPS:
        return True
    earlier = list(STEPS)[: list(STEPS).index(key)]
    return all(before.get(step) for step in earlier)


def next_step(stored: dict[str, str]) -> str | None:
    """The first step still missing, by its name in [ctx], or None once all three are stored."""
    return next((name for key, name in STEPS.items() if not stored.get(key)), None)


def _gathered(stored: str | None, value: str, key: str) -> str:
    """What `stored` holds with the entries of `value` added after it, none twice, and the oldest dropped
    when the whole no longer fits."""
    separator, limit = GATHERED[key]
    entries: list[str] = []
    for entry in [*(stored or "").split(separator.strip()), *value.split(separator.strip())]:
        entry = entry.strip()
        if entry and entry.lower() not in (e.lower() for e in entries):
            entries.append(entry)
    while len(separator.join(entries)) > limit and len(entries) > 1:
        entries.pop(0)
    return separator.join(entries)[:limit].rstrip()


def merge(
    stored: dict[str, str], update: UnderstandingUpdate | None, *, before: dict[str, str] | None = None,
    frozen: bool = False,
) -> dict[str, str]:
    """The record after this turn. Per key, a null or blank value keeps what is stored; anything
    else replaces it, on one line (which also keeps it from opening a line of its own in [ctx]) and
    cut to LIMIT characters, except what gathers (GATHERED), which is added to. A step is taken only
    in order, judged on `before`, the record as this turn began (`stored` when not given), and not at
    all when `frozen`: once an offer is open or a framework runs, the case is the one they confirmed and
    anything new goes in `also`."""
    before = stored if before is None else before
    merged = {key: stored[key] for key in KEYS if stored.get(key)}
    for key in KEYS:
        value = " ".join((getattr(update, key, None) or "").split())
        if not value or (key in STEPS and (frozen or not _in_order(key, before))):
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
    """The record after a stored check: its problem is the issue they are dealing with, and what it
    came down to, which they confirmed, is kept too, since it is closer to what they hold than their
    opening line (live, 2026-10-13)."""
    merged = merge(stored, UnderstandingUpdate(
        issue=check.problem, core_issue=check.core_issue, underlying_feeling=check.underlying_feeling,
    ))
    came_to = " ".join((check.comes_down_to or "").split())
    if came_to:
        merged["comes_down_to"] = came_to[:LIMIT].rstrip()
    return merged
