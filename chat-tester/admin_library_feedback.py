# ABOUTME: The admin's review of library ratings: who rated which exercise, 👍 or 👎, why, and when, newest first.
# ABOUTME: Filtered by part of an email or an exact user id; read-only.

from __future__ import annotations

import datetime as dt
from typing import Any

import streamlit as st

import client as mani

THUMBS = {"up": "👍", "down": "👎"}


def table_rows(ratings: list[dict[str, Any]]) -> list[dict[str, str]]:
    """One row per rating, in the order the backend sends them (most recently changed first)."""
    return [
        {
            "When": dt.datetime.fromisoformat(r["updated_at"].replace("Z", "+00:00")).strftime("%b %d, %H:%M UTC"),
            "Person": r.get("user_email") or r["user_id"],
            "Exercise": r["exercise_title"],
            "Rating": THUMBS[r["rating"]],
            "Reason": r.get("reason") or "",
            "Type": r.get("exercise_type") or "",
        }
        for r in ratings
    ]


def render_library_feedback(client: mani.ManiClient) -> None:
    st.title("📚 Library feedback")
    search = st.text_input("Filter by email or user id", key="admin_library_search")
    try:
        ratings = client.admin_exercise_feedback(search)
    except mani.ApiError as exc:
        st.error(f"Could not list library feedback: {exc}")
        return
    if not ratings:
        st.caption("No ratings match." if search.strip() else "No one has rated an exercise yet.")
        return
    up = sum(r["rating"] == "up" for r in ratings)
    people = len({r["user_id"] for r in ratings})
    count = f"{len(ratings)} rating" + ("" if len(ratings) == 1 else "s")
    st.caption(f"{count} from {people} {'person' if people == 1 else 'people'}  ·  👍 {up}  ·  👎 {len(ratings) - up}")
    st.dataframe(table_rows(ratings), hide_index=True, width="stretch")
