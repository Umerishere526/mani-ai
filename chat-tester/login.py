# ABOUTME: The sign-in and sign-up screen: a real Supabase account per person,
# ABOUTME: so each one sees only their own conversations. Shown until somebody is signed in.

from __future__ import annotations

from typing import Callable

import streamlit as st

import client as mani
import session_store


# Sign-up's answer when the project emails a confirmation link before the account can sign in (local Supabase does).
CONFIRM_FIRST = "Account created. Open the confirmation link sent to {email}, then sign in."


def _start(sign_in: Callable[[], mani.Session | None], email: str, nickname: str = "") -> None:
    """Sign in one way or another, then start from a clean slate as that person."""
    try:
        session = sign_in()
        if session is None:
            st.info(CONFIRM_FIRST.format(email=email.strip()))
            return
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
    # Survives a browser reload, which st.session_state does not.
    session_store.start(session, email.strip())
    st.rerun()


def render_account(role: str) -> None:
    """The sidebar's top: who is signed in, as what, and the way out."""
    st.header("Session")
    st.caption(f"backend: {mani.API_BASE_URL}")
    st.caption(f"signed in: {st.session_state.email} ({role})")
    if st.button("Sign out", use_container_width=True):
        session_store.end()
        st.session_state.clear()
        st.rerun()


def render_nickname(client: mani.ManiClient) -> None:
    """The name Mani greets them by. Sign-up is the only other place it is asked, so an account made without one,
    or signed in to, would be greeted as "Hi there" in every chat (Lolly, 2026-11-03)."""
    with st.form("nickname", enter_to_submit=True, border=False):
        current = st.session_state.get("profile_nickname")
        if current is None:
            try:
                current = client.get_profile().get("nickname") or ""
            except mani.ApiError:
                current = ""
            st.session_state.profile_nickname = current
        typed = st.text_input("Nickname, used in the greeting", value=current, max_chars=40)
        if st.form_submit_button("Save nickname", use_container_width=True) and typed.strip() != current:
            try:
                st.session_state.profile_nickname = client.set_profile(typed.strip()).get("nickname") or ""
            except mani.ApiError as exc:
                st.error(str(exc))
            else:
                st.caption("Saved. The greeting of your next new conversation uses it.")


def render_login() -> None:
    st.title("🧠 Mani chat tester")
    sign_in_tab, sign_up_tab = st.tabs(["Sign in", "Sign up"])

    with sign_in_tab, st.form("sign_in", enter_to_submit=False):
        email = st.text_input("Email", key="sign_in_email")
        password = st.text_input("Password", type="password", key="sign_in_password")
        if st.form_submit_button("Sign in", use_container_width=True, type="primary"):
            _start(lambda: mani.sign_in_with_password(email, password), email)

    with sign_up_tab, st.form("sign_up", enter_to_submit=False):
        email = st.text_input("Email", key="sign_up_email")
        password = st.text_input("Password", type="password", key="sign_up_password")
        nickname = st.text_input("Nickname (optional, used in the greeting)", key="sign_up_nickname")
        if st.form_submit_button("Create account", use_container_width=True, type="primary"):
            _start(lambda: mani.sign_up(email, password), email, nickname)

