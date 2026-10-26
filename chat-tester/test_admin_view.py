# ABOUTME: Checks the admin's read-only viewer: an admin reaches no composer, sees every message with its timing,
# ABOUTME: and cannot have their password reset from the page. Fakes the backend; needs no services.

from __future__ import annotations

import base64
import json

import pytest
from streamlit.testing.v1 import AppTest

import client as mani
from admin_view import gap


def _token(app_metadata: dict) -> str:
    def part(data: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()

    return f"{part({'alg': 'HS256'})}.{part({'sub': 'u', 'app_metadata': app_metadata})}.sig"


ADMIN = mani.Session("admin-id", _token({"admin_role": "admin"}), "refresh")
TESTER = mani.Session("tester-id", _token({}), "refresh")

THREAD = {
    "id": "t1", "user_id": "u1", "user_email": "beta@test.dev", "user_nickname": "Sam",
    "title": "Work stress", "message_count": 3, "crisis_detected": False, "conversation_style": "directive",
    "created_at": "2026-10-26T10:00:00Z", "last_message_at": "2026-10-26T10:05:10Z",
}
OLDER = THREAD | {"id": "t0", "title": "Sleep", "conversation_style": None,
                  "last_message_at": "2026-10-25T09:00:00Z"}
OTHER = THREAD | {"id": "t2", "user_id": "u2", "user_email": "other@test.dev", "user_nickname": None,
                  "title": "Exams", "crisis_detected": True, "last_message_at": "2026-10-26T09:00:00Z"}
MESSAGES = [
    {"role": "mani", "content": "Hi Sam, what's on your mind?", "created_at": "2026-10-26T10:00:00Z"},
    {"role": "user", "content": "My boss again.", "created_at": "2026-10-26T10:02:00Z",
     "selected_prompt": None},
    {"role": "mani", "content": "What happened this time?", "created_at": "2026-10-26T10:02:09Z"},
]


class FakeBackend(mani.ManiClient):
    """Answers the admin endpoints from memory, and fails loudly on anything that would chat."""

    def admin_threads(self, search="", limit=200):
        return {"threads": [THREAD, OTHER, OLDER], "next_cursor": None}

    def admin_transcript(self, thread_id):
        return {"thread": THREAD, "messages": MESSAGES}

    def _call(self, method, path, **kwargs):
        raise AssertionError(f"the admin view called {method} {path}")


def _app(session: mani.Session, **state) -> AppTest:
    app = AppTest.from_file("app.py", default_timeout=30)
    app.session_state["client"] = FakeBackend(session=session)
    app.session_state["email"] = "someone@test.dev"
    app.session_state["user_id"] = session.user_id
    for key, value in state.items():
        app.session_state[key] = value
    return app.run()


def test_the_token_decides_who_is_an_admin():
    assert mani.is_admin(ADMIN)
    assert not mani.is_admin(TESTER)


def test_an_admin_gets_the_viewer_with_no_way_to_send_anything():
    app = _app(ADMIN)

    assert not app.exception
    assert not app.chat_input
    assert app.title[0].value == "🧠 Beta conversations"
    assert [e.label for e in app.sidebar.expander] == [
        "Sam · beta@test.dev · 2 conversations", "🚨 other@test.dev · 1 conversation",
    ]
    assert [b.label for b in app.sidebar.button] == [
        "Sign out", "Work stress (Directive)", "Sleep", "🚨 Exams (Directive)",
    ]


def test_an_open_transcript_shows_every_message_with_the_time_since_the_one_before():
    app = _app(ADMIN, admin_thread="t1")

    assert not app.exception
    assert not app.chat_input
    captions = [c.value for c in app.caption]
    assert any(c.endswith("+2m") for c in captions)
    assert any(c.endswith("+9s") for c in captions)
    assert [m.markdown[0].value for m in app.chat_message] == [m["content"] for m in MESSAGES]


@pytest.mark.parametrize(
    ("seconds", "shown"),
    [(9, "+9s"), (120, "+2m"), (3600, "+1h"), (7500, "+2h 5m"), (86400, "+1d"), (100800, "+1d 4h")],
)
def test_the_gap_between_messages_reads_at_a_glance(seconds, shown):
    assert gap(seconds) == shown


def test_an_admin_accounts_password_is_never_reset(monkeypatch):
    monkeypatch.setattr(mani, "_require_keys", lambda: None)
    monkeypatch.setattr(
        mani, "_account_for", lambda email: {"id": "a", "app_metadata": {"admin_role": "admin"}}
    )
    monkeypatch.setattr(mani.requests, "put", lambda *a, **k: pytest.fail("reset an admin's password"))

    with pytest.raises(RuntimeError, match="cannot be reset here"):
        mani.reset_password("admin@test.dev", "newpass1")
