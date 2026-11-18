# ABOUTME: Checks the "Why" panel shows every decision the backend writes into a turn's trace.
# ABOUTME: Pure lines, no Streamlit session needed.

from __future__ import annotations

import trace_view


def test_every_decision_the_turn_writes_gets_a_labelled_line():
    trace = {
        "action": "offer", "framework": "abcde", "stage": "belief", "safety": {"level": "none"}, "paused": True,
        "refused": "offer", "unanswered": True, "buttons": ["Try it"], "latency_ms": 900, "notes": "pushover",
    }
    shown = "\n".join(trace_view.lines(trace))
    for label in ("Action", "Framework", "Stage", "Safety", "Chat paused", "Code refused", "No host answered",
                  "Buttons", "Model time (ms)", "Mani's notes"):
        assert f"**{label}:**" in shown, label
    assert "**Safety:** level none" in shown


def test_a_key_the_panel_does_not_know_is_still_shown_under_its_own_name():
    """Turns stored before the one-call turn keep their own trace keys, and an admin reading one sees them all."""
    shown = trace_view.lines({"moment": "chatting", "action": "none"})
    assert shown[0] == "**Action:** none"
    assert "**moment:** chatting" in shown
