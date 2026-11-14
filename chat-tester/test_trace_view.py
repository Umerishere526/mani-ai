# ABOUTME: Checks the "Why" panel shows every decision the backend writes into a turn's trace.
# ABOUTME: Pure lines, no Streamlit session needed.

from __future__ import annotations

import trace_view


def test_the_question_safety_and_reading_entries_each_get_a_labelled_line():
    """2026-11-11: these were written into the trace and never shown."""
    trace = {
        "safety_settled": True, "no_forward": True, "text_asks": True, "forward_asks_many": True,
        "reading_before": "failed:timeout", "stepped_out_of": "abcde",
    }
    shown = "\n".join(trace_view.lines(trace))
    for label in ("Safety settled", "Reply asked no question", "Question in the text too",
                  "More than one question at the end", "Reading of the turn before", "Stepped out of"):
        assert f"**{label}:**" in shown
    assert "failed:timeout" in shown


def test_a_paused_chat_and_the_safety_check_at_the_end_each_get_a_labelled_line():
    shown = "\n".join(trace_view.lines({"paused": True, "return_check": "paused_thread", "end_check": "asked"}))
    assert "**Chat paused:** True" in shown
    assert "**Return check:** paused_thread" in shown
    assert "**Safety check after the last stage:** asked" in shown
