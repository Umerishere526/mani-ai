# ABOUTME: Checks a new conversation is a local draft until the person's first message: it shows Mani's greeting and
# ABOUTME: the style buttons, holds a tap, and only the first message creates the thread. Fake backend; no services.

from __future__ import annotations

import base64
import pathlib
import threading

import pytest
import requests
from streamlit.testing.v1 import AppTest

import client as mani

GREETING = "Hi there. It's MANI. How would you like me to speak with you today?"
OPENERS = {
    "directive": "How can I help you today?",
    "supportive": "How can I support you today?",
    "reflective": "What's on your mind today?",
}
OPENING = {
    "greeting": GREETING,
    "style_options": [{"label": label.capitalize(), "style": label} for label in OPENERS],
    "openers": OPENERS,
    "chat_paused_from": None,
    "chat_paused_until": None,
}
REPLY = "What happened next?"
THREAD = {
    "id": "T", "title": None, "message_count": 3, "crisis_detected": False,
    "conversation_style": None, "created_at": "2026-11-13T10:00:00Z", "last_message_at": "2026-11-13T10:00:00Z",
}
EARLIER = [
    {"id": "e0", "role": "mani", "content": GREETING, "prompts": []},
    {"id": "e1", "role": "user", "content": "Supportive"},
    {"id": "e2", "role": "mani", "content": OPENERS["supportive"], "prompts": []},
]


class DraftBackend(mani.ManiClient):
    """Answers the routes the draft uses from memory and records each call, as the real backend would see it."""

    def __init__(self, earlier: bool = False, history_fails: bool = False, creates_timing_out: int = 0) -> None:
        token = "h." + base64.urlsafe_b64encode(b'{"role":"authenticated"}').decode().rstrip("=") + ".s"
        super().__init__(session=mani.Session("00000000-0000-0000-0000-000000000001", token, "refresh"))
        self.earlier = earlier
        self.history_fails = history_fails
        self.creates_timing_out = creates_timing_out
        self.calls: list[tuple] = []
        self.folded = threading.Event()
        self.stored: list[dict] = []

    def _call(self, method, path, **kwargs):
        self.calls.append((method, path, kwargs.get("json")))
        if (method, path) == ("GET", "/v1/threads/current"):
            return {"thread": THREAD, "messages": EARLIER[-20:]} if self.earlier else {"thread": None, "messages": []}
        if path == "/v1/threads/opening":
            return OPENING
        if path == "/v1/threads/memory-fold":
            self.folded.set()
            return {"folded": 0}
        if (method, path) == ("POST", "/v1/threads"):
            if self.creates_timing_out:
                self.creates_timing_out -= 1
                raise requests.exceptions.ReadTimeout("no reply")
            self._store(kwargs["json"])
            return {"thread": THREAD, "turn": {"id": "r1", "content": REPLY, "prompts": [], "follow_up_pending": False}}
        if (method, path) == ("GET", "/v1/threads/T/messages"):
            if self.history_fails:
                raise mani.ApiError(500, {"error": {"category": "internal", "message": "down"}})
            return {"messages": self.stored[::-1], "next_cursor": None}
        if (method, path) == ("GET", "/v1/threads"):
            return {"threads": [THREAD] if self.stored else []}
        if path == "/v1/profile":
            return {}
        raise AssertionError(f"unexpected {method} {path}")

    def _store(self, body: dict) -> None:
        style = body.get("style")
        self.stored = [{"id": "g", "role": "mani", "content": GREETING, "prompts": []}]
        if style:
            self.stored += [
                {"id": "t", "role": "user", "content": style.capitalize()},
                {"id": "o", "role": "mani", "content": OPENERS[style], "prompts": []},
            ]
        self.stored += [
            {"id": "u", "role": "user", "content": body["content"]},
            {"id": "r1", "role": "mani", "content": REPLY, "prompts": []},
        ]

    def writes(self) -> list[tuple]:
        return [(m, p) for m, p, _ in self.calls if m != "GET"]


@pytest.fixture(autouse=True)
def no_database(monkeypatch):
    monkeypatch.setattr(mani, "DATABASE_URL", "")


def _open(backend: DraftBackend) -> AppTest:
    app = AppTest.from_file(str(pathlib.Path(__file__).with_name("app.py")), default_timeout=20)
    app.session_state["email"], app.session_state["client"] = "a@b.c", backend
    app.session_state["user_id"] = backend.session.user_id
    app.run()
    assert not app.exception
    return app


def _tap(app: AppTest, label: str) -> None:
    next(b for b in app.button if b.label == label).click().run()
    assert not app.exception


def _contents(app: AppTest) -> list[str]:
    return [m["content"] for m in app.session_state.messages]


def test_new_conversation_calls_nothing_that_writes():
    backend = DraftBackend(earlier=True)
    app = _open(backend)
    backend.calls.clear()

    next(b for b in app.sidebar.button if b.label.endswith("New conversation")).click().run()

    assert not app.exception
    assert backend.folded.wait(2)
    assert backend.writes() == [("POST", "/v1/threads/memory-fold")]
    assert ("GET", "/v1/threads/opening", None) in backend.calls
    assert app.session_state.thread is None
    assert _contents(app) == [GREETING]


def test_a_style_tap_in_a_draft_sends_nothing():
    backend = DraftBackend()
    app = _open(backend)
    assert {b.label for b in app.button} >= {"Directive", "Supportive", "Reflective"}
    backend.calls.clear()

    _tap(app, "Supportive")

    assert backend.writes() == []
    assert _contents(app) == [GREETING, "Supportive", OPENERS["supportive"]]
    assert app.session_state.draft_style == "supportive"
    assert [b for b in app.button if b.label in ("Directive", "Supportive", "Reflective")] == []


def test_the_first_message_creates_the_thread_with_the_held_style():
    backend = DraftBackend()
    app = _open(backend)
    _tap(app, "Directive")

    app.chat_input[0].set_value("my boss again").run()

    assert not app.exception
    posts = [body for method, path, body in backend.calls if (method, path) == ("POST", "/v1/threads")]
    assert len(posts) == 1
    assert posts[0]["content"] == "my boss again" and posts[0]["style"] == "directive"
    assert backend.writes() == [("POST", "/v1/threads")]
    assert app.session_state.thread["id"] == "T"
    assert app.session_state.draft_style is None
    assert _contents(app) == [GREETING, "Directive", OPENERS["directive"], "my boss again", REPLY]
    # The opening stays without copy or edit, and the person's first message is the one that can be edited.
    copies = [h for h in app.get("html") if "data-copy" in h.proto.body]
    assert [c.proto.body.split('data-copy="')[1].split('"')[0] for c in copies] == ["my boss again", REPLY]
    assert [b for b in app.button if b.key == "edit_last"]


def test_a_first_message_without_a_tap_sends_no_style():
    backend = DraftBackend()
    app = _open(backend)

    app.chat_input[0].set_value("hello").run()

    posts = [body for method, path, body in backend.calls if (method, path) == ("POST", "/v1/threads")]
    assert [p["style"] for p in posts] == [None]
    assert _contents(app) == [GREETING, "hello", REPLY]


def test_a_thread_that_cannot_be_read_back_is_shown_from_the_reply_and_not_created_twice():
    backend = DraftBackend(history_fails=True)
    app = _open(backend)
    _tap(app, "Reflective")

    app.chat_input[0].set_value("hello").run()

    assert not app.exception
    assert backend.writes() == [("POST", "/v1/threads")]
    assert app.session_state.thread["id"] == "T"
    assert _contents(app) == [GREETING, "Reflective", OPENERS["reflective"], "hello", REPLY]


def test_opening_the_app_on_an_earlier_conversation_shows_it_and_not_a_draft():
    backend = DraftBackend(earlier=True)
    app = _open(backend)

    assert app.session_state.thread["id"] == "T"
    assert ("GET", "/v1/threads/opening", None) not in backend.calls


def _create_ids(backend: DraftBackend) -> list[str]:
    return [body["client_message_id"] for method, path, body in backend.calls if (method, path) == ("POST", "/v1/threads")]


def test_a_resent_first_message_carries_the_same_id_so_the_backend_makes_one_thread():
    backend = DraftBackend(creates_timing_out=1)
    app = _open(backend)

    app.chat_input[0].set_value("hello").run()
    assert app.session_state.thread is None
    app.chat_input[0].set_value("hello").run()

    assert not app.exception
    ids = _create_ids(backend)
    assert len(ids) == 2 and ids[0] == ids[1]
    assert app.session_state.thread["id"] == "T"


def test_a_changed_first_message_gets_a_new_id():
    backend = DraftBackend(creates_timing_out=1)
    app = _open(backend)

    app.chat_input[0].set_value("hello").run()
    app.chat_input[0].set_value("hello again").run()

    ids = _create_ids(backend)
    assert len(ids) == 2 and ids[0] != ids[1]
