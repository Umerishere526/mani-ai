# ABOUTME: The library page: every exercise from the backend on one page, grouped by topic,
# ABOUTME: each with a player and a 👍/👎 row. Reached from a Visit library button or the sidebar.

from __future__ import annotations

import math

import streamlit as st

import client as mani
from audio_player import audio_player
from library_feedback import feedback_row

# The order and names the mani app shows its sections in.
SECTIONS = {
    "Anxiety": "Anxiety",
    "Boundaries": "Boundaries",
    "BuildingHabits": "Building Habits",
    "Burnout": "Burnout",
    "EmotionalIntelligence": "Emotional Intelligence",
    "LoveRelationships": "Love and Relationships",
    "ManagingWorry": "Managing Worry",
    "Sleep": "Sleep",
}

# Every exercise plays in the same player; only stories get its speed choice.
STORY = "Story"


def _duration(minutes: float | None) -> str:
    if minutes is None:
        return ""
    # To the nearest 30 seconds with halves rounded up, as the apps round it (Python's round() would take 1.25 minutes
    # down to 1:00), and never 0:00.
    seconds = max(30, 30 * math.floor(minutes * 2 + 0.5))
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
                    audio_player(exercise["audio_url"], speed_choice=exercise.get("type") == STORY)
                else:
                    st.caption("Audio unavailable right now.")
                feedback_row(client, exercise)
