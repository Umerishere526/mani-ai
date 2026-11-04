# ABOUTME: Checks that an edit is addressed to the person's newest message and posted to the edit endpoint.
# ABOUTME: Serves history from a fake backend and records the call; needs no services.

from __future__ import annotations

import base64
import pathlib

from streamlit.testing.v1 import AppTest

import client as mani


class RecordingBackend(mani.ManiClient):
    def __init__(self) -> None:
        super().__init__(session=mani.Session("user", "token", "refresh"))
        self.calls: list[tuple] = []

    def _call(self, method, path, **kwargs):
        self.calls.append((method, path, kwargs.get("json")))
        if method == "GET":
            messages = [
                {"id": "u1", "role": "user"}, {"id": "m1", "role": "mani"},
                {"id": "u2", "role": "user"}, {"id": "m2", "role": "mani"},
            ]
            return {"messages": messages[::-1], "next_cursor": None}
        return {"content": "new reply"}


def test_an_edit_targets_the_newest_user_message():
    backend = RecordingBackend()

    message_id = backend.last_user_message_id("thread")
    backend.edit_message("thread", message_id, "better words")

    assert message_id == "u2"
    assert backend.calls[-1] == ("POST", "/v1/threads/thread/messages/u2/edit", {"content": "better words"})


class EditScreenBackend(mani.ManiClient):
    def __init__(self) -> None:
        token = "h." + base64.urlsafe_b64encode(b'{"role":"authenticated"}').decode().rstrip("=") + ".s"
        super().__init__(session=mani.Session("user", token, "refresh"))
        self.edits: list[str] = []

    def start_or_resume_thread(self):
        thread = {"id": "T", "message_count": 4, "crisis_detected": False, "conversation_style": "supportive", "title": None}
        return {"is_new": False, "thread": thread, "messages": [
            {"id": "m0", "role": "mani", "content": "Hi", "prompts": []},
            {"id": "u1", "role": "user", "content": "first"},
            {"id": "m1", "role": "mani", "content": "reply", "prompts": []},
        ]}

    def list_threads(self, limit=50):
        return []

    def get_profile(self):
        return {}

    def last_user_message_id(self, thread_id):
        return "u1"

    def edit_message(self, thread_id, message_id, content):
        self.edits.append(content)
        if not content.replace("​", "").strip():
            raise mani.ApiError(422, {"error": {"category": "invalid_request", "message": "Write a message first."}})
        return {"content": "new reply", "prompts": [], "id": "x"}


def test_the_edit_screen_tells_them_what_to_do_and_only_sends_a_real_change():
    app = AppTest.from_file(str(pathlib.Path(__file__).with_name("app.py")), default_timeout=20)
    backend = EditScreenBackend()
    app.session_state["email"], app.session_state["client"] = "a@b.c", backend
    app.run()

    def press_send(text):
        app.text_area(key="edit_text").set_value(text).run()
        next(b for b in app.button if b.key == "edit_send").click().run()
        return [t.value for t in app.toast]

    next(b for b in app.button if b.key == "edit_last").click().run()
    assert "Nothing has changed" in press_send("first")[0]
    assert "can't be empty" in press_send("   ")[0]
    assert press_send("​​") == ["Write a message first."]
    assert app.session_state.editing and backend.edits == ["​​"]

    press_send("better words")
    assert not app.session_state.editing and backend.edits[-1] == "better words"
    assert app.session_state.messages[-1]["content"] == "new reply"


class OpeningOnlyBackend(EditScreenBackend):
    def start_or_resume_thread(self):
        thread = {"id": "T", "message_count": 3, "crisis_detected": False, "conversation_style": "directive", "title": None}
        return {"is_new": False, "thread": thread, "messages": [
            {"id": "m0", "role": "mani", "content": "Hi there. How would you like me to speak with you today?", "prompts": []},
            {"id": "u1", "role": "user", "content": "Directive"},
            {"id": "m1", "role": "mani", "content": "How can I help you today?", "prompts": []},
        ]}


def test_the_greeting_the_style_they_tapped_and_the_opener_have_no_copy_or_edit():
    app = AppTest.from_file(str(pathlib.Path(__file__).with_name("app.py")), default_timeout=20)
    app.session_state["email"], app.session_state["client"] = "a@b.c", OpeningOnlyBackend()
    app.run()

    assert not [b for b in app.button if b.key == "edit_last"]
    assert not [h for h in app.get("html") if "mani-copy" in h.proto.body and "data-copy" in h.proto.body]


def test_after_the_opening_copy_and_edit_sit_on_one_row():
    app = AppTest.from_file(str(pathlib.Path(__file__).with_name("app.py")), default_timeout=20)
    app.session_state["email"], app.session_state["client"] = "a@b.c", EditScreenBackend()
    app.run()

    copies = [h for h in app.get("html") if "data-copy" in h.proto.body]
    assert [c.proto.body.split('data-copy="')[1].split('"')[0] for c in copies] == ["first", "reply"]
    assert [b for b in app.button if b.key == "edit_last"]
