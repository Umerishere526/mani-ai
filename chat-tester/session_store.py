# ABOUTME: Keeps a signed-in session across a browser reload, which st.session_state cannot.
# ABOUTME: The refresh token lives in a local file; only its key is in the URL.

from __future__ import annotations

import json
import os
import pathlib
import secrets
import tempfile
import time
from dataclasses import dataclass

import streamlit as st

import client as mani

# st.session_state is per-connection memory: a reload opens a new connection and it is gone,
# which is why reloading used to drop a signed-in person back to the login screen mid-chat.
# st.context.cookies is read-only in Streamlit 1.64, so the browser side of this is the one
# thing Streamlit will let the page keep across a reload: a query parameter.
#
# Only an opaque key goes in the URL. The refresh token itself stays in a file next to the
# app's temp directory, so a shared or pasted URL carries no credential on its own.
PARAM = "s"
TTL_SECONDS = 14 * 24 * 60 * 60

# Alongside Streamlit's own temp files rather than in the repo, so a stray token is never
# committed and a machine reboot clears them.
#
# This is per-instance state, which is the one thing to know before deploying: a reload is
# only recognised by the instance that handled the sign-in. On a single container (which is
# how this tool is run) that is every reload. Behind more than one replica, a reload that
# lands elsewhere falls back to the login screen - no worse than today's behaviour, never an
# error - and a container restart signs everyone out the same way. Set
# CHAT_TESTER_SESSION_DIR to a mounted volume to survive restarts; sharing sessions across
# replicas would need a real store (Redis, a table), which this tool does not warrant.
STORE = pathlib.Path(
    os.environ.get("CHAT_TESTER_SESSION_DIR")
    or pathlib.Path(tempfile.gettempdir()) / "mani-chat-tester-sessions"
)


@dataclass(frozen=True)
class Stored:
    key: str
    user_id: str
    email: str
    refresh_token: str


def _path(key: str) -> pathlib.Path:
    # The key is generated here and never read from the URL without this check, so a
    # crafted ?s=../../etc/passwd cannot escape the directory.
    if not key.isalnum():
        raise ValueError("bad session key")
    return STORE / f"{key}.json"


def remember(session: mani.Session, email: str) -> str | None:
    """Store the session and return the key that reopens it, or None if it cannot be stored.

    None is a working state, not a failure: the person is signed in either way, they just
    lose it on a reload, which is exactly how this behaved before. A read-only filesystem
    must not stop somebody signing in.
    """
    key = secrets.token_urlsafe(24).replace("-", "").replace("_", "")
    payload = {
        "user_id": session.user_id,
        "email": email,
        "refresh_token": session.refresh_token,
        "at": time.time(),
    }
    try:
        STORE.mkdir(parents=True, exist_ok=True)
        path = _path(key)
        path.write_text(json.dumps(payload))
        os.chmod(path, 0o600)
    except OSError:
        return None
    return key


def recall(key: str) -> Stored | None:
    """What was stored under this key, if it is still there and still fresh."""
    try:
        path = _path(key)
    except ValueError:
        return None
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    if time.time() - payload.get("at", 0) > TTL_SECONDS:
        path.unlink(missing_ok=True)
        return None
    return Stored(key, payload["user_id"], payload["email"], payload["refresh_token"])


def forget(key: str | None) -> None:
    if not key:
        return
    try:
        _path(key).unlink(missing_ok=True)
    except ValueError:
        pass


def restore() -> bool:
    """Put a signed-in session back into st.session_state after a reload.

    True when somebody is now signed in. The refresh token is exchanged for a fresh access
    token, so an expired one signs them out properly rather than failing on the first call.
    """
    key = st.query_params.get(PARAM)
    if not key:
        return False
    stored = recall(key)
    if stored is None:
        st.query_params.pop(PARAM, None)
        return False
    try:
        session = mani.refresh(
            mani.Session(stored.user_id, access_token="", refresh_token=stored.refresh_token)
        )
    except (RuntimeError, mani.ApiError):
        forget(key)
        st.query_params.pop(PARAM, None)
        return False

    # Supabase rotates the refresh token on every exchange, so the stored one is now spent.
    renewed = remember(session, stored.email)
    forget(key)
    if renewed is None:
        st.query_params.pop(PARAM, None)
    else:
        st.session_state.session_key = renewed
        st.query_params[PARAM] = renewed
    st.session_state.client = mani.ManiClient(session=session)
    st.session_state.user_id = session.user_id
    st.session_state.email = stored.email
    return True


def start(session: mani.Session, email: str) -> None:
    """Remember a session just signed in, and put its key in the URL."""
    key = remember(session, email)
    if key is None:
        return
    st.session_state.session_key = key
    st.query_params[PARAM] = key


def end() -> None:
    """Sign out: the stored session goes, and so does the key in the URL."""
    forget(st.session_state.get("session_key"))
    st.query_params.pop(PARAM, None)
