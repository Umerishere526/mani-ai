# ABOUTME: The 👍/👎 row under each library exercise: a tap saves at once, then an optional one-line reason and Submit.
# ABOUTME: Runs as a fragment, so rating never reruns the page and an exercise that is playing keeps playing.

from __future__ import annotations

from typing import Any

import requests
import streamlit as st

import client as mani

# st.feedback's thumbs: 0 is 👎, 1 is 👍.
RATINGS = ("down", "up")
PLACEHOLDER = "[Optional] Please provide an explanation"
# The backend's limit, so the field stops there rather than the save being refused.
MAX_REASON = 1000
NOT_SAVED = "Your rating couldn't be saved. Try again."
THANKS = "Thanks for your feedback."


def _thumb_key(exercise: dict[str, Any]) -> str:
    return f"library_rating_{exercise['id']}"


def _reason_key(exercise: dict[str, Any]) -> str:
    return f"library_reason_{exercise['id']}"


def _refused(exc: Exception) -> str:
    error = (exc.body.get("error") or {}) if isinstance(exc, mani.ApiError) else {}
    return error.get("message") or NOT_SAVED


def _changed(client: mani.ManiClient, exercise: dict[str, Any]) -> None:
    """Saves the thumb just tapped, or clears it when the same thumb was tapped again. A new thumb starts with no
    reason, since any earlier one was about the other rating."""
    choice = st.session_state[_thumb_key(exercise)]
    try:
        if choice is None:
            client.clear_exercise_rating(exercise["id"])
            exercise["feedback"] = None
        else:
            exercise["feedback"] = client.rate_exercise(exercise["id"], RATINGS[choice])
        st.session_state.pop(_reason_key(exercise), None)
    except (mani.ApiError, requests.exceptions.RequestException) as exc:
        stored = exercise.get("feedback")
        st.session_state[_thumb_key(exercise)] = RATINGS.index(stored["rating"]) if stored else None
        st.toast(_refused(exc))


def _submit(client: mani.ManiClient, exercise: dict[str, Any]) -> None:
    # Sent as typed: the backend cleans it, and nothing left means no reason.
    reason = st.session_state.get(_reason_key(exercise)) or None
    try:
        exercise["feedback"] = client.rate_exercise(exercise["id"], exercise["feedback"]["rating"], reason)
    except (mani.ApiError, requests.exceptions.RequestException) as exc:
        st.toast(_refused(exc))
    else:
        st.toast(THANKS)


@st.fragment
def feedback_row(client: mani.ManiClient, exercise: dict[str, Any]) -> None:
    stored = exercise.get("feedback")
    # The stored rating seeds the widget once; after that the widget's own state is the truth.
    default = None if _thumb_key(exercise) in st.session_state or not stored else RATINGS.index(stored["rating"])
    with st.container(horizontal=True, vertical_alignment="center"):
        st.feedback(
            "thumbs", key=_thumb_key(exercise), default=default, on_change=_changed, args=(client, exercise)
        )
        if exercise.get("feedback"):
            st.text_input(
                "Why",
                value=exercise["feedback"].get("reason") or "",
                key=_reason_key(exercise),
                placeholder=PLACEHOLDER,
                max_chars=MAX_REASON,
                label_visibility="collapsed",
            )
            st.button(
                "Submit", key=f"library_submit_{exercise['id']}", type="tertiary",
                on_click=_submit, args=(client, exercise),
            )
