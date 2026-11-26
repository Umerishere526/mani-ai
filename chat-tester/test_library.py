# ABOUTME: Checks the library page: topics with their blurbs, a topic's exercises grouped under their subcategories,
# ABOUTME: one player each (speed only for stories), and "Coming soon" for what is not recorded. Fake client, no services.

from __future__ import annotations

from streamlit.testing.v1 import AppTest

TOPICS = [
    {"id": "Stress", "title": "Stress", "blurb": "Ease the pressure.", "display_order": 1},
    {"id": "WorkplaceChallenges", "title": "Workplace Challenges", "blurb": "", "display_order": 2},
]
URL = "https://x.supabase.co/storage/v1/object/sign/exercises/a.mp3?token=t"


def exercise(id_: str, title: str, **fields) -> dict:
    return {"id": id_, "title": title, "category": "Stress", "subtitle": None, "description": "A short exercise.",
            "type": "Breathing", "subcategory": None, "duration_minutes": 3.5, "recorded": True, "audio_url": URL,
            "feedback": None, **fields}


class FakeClient:
    """Answers as the backend does: topics in order, and a topic's listing with its own exercises first."""

    def __init__(self) -> None:
        self.asked: list[str] = []

    def list_topics(self):
        return TOPICS

    def list_exercises(self, topic):
        self.asked.append(topic)
        if topic == "Stress":
            return [exercise("e1", "Bee Breathing"), exercise("e2", "The Night Drive", type="Story"),
                    exercise("e3", "Calm Your Mind", audio_url=None)]
        return [exercise("w1", "Desk Reset", category="WorkplaceChallenges", recorded=False, audio_url=None,
                         duration_minutes=None),
                exercise("e1", "Bee Breathing", subcategory="Stress & Pressure"),
                exercise("b1", "Saying No", category="Boundaries", subcategory="Boundaries at Work"),
                exercise("e2", "The Night Drive", type="Story", subcategory="Stress & Pressure")]


def _library():
    import streamlit as st

    from library import open_topic, render_library

    if "opened" not in st.session_state:
        st.session_state.opened = True
        open_topic(st.session_state.topic)
    render_library(st.session_state.client)


def _open(topic: str | None) -> AppTest:
    app = AppTest.from_function(_library)
    app.session_state.client, app.session_state.topic = FakeClient(), topic
    return app.run()


def _players(app: AppTest) -> list[str]:
    return [html.proto.body for html in app.get("html") if 'class="mani-player"' in html.proto.body]


def test_the_front_page_lists_each_topic_with_its_blurb_and_fetches_no_exercises():
    app = _open("home")

    assert not app.exception
    assert [m.value for m in app.markdown] == ["**Stress**  \nEase the pressure.", "**Workplace Challenges**"]
    assert app.session_state.client.asked == []


def test_every_recorded_exercise_gets_the_player_and_only_a_story_gets_the_speed_choice():
    app = _open("Stress")

    assert not app.exception
    assert not app.get("audio")
    assert ['class="mani-speed"' in player for player in _players(app)] == [False, True]
    assert [c.value for c in app.caption if c.value == "Audio unavailable right now."] == ["Audio unavailable right now."]
    assert "Ease the pressure." in [c.value for c in app.caption]
    assert "**Bee Breathing**  \nBreathing · 3:30" in [m.value for m in app.markdown]


def test_a_collecting_topic_groups_by_subcategory_and_an_unrecorded_item_is_coming_soon():
    app = _open("WorkplaceChallenges")

    assert not app.exception
    assert [h.value for h in app.subheader] == ["Stress & Pressure", "Boundaries at Work"]
    shown = [m.value for m in app.markdown]
    titles = [next(t for t in ("Desk Reset", "Bee Breathing", "The Night Drive", "Saying No") if t in m) for m in shown]
    assert titles == ["Desk Reset", "Bee Breathing", "The Night Drive", "Saying No"]
    assert [c.value for c in app.caption].count("Coming soon") == 1
    assert len(_players(app)) == 3, "no player for the item that is not recorded"
    assert not [f for f in app.get("feedback") if f.key == "library_rating_w1"], "nothing to rate before it is recorded"


def test_an_exercises_length_is_shown_as_the_api_sends_it():
    """The API rounds to the nearest 30 seconds (R143); the page only formats it."""
    import library

    assert library._duration(4.5) == "4:30"
    assert library._duration(0.5) == "0:30"
    assert library._duration(10) == "10:00"
    assert library._duration(None) == ""
