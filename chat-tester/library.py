# ABOUTME: The library page: every exercise from the backend on one page, grouped by topic,
# ABOUTME: each with a player. Reached from a Go to Library button or the sidebar.

from __future__ import annotations

import streamlit as st

import client as mani

# The order and names the mani app shows its sections in. "home" is the start-here set.
SECTIONS = {
    "home": "Start here",
    "Anxiety": "Anxiety",
    "Boundaries": "Boundaries",
    "BuildingHabits": "Building Habits",
    "Burnout": "Burnout",
    "EmotionalIntelligence": "Emotional Intelligence",
}


def _duration(minutes: float | None) -> str:
    if minutes is None:
        return ""
    seconds = round(minutes * 60)
    return f"{seconds // 60}:{seconds % 60:02d}"


def render_library(client: mani.ManiClient) -> None:
    if st.button("← Back to chat"):
        st.session_state.view = "chat"
        st.rerun()
    st.title("📚 Library")

    # Fetched on every render: the links are signed for an hour, so a stale page never plays.
    try:
        exercises = client.list_exercises()
    except mani.ApiError as exc:
        st.error(str(exc))
        return

    known = [key for key in SECTIONS if any(e["category"] == key for e in exercises)]
    others = sorted({e["category"] for e in exercises} - set(SECTIONS))
    for key in known + others:
        st.subheader(SECTIONS.get(key, key))
        for exercise in (e for e in exercises if e["category"] == key):
            with st.container(border=True):
                meta = " · ".join(
                    part for part in (exercise.get("type"), _duration(exercise.get("duration_minutes"))) if part
                )
                st.markdown(f"**{exercise['title']}**" + (f"  \n{meta}" if meta else ""))
                st.caption(exercise.get("subtitle") or exercise.get("description") or "")
                if exercise.get("audio_url"):
                    st.audio(exercise["audio_url"])
                else:
                    st.caption("Audio unavailable right now.")
