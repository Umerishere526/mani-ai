# ABOUTME: Checks the sidebar's nickname form: it shows the name Mani greets them by and saves a changed one.
# ABOUTME: Runs the form in Streamlit's own test runner against a fake backend; needs no services.

from __future__ import annotations

from streamlit.testing.v1 import AppTest


def _sidebar_form():
    import streamlit as st

    import client as mani
    from login import render_nickname

    class ProfileBackend(mani.ManiClient):
        """Holds one profile and records each PUT, as the backend's /v1/profile would."""

        def __init__(self) -> None:
            super().__init__(session=mani.Session("user", "token", "refresh"))

        def _call(self, method, path, **kwargs):
            if method == "PUT":
                st.session_state.saved.append(kwargs["json"]["nickname"])
                return {"nickname": kwargs["json"]["nickname"]}
            return {"nickname": st.session_state.stored_nickname}

    st.session_state.setdefault("saved", [])
    render_nickname(ProfileBackend())


def test_the_form_shows_their_nickname_and_saves_a_new_one():
    app = AppTest.from_function(_sidebar_form)
    app.session_state.stored_nickname = None

    app.run()
    assert app.text_input[0].value == ""

    app.text_input[0].input("Lolly")
    app.button[0].click().run()

    assert app.session_state.saved == ["Lolly"]
    assert app.session_state.profile_nickname == "Lolly"


def test_an_unchanged_nickname_is_not_saved_again():
    app = AppTest.from_function(_sidebar_form)
    app.session_state.stored_nickname = "Lolly"

    app.run()
    assert app.text_input[0].value == "Lolly"
    app.button[0].click().run()

    assert app.session_state.saved == []
