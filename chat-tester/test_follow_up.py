# ABOUTME: Checks the chat tester asks for the work after a reply, and the memory fold after a new chat, off the wait.
# ABOUTME: A fake backend records the calls; needs no services.

from __future__ import annotations

import threading

import client as mani


class Backend(mani.ManiClient):
    def __init__(self, answer: dict, fail_after: bool = False) -> None:
        super().__init__(session=mani.Session("user", "token", "refresh"))
        self.answer = answer
        self.fail_after = fail_after
        self.calls: list[tuple[str, str]] = []
        self.after = threading.Event()

    def _call(self, method, path, **kwargs):
        self.calls.append((method, path))
        if path.endswith(("/follow-up", "/memory-fold")):
            self.after.set()
            if self.fail_after:
                raise mani.ApiError(500, {"error": {"category": "internal", "message": "down"}})
            return {}
        return self.answer


def test_a_reply_with_work_waiting_asks_for_it_by_the_reply():
    backend = Backend({"id": "m1", "content": "What happened?", "follow_up_pending": True})

    turn = backend.send_message("T", "my brother never calls")

    assert turn["content"] == "What happened?"
    assert backend.after.wait(2)
    assert ("POST", "/v1/threads/T/messages/m1/follow-up") in backend.calls


def test_an_edit_asks_for_its_follow_up_too():
    backend = Backend({"id": "m2", "content": "What happened?", "follow_up_pending": True})

    backend.edit_message("T", "u1", "better words")

    assert backend.after.wait(2)
    assert ("POST", "/v1/threads/T/messages/m2/follow-up") in backend.calls


def test_a_reply_with_nothing_waiting_asks_for_nothing():
    backend = Backend({"id": "m1", "content": "Take your time.", "follow_up_pending": False})

    backend.send_message("T", "I need a minute")

    assert not backend.after.wait(0.2)


def test_a_new_chat_asks_for_the_earlier_ones_to_be_folded_into_memory():
    backend = Backend({"thread": {"id": "T2"}, "messages": [], "is_new": True, "memory_fold_pending": True})

    backend.start_new_thread()

    assert backend.after.wait(2)
    assert ("POST", "/v1/threads/T2/memory-fold") in backend.calls


def test_a_failed_follow_up_never_reaches_the_conversation():
    backend = Backend({"id": "m1", "content": "What happened?", "follow_up_pending": True}, fail_after=True)

    turn = backend.send_message("T", "my brother never calls")

    assert turn["content"] == "What happened?"
    assert backend.after.wait(2)
