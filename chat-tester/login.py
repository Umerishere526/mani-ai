# ABOUTME: The sign-in, sign-up and password-reset screen: a real Supabase account per person,
# ABOUTME: so each one sees only their own conversations. Shown until somebody is signed in.

from __future__ import annotations

from typing import Callable

import streamlit as st

import client as mani
import session_store


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
    # Survives a browser reload, which st.session_state does not.
    session_store.start(session, email.strip())
    st.rerun()


def render_login() -> None:
    st.title("🧠 Mani chat tester")
    sign_in_tab, sign_up_tab, reset_tab = st.tabs(["Sign in", "Sign up", "Forgot password"])

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

    with reset_tab:
        st.caption(
            "We email a six-digit code to the address on the account. Only someone who can "
            "read that mailbox can set a new password."
        )
        with st.form("send_code", enter_to_submit=False):
            email = st.text_input("Email", key="reset_email")
            if st.form_submit_button("Email me a code", use_container_width=True):
                try:
                    mani.send_recovery_code(email)
                except (RuntimeError, mani.ApiError) as exc:
                    st.error(str(exc))
                else:
                    # Said the same way whether or not the account exists, so this page
                    # cannot be used to find out who has signed up.
                    st.session_state.code_sent_to = email.strip()
                    st.success(f"If {email.strip()} has an account, a code is on its way.")

        if st.session_state.get("code_sent_to"):
            with st.form("use_code", enter_to_submit=False):
                st.caption(f"Code sent to {st.session_state.code_sent_to}. It expires in an hour.")
                code = st.text_input("Six-digit code", key="reset_code", max_chars=6)
                password = st.text_input("New password", type="password", key="reset_password")
                again = st.text_input("New password again", type="password", key="reset_password_again")
                if st.form_submit_button("Set new password", use_container_width=True, type="primary"):
                    if password != again:
                        st.error("Those two passwords are not the same.")
                    elif len(password) < 6:
                        # Supabase's own minimum; caught here so the error names the rule.
                        st.error("A password needs at least six characters.")
                    else:
                        # Bound here rather than read inside the lambda: _start clears
                        # session_state, and this must not depend on when it does that.
                        to = st.session_state.code_sent_to
                        _start(
                            lambda: mani.reset_password_with_code(to, code, password), to
                        )
