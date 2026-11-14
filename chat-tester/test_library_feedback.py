# ABOUTME: Checks the 👍/👎 under library exercises: a tap saves at once, the reason field and Submit follow, the same
# ABOUTME: thumb again clears, and a refused save is put back. Uses a fake backend that records its calls.

from __future__ import annotations

from streamlit.testing.v1 import AppTest

import client as mani

STAMP = "2026-11-14T10:00:00+00:00"


class LibraryBackend:
    def __init__(self, refuse: bool = False) -> None:
        self.refuse = refuse
        self.calls: list[tuple] = []
        # What the backend holds, so the page reads back what was saved, as it does from the real API.
        self.ratings = {"e2": {"rating": "down", "reason": "too long", "updated_at": STAMP}}

    def list_exercises(self):
        exercise = {"category": "Anxiety", "description": "", "duration_minutes": 4, "audio_url": None}
        return [
            {**exercise, "id": "e1", "title": "Bee Breathing", "type": "Breathing", "feedback": self.ratings.get("e1")},
            {**exercise, "id": "e2", "title": "The Night Drive", "type": "Story", "feedback": self.ratings.get("e2")},
        ]

    def rate_exercise(self, exercise_id, rating, reason=None):
        self.calls.append((exercise_id, rating, reason))
        if self.refuse:
            raise mani.ApiError(404, {"error": {"message": "That exercise is not available."}})
        self.ratings[exercise_id] = {"rating": rating, "reason": (reason or "").strip() or None, "updated_at": STAMP}
        return self.ratings[exercise_id]

    def clear_exercise_rating(self, exercise_id):
        self.calls.append((exercise_id, None, None))
        self.ratings.pop(exercise_id, None)


def _library():
    import streamlit as st

    from library import render_library

    render_library(st.session_state.backend)


def _open(backend: LibraryBackend) -> AppTest:
    app = AppTest.from_function(_library, default_timeout=10)
    app.session_state.backend = backend
    return app.run()


def test_a_tap_saves_then_the_reason_follows_and_the_same_thumb_clears():
    backend = LibraryBackend()
    app = _open(backend)

    # A stored rating shows with its reason; an unrated exercise has thumbs only.
    assert app.feedback(key="library_rating_e2").value == 0
    assert [t.value for t in app.text_input] == ["too long"]

    app.feedback(key="library_rating_e1").set_value(1).run()
    assert backend.calls == [("e1", "up", None)]
    assert app.text_input(key="library_reason_e1").placeholder == "[Optional] Please provide an explanation"

    app.text_input(key="library_reason_e1").set_value("calming").run()
    app.button(key="library_submit_e1").click().run()
    assert backend.calls[-1] == ("e1", "up", "calming")
    assert [t.value for t in app.toast] == ["Thanks for your feedback."]

    app.feedback(key="library_rating_e2").set_value(None).run()
    assert backend.calls[-1] == ("e2", None, None)
    assert [t.key for t in app.text_input] == ["library_reason_e1"]


def test_a_refused_rating_is_put_back_and_says_why():
    backend = LibraryBackend(refuse=True)
    app = _open(backend)

    app.feedback(key="library_rating_e2").set_value(1).run()

    assert app.feedback(key="library_rating_e2").value == 0
    assert [t.value for t in app.toast] == ["That exercise is not available."]
