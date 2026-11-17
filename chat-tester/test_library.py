# ABOUTME: Checks the library's players: every exercise gets the same player, and only a story's has a speed choice.
# ABOUTME: Runs the page in Streamlit's own test runner against a fake client; needs no services.

from __future__ import annotations

from streamlit.testing.v1 import AppTest


def _library():
    from library import render_library

    class FakeClient:
        def list_exercises(self):
            exercise = {
                "category": "Anxiety",
                "subtitle": None,
                "description": "A short exercise.",
                "duration_minutes": 3,
                "audio_url": "https://x.supabase.co/storage/v1/object/sign/exercises/a.mp3?token=t",
            }
            return [
                {**exercise, "id": "e1", "title": "Bee Breathing", "type": "Breathing"},
                {**exercise, "id": "e2", "title": "The Night Drive", "type": "Story"},
                {**exercise, "id": "e3", "title": "Calm Your Mind", "type": "Meditation", "audio_url": None},
            ]

    render_library(FakeClient())


def test_every_exercise_gets_the_player_and_only_a_story_gets_the_speed_choice():
    app = AppTest.from_function(_library)
    app.run()

    assert not app.exception
    assert not app.get("audio")
    players = [html.proto.body for html in app.get("html") if 'class="mani-player"' in html.proto.body]
    assert len(players) == 2
    assert ['class="mani-speed"' in player for player in players] == [False, True]
    assert [c.value for c in app.caption if c.value == "Audio unavailable right now."] == ["Audio unavailable right now."]


def test_an_exercises_length_is_shown_to_the_nearest_half_minute():
    """muhammad, 2026-11-16: 4:35 and 4:40 read as false precision; the length is rounded to the nearest 30 seconds."""
    import library

    assert library._duration(4.58) == "4:30"
    assert library._duration(4.8) == "5:00"
    assert library._duration(0.3) == "0:30", "a short one is never shown as 0:00"
    assert library._duration(10) == "10:00"
    assert library._duration(None) == ""
