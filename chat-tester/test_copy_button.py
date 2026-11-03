# ABOUTME: Checks the copy icon: a message's text rides on its button escaped, never as markup or code.
# ABOUTME: Runs the button in Streamlit's own test runner; needs no services.

from __future__ import annotations

from streamlit.testing.v1 import AppTest


def _one_button():
    import streamlit as st

    from copy_button import copy_button

    copy_button(st.session_state.text)


def test_a_message_is_copied_exactly_and_can_never_run_as_markup():
    app = AppTest.from_function(_one_button)
    app.session_state.text = 'He said "fine" <script>alert(1)</script>\nThen nothing.'
    app.run()

    body = app.get("html")[0].proto.body
    assert 'data-copy="He said &quot;fine&quot; &lt;script&gt;alert(1)&lt;/script&gt;\nThen nothing."' in body
    assert "<script>alert(1)" not in body

