# ABOUTME: Nothing runs after a response any more: the turn awaits its writes, and the app asks for the rest.
# ABOUTME: Over HTTP with the turn, the follow-up and the fold faked, so this checks the wiring, not the work.

import datetime as dt
import uuid

import pytest
from fastapi.testclient import TestClient

from mani import memory
from mani.chat import orchestrator
from mani.routers import messages as messages_router
from main import create_app
from tests.unit.test_endpoint_auth import USER, _token, secret  # noqa: F401 - secret is a fixture

THREAD = uuid.uuid4()
REPLY = uuid.uuid4()


def _turn(read_after: bool = False, needs_summary: bool = False, was_duplicate: bool = False) -> orchestrator.Turn:
    job = orchestrator.ReadAfter(
        thread_id=THREAD, user_id=uuid.UUID(USER), message_id=REPLY, messages=[], model="test/model",
        parameters={}, routing=None,
    )
    return orchestrator.Turn(
        message_id=REPLY, content="What happened?", created_at=dt.datetime.now(dt.UTC), llm_call_id=uuid.uuid4(),
        trace={"moment": "chatting"}, was_duplicate=was_duplicate, needs_summary=needs_summary,
        read_after=job if read_after else None,
    )


@pytest.fixture
def wired(monkeypatch, secret):  # noqa: F811
    seen = {"follow_ups": [], "links": [], "traces": [], "folds": []}

    async def follow_up(user, thread_id, message_id):
        seen["follow_ups"].append((user.user_id, thread_id, message_id))
        return orchestrator.FollowedUp(understanding={"heart": "exploring"}, summarized=True)

    async def link_call(call_id, message_id):
        seen["links"].append(message_id)

    async def record_trace(turn, thread_id):
        seen["traces"].append(turn.message_id)

    async def fold_finished(user, *, keep=None, idle_before=None):
        seen["folds"].append((user.user_id, keep))
        return 2

    monkeypatch.setattr(orchestrator, "follow_up", follow_up)
    monkeypatch.setattr(orchestrator, "link_call", link_call)
    monkeypatch.setattr(orchestrator, "record_trace", record_trace)
    monkeypatch.setattr(memory, "fold_finished", fold_finished)
    return seen, {"Authorization": f"Bearer {_token(secret)}"}


def _send(monkeypatch, headers, turn) -> dict:
    async def send(*args, **kwargs):
        return turn

    monkeypatch.setattr(messages_router.runner, "send", send)
    with TestClient(create_app()) as client:
        response = client.post(f"/v1/threads/{THREAD}/messages", json={"content": "my brother never calls"},
                               headers=headers)
    assert response.status_code == 201
    return response.json()


@pytest.mark.parametrize(("turn", "pending"), [
    (_turn(read_after=True), True),
    (_turn(needs_summary=True), True),
    (_turn(), False),
    (_turn(read_after=True, needs_summary=True, was_duplicate=True), False),
])
def test_a_turn_says_whether_work_waits_for_after_its_reply(wired, monkeypatch, turn, pending):
    """On Vercel the instance stops once the response is sent, and work started after it was cut off (2026-11-05)."""
    _, headers = wired
    assert _send(monkeypatch, headers, turn)["follow_up_pending"] is pending


def test_the_call_link_and_the_trace_are_written_before_the_response(wired, monkeypatch):
    seen, headers = wired
    _send(monkeypatch, headers, _turn())
    assert seen["links"] == [REPLY] and seen["traces"] == [REPLY]


def test_the_follow_up_endpoint_runs_what_waits_for_that_reply(wired):
    seen, headers = wired
    with TestClient(create_app()) as client:
        response = client.post(f"/v1/threads/{THREAD}/messages/{REPLY}/follow-up", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"read": True, "summarized": True, "pending": False, "understanding": None}, (
        "what Mani understands goes to a client only in debug mode"
    )
    assert seen["follow_ups"] == [(USER, THREAD, REPLY)]


def test_the_memory_fold_endpoint_folds_every_finished_chat_but_the_new_one(wired):
    seen, headers = wired
    with TestClient(create_app()) as client:
        response = client.post(f"/v1/threads/{THREAD}/memory-fold", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"folded": 2}
    assert seen["folds"] == [(USER, THREAD)]


@pytest.mark.parametrize("path", [f"/v1/threads/{THREAD}/messages/{REPLY}/follow-up",
                                  f"/v1/threads/{THREAD}/memory-fold"])
def test_the_after_work_endpoints_need_a_token(wired, path):
    seen, _ = wired
    with TestClient(create_app()) as client:
        assert client.post(path).status_code == 401
    assert seen["follow_ups"] == [] and seen["folds"] == []
