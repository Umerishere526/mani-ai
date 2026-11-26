# ABOUTME: The library page: the client's topics with their blurbs, and one topic's exercises at a time, grouped under
# ABOUTME: their subcategories, each with a player and a 👍/👎 row, or "Coming soon" until it is recorded.

from __future__ import annotations

from typing import Any

import streamlit as st

import client as mani
from audio_player import audio_player
from library_feedback import feedback_row

# Every exercise plays in the same player; only stories get its speed choice.
STORY = "Story"
# An exercise the client has not recorded yet (`recorded` false): listed, with no player and no link.
COMING_SOON = "Coming soon"
TOPIC_KEY = "library_topic"


def _duration(minutes: float | None) -> str:
    """A length as m:ss. The API already rounds it to the nearest 30 seconds."""
    if minutes is None:
        return ""
    seconds = round(minutes * 60)
    return f"{seconds // 60}:{seconds % 60:02d}"


def open_topic(section: str | None) -> None:
    """Opens the library on a section, as a Visit library button names it; "home" or None is the list of topics."""
    st.session_state[TOPIC_KEY] = None if section in (None, "home") else section


def _exercise(client: mani.ManiClient, exercise: dict[str, Any]) -> None:
    with st.container(border=True):
        meta = " · ".join(part for part in (exercise.get("type"), _duration(exercise.get("duration_minutes"))) if part)
        st.markdown(f"**{exercise['title']}**" + (f"  \n{meta}" if meta else ""))
        st.caption(exercise.get("subtitle") or exercise.get("description") or "")
        if not exercise["recorded"]:
            st.caption(COMING_SOON)
            return
        if exercise.get("audio_url"):
            audio_player(exercise["audio_url"], speed_choice=exercise.get("type") == STORY)
        else:
            st.caption("Audio unavailable right now.")
        feedback_row(client, exercise)


def _topic(client: mani.ManiClient, topic: dict[str, Any]) -> None:
    """One topic: its blurb, its own exercises, then the ones it lists from other topics under each subcategory."""
    if topic.get("blurb"):
        st.caption(topic["blurb"])
    # Fetched on every render: the links are signed for an hour, so a stale page never plays.
    try:
        exercises = client.list_exercises(topic["id"])
    except mani.ApiError as exc:
        st.error(str(exc))
        return
    groups: dict[str | None, list[dict[str, Any]]] = {}
    for exercise in exercises:
        groups.setdefault(exercise.get("subcategory"), []).append(exercise)
    for subcategory, group in groups.items():
        if subcategory:
            st.subheader(subcategory)
        for exercise in group:
            _exercise(client, exercise)


def render_library(client: mani.ManiClient) -> None:
    if st.button("← Back to chat"):
        st.session_state.view = "chat"
        st.rerun()
    st.title("📚 Library")

    try:
        topics = client.list_topics()
    except mani.ApiError as exc:
        st.error(str(exc))
        return
    titles = {t["id"]: t["title"] for t in topics}
    if st.session_state.get(TOPIC_KEY) not in titles:
        st.session_state[TOPIC_KEY] = None
    chosen = st.pills("Topics", list(titles), format_func=titles.get, key=TOPIC_KEY, label_visibility="collapsed")
    if chosen is None:
        for topic in topics:
            st.markdown(f"**{topic['title']}**" + (f"  \n{topic['blurb']}" if topic.get("blurb") else ""))
        return
    _topic(client, next(t for t in topics if t["id"] == chosen))
