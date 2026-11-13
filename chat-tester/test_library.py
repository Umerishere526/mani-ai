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
                {**exercise, "title": "Bee Breathing", "type": "Breathing"},
                {**exercise, "title": "The Night Drive", "type": "Story"},
                {**exercise, "title": "Calm Your Mind", "type": "Meditation", "audio_url": None},
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
