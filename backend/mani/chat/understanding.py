# ABOUTME: What Mani understands of the person so far (their feeling word and their issue), kept per thread.
# ABOUTME: Pure functions: this turn's reported update merged into the stored record, and its [ctx] value.

from __future__ import annotations

from mani.chat import context
from mani.llm.schema import UnderstandingUpdate

KEYS = ("feeling", "issue")
LIMIT = 200


def merge(stored: dict[str, str], update: UnderstandingUpdate | None) -> dict[str, str]:
    """The record after this turn. Per key, a null or blank value keeps what is stored; anything
    else replaces it, on one line (which also keeps it from opening a line of its own in [ctx]) and
    cut to LIMIT characters."""
    merged = {key: stored[key] for key in KEYS if stored.get(key)}
    for key in KEYS:
        value = " ".join((getattr(update, key, None) or "").split())
        if value:
            merged[key] = value[:LIMIT].rstrip()
    return merged


def render(stored: dict[str, str]) -> str | None:
    """The record as the value of its [ctx] line, or None when nothing is stored yet."""
    parts = [f"{key}: {context.disarm(stored[key])}" for key in KEYS if stored.get(key)]
    return "; ".join(parts) or None
