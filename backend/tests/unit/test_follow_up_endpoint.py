# ABOUTME: Nothing runs after a response any more: the turn awaits its writes, and the app asks for the rest.
# ABOUTME: Over HTTP with the turn and the follow-up faked, so this checks the wiring, not the work.

import datetime as dt
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mani.auth.deps import Participant, require_chat_open
from mani.auth.jwt import Claims
from mani.chat import turn as chat_turn
from mani.routers import messages as messages_router
from main import create_app
from tests.unit.test_endpoint_auth import USER, _token, secret  # noqa: F401 - secret is a fixture

THREAD = uuid.uuid4()
REPLY = uuid.uuid4()


async def _no_pause(user: Participant) -> Claims:
    """The chat-open check with no pause on record, so the wiring is checked without a database."""
    return user


def _app() -> FastAPI:
    app = create_app()
    app.dependency_overrides[require_chat_open] = _no_pause
    return app


def _turn(needs_summary: bool = False, was_duplicate: bool = False) -> chat_turn.Turn:
    return chat_turn.Turn(
        message_id=REPLY, content="What happened?", created_at=dt.datetime.now(dt.UTC), llm_call_id=uuid.uuid4(),
        trace={"action": "none"}, was_duplicate=was_duplicate, needs_summary=needs_summary,
    )


@pytest.fixture
def wired(monkeypatch, secret):  # noqa: F811
    seen = {"follow_ups": [], "links": [], "traces": []}

    async def follow_up(user, thread_id, message_id):
        seen["follow_ups"].append((user.user_id, thread_id, message_id))
        return chat_turn.FollowedUp(summarized=True)

    async def link_call(call_id, message_id):
        seen["links"].append(message_id)

    async def record_trace(turn, thread_id):
        seen["traces"].append(turn.message_id)

    monkeypatch.setattr(chat_turn, "follow_up", follow_up)
    monkeypatch.setattr(chat_turn, "link_call", link_call)
    monkeypatch.setattr(chat_turn, "record_trace", record_trace)
    return seen, {"Authorization": f"Bearer {_token(secret)}"}


def _send(monkeypatch, headers, turn) -> dict:
    async def send(*args, **kwargs):
        return turn

    monkeypatch.setattr(messages_router.runner, "send", send)
    with TestClient(_app()) as client:
        response = client.post(f"/v1/threads/{THREAD}/messages", json={"content": "my brother never calls"},
                               headers=headers)
    assert response.status_code == 201
    return response.json()


@pytest.mark.parametrize(("turn", "pending"), [
    (_turn(needs_summary=True), True),
    (_turn(), False),
    (_turn(needs_summary=True, was_duplicate=True), False),
])
def test_a_turn_says_whether_work_waits_for_after_its_reply(wired, monkeypatch, turn, pending):
    """On Vercel the instance stops once the response is sent, and work started after it was cut off (2026-11-05)."""
    _, headers = wired
    assert _send(monkeypatch, headers, turn)["follow_up_pending"] is pending


def test_the_call_link_and_the_trace_are_written_before_the_response(wired, monkeypatch):
    seen, headers = wired
    _send(monkeypatch, headers, _turn())
    assert seen["links"] == [REPLY] and seen["traces"] == [REPLY]


def test_the_follow_up_endpoint_reports_read_false_and_summarizes(wired):
    seen, headers = wired
    with TestClient(_app()) as client:
        response = client.post(f"/v1/threads/{THREAD}/messages/{REPLY}/follow-up", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"read": False, "summarized": True, "pending": False, "understanding": None}, (
        "nothing reads the conversation after a reply any more; only the summary runs"
    )
    assert seen["follow_ups"] == [(USER, THREAD, REPLY)]


def test_the_follow_up_endpoint_needs_a_token(wired):
    seen, _ = wired
    with TestClient(_app()) as client:
        assert client.post(f"/v1/threads/{THREAD}/messages/{REPLY}/follow-up").status_code == 401
    assert seen["follow_ups"] == []
