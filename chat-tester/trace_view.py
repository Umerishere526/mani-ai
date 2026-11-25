# ABOUTME: The "Why" under a Mani reply: what code decided on that turn (admin.turn_traces), one line per decision.
# ABOUTME: Shared by the chat view (the turn as it arrives, in debug) and the admin transcript (every stored turn).

from __future__ import annotations

import json
from typing import Any

import streamlit as st

# Each decision the turn writes, in the order a review asks them.
_ORDER = (
    ("action", "Action"), ("framework", "Framework"), ("stage", "Stage"), ("safety", "Safety"),
    ("paused", "Chat paused"), ("resources_added", "Help line added"), ("raised_by_phrase", "Raised by phrase"), ("refused", "Code refused"), ("unanswered", "No host answered"),
    ("question", "Question plan"), ("question_cut", "Question cut"), ("buttons", "Buttons"), ("latency_ms", "Model time (ms)"), ("notes", "Mani's notes"),
)
_LABELS = dict(_ORDER)


def _line(label: str, value: Any) -> str:
    if isinstance(value, dict):
        value = ", ".join(f"{k} {v}" for k, v in value.items())
    elif isinstance(value, list):
        value = " | ".join(json.dumps(v) if isinstance(v, dict) else str(v) for v in value)
    return f"**{label}:** {value}"


def lines(trace: dict[str, Any]) -> list[str]:
    """One line per decision the trace holds: the known ones in order, then any other under its own name."""
    return ([_line(label, trace[key]) for key, label in _ORDER if key in trace]
            + [_line(key, value) for key, value in trace.items() if key not in _LABELS])


def render(trace: dict[str, Any] | None, raw_reply: dict[str, Any] | None = None) -> None:
    """An expander with the turn's trace, and the model's raw reply when it was kept."""
    if not trace:
        return
    with st.expander("Why", expanded=False):
        st.markdown("  \n".join(lines(trace)))
        if raw_reply:
            st.caption("The model's raw reply (debug, kept 14 days)")
            st.json(raw_reply, expanded=False)
