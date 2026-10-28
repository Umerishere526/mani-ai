# ABOUTME: What Mani understands of the person so far: the feelings they named, where its reading of the heart of it
# ABOUTME: stands, and the case they confirmed. Pure functions: this turn merged into the stored record, and its [ctx] value.

from __future__ import annotations

from mani.chat import context, picture
from mani.llm.schema import PictureUpdate

KEYS = ("feeling", "heart", "case")
LIMIT = 200
# The confirmed case says the core and the feeling underneath, a sentence or two.
CASE_LIMIT = 3 * LIMIT
# Every feeling word they name gathers over the conversation and is never taken away.
FEELING_SEPARATOR = ", "
# Where the reply last judged its reading of the core: not known yet, said back and not corrected, or named and
# since deepened or confirmed (muhammad, 2026-10-28; before it, the central conflict, 2026-10-26). Only a reply
# that judges it ready may check its understanding (R33).
READY = "ready"
# The core said back and not corrected (muhammad, 2026-10-28). A record written before then says conflict_named.
CORE_NAMED = "core_named"
_LEGACY_HEART = {"conflict_named": CORE_NAMED}


def heart(stored: dict) -> str | None:
    """Where the last reply judged the core, with a record from before 2026-10-28 read in today's words."""
    value = (stored or {}).get("heart")
    return _LEGACY_HEART.get(value, value)


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


def merge(stored: dict, update: PictureUpdate | None, heart: str | None) -> dict:
    """The record after this turn: the picture with what their message adds or changes, every feeling it names
    added to those kept, and where the reply judged the heart of it, replacing the last judgement. A null or blank
    value keeps what is stored."""
    merged = {key: stored[key] for key in (*KEYS, picture.KEY) if stored.get(key)}
    if merged.get("heart") in _LEGACY_HEART:
        merged["heart"] = _LEGACY_HEART[merged["heart"]]
    before = stored.get(picture.KEY)
    after = picture.merge(before, update)
    if after:
        merged[picture.KEY] = after
    known = picture.feeling_words(before)
    if new := [word for word in picture.feeling_words(after) if word not in known]:
        merged["feeling"] = _gathered(merged.get("feeling"), FEELING_SEPARATOR.join(new))
    if update is not None and (update.shift or "").strip().lower() == "new_issue":
        # Another situation: the reading of the last one does not hold for it, so the heart of it is found again.
        merged.pop("heart", None)
    if heart:
        merged["heart"] = heart
    return merged


def render(stored: dict) -> str | None:
    """The record as the value of its [ctx] line, or None when nothing is stored yet."""
    parts = [f"{key}: {context.disarm(stored[key])}" for key in KEYS if stored.get(key)]
    return "; ".join(parts) or None


def picture_line(stored: dict) -> str | None:
    """The picture of them as one line the model reads, or None while it holds nothing."""
    rendered = picture.render(stored.get(picture.KEY))
    return context.disarm(rendered) if rendered else None


def merge_check(stored: dict[str, str], summary: str) -> dict[str, str]:
    """The record after a stored check: its summary is the case, the core and the feeling underneath, which a yes
    makes what the questions are about."""
    return {**stored, "case": " ".join(summary.split())[:CASE_LIMIT].rstrip()}
