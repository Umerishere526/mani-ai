# ABOUTME: The "Why" under a Mani reply: what code decided on that turn (admin.turn_traces), one line per decision.
# ABOUTME: Shared by the chat view (the turn as it arrives, in debug) and the admin transcript (every stored turn).

from __future__ import annotations

import json
from typing import Any

import streamlit as st

# The decisions read first, in the order a review asks them.
_ORDER = (
    ("moment", "Moment"), ("style", "Style"), ("their_message", "Their message no."), ("framework", "Framework"),
    ("phase_before", "Stage before"), ("phase_after", "Stage after"), ("tapped", "Tapped"),
    ("may_move", "May move to the set"), ("move_held", "Move held by"), ("moved", "Moved to the set"), ("offered", "Offered"),
    ("offer_dropped", "Offer unusable"), ("toward_framework", "Pressing toward the framework"),
    ("corrected_offer", "Corrected the offer"), ("core_fixed", "Core held fixed"), ("safety", "Safety screen"),
    ("model_concern", "Model concern"), ("guarded", "Guarded"), ("safety_settled", "Safety settled"),
    ("paused", "Chat paused"), ("return_check", "Return check"), ("end_check", "Safety check after the last stage"),
    ("stepped_out_of", "Stepped out of"), ("no_forward", "Reply asked no question"),
    ("text_asks", "Question in the text too"), ("forward_asks_many", "More than one question at the end"),
    ("reading_before", "Reading of the turn before"), ("latency_ms", "Model time (ms)"),
)


def _line(label: str, value: Any) -> str:
    if isinstance(value, dict):
        value = ", ".join(f"{k} {v}" for k, v in value.items())
    elif isinstance(value, list):
        value = " | ".join(json.dumps(v) if isinstance(v, dict) else str(v) for v in value)
    return f"**{label}:** {value}"


def lines(trace: dict[str, Any]) -> list[str]:
    """One line per decision the trace holds: the ordered ones, then the longer records."""
    shown = [_line(label, trace[key]) for key, label in _ORDER if key in trace]
    for key, label in (("model", "Model reported"), ("applied", "Code applied"), ("walk", "Walk"),
                       ("funnel", "Funnel"), ("stages", "Stages after"), ("buttons", "Buttons"),
                       ("notes", "Code's notes"), ("checks", "Checks")):
        if key in trace:
            shown.append(_line(label, trace[key]))
    return shown


def render(trace: dict[str, Any] | None, raw_reply: dict[str, Any] | None = None) -> None:
    """An expander with the turn's trace, and the model's raw reply when it was kept."""
    if not trace:
        return
    with st.expander("Why", expanded=False):
        st.markdown("  \n".join(lines(trace)))
        if raw_reply:
            st.caption("The model's raw reply (debug, kept 14 days)")
            st.json(raw_reply, expanded=False)
