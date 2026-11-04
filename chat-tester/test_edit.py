# ABOUTME: Checks that an edit is addressed to the person's newest message and posted to the edit endpoint.
# ABOUTME: Serves history from a fake backend and records the call; needs no services.

from __future__ import annotations

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
