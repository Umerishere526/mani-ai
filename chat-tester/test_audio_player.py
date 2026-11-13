# ABOUTME: Checks the exercise audio player: the signed link rides on the audio element escaped, never as markup or code,
# ABOUTME: with the four speeds offered and 1x chosen. Runs in Streamlit's own test runner; needs no services.

from __future__ import annotations

from streamlit.testing.v1 import AppTest


def _one_player():
    import streamlit as st

    from audio_player import audio_player

    audio_player(st.session_state.url, speed_choice=True)


def test_a_signed_link_plays_as_given_and_can_never_run_as_markup():
    app = AppTest.from_function(_one_player)
    app.session_state.url = 'https://x.supabase.co/storage/v1/object/sign/exercises/a.mp3?token=a&b="><script>alert(1)</script>'
    app.run()

    body = app.get("html")[0].proto.body
    assert 'src="https://x.supabase.co/storage/v1/object/sign/exercises/a.mp3?token=a&amp;b=&quot;&gt;&lt;script&gt;' in body
    assert "<script>alert(1)" not in body
    assert [speed for speed in ("0.5", "1", "1.5", "2") if f'value="{speed}"' in body] == ["0.5", "1", "1.5", "2"]
    assert '<option value="1" selected>' in body
