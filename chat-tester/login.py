# ABOUTME: The sign-in and sign-up screen: a real Supabase account per person, so each one
# ABOUTME: sees only their own conversations. Shown until somebody is signed in.

from __future__ import annotations

from typing import Callable

import streamlit as st

import client as mani


def _start(sign_in: Callable[[], mani.Session], email: str, nickname: str = "") -> None:
    """Sign in one way or another, then start from a clean slate as that person."""
    try:
        session = sign_in()
        client = mani.ManiClient(session=session)
        if nickname.strip():
            # Before any chat starts, so the very first greeting already uses it.
            client.set_profile(nickname.strip())
    except (RuntimeError, mani.ApiError) as exc:
        st.error(str(exc))
        return
    st.session_state.clear()
    st.session_state.client = client
    st.session_state.user_id = session.user_id
    st.session_state.email = email.strip()
    st.rerun()


def render_login() -> None:
    st.title("🧠 Mani chat tester")
    sign_in_tab, sign_up_tab = st.tabs(["Sign in", "Sign up"])

    with sign_in_tab, st.form("sign_in"):
        email = st.text_input("Email", key="sign_in_email")
        password = st.text_input("Password", type="password", key="sign_in_password")
        if st.form_submit_button("Sign in", use_container_width=True, type="primary"):
            _start(lambda: mani.sign_in_with_password(email, password), email)

    with sign_up_tab, st.form("sign_up"):
        email = st.text_input("Email", key="sign_up_email")
        password = st.text_input("Password", type="password", key="sign_up_password")
        nickname = st.text_input("Nickname (optional, used in the greeting)", key="sign_up_nickname")
        if st.form_submit_button("Create account", use_container_width=True, type="primary"):
            _start(lambda: mani.sign_up(email, password), email, nickname)
