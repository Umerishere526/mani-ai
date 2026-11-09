# ABOUTME: Progress memory is the person's: they can read, correct and delete it, and switching it off forgets it.
# ABOUTME: Over HTTP with the database calls faked, so this checks the wiring and the limits, not the storage.

import pytest
from fastapi.testclient import TestClient

from mani import memory
from mani.db import memory as memory_db, profiles
from mani.llm.schema import Memory, ProgressMemory
from main import create_app
from tests.unit.test_endpoint_auth import USER, _token, secret  # noqa: F401 - secret is a fixture

KEPT = ProgressMemory(realised=["I can be capable without being perfect"], working_on=["checking work over and over"])


@pytest.fixture
def wired(monkeypatch, secret):  # noqa: F811
    seen = {"saved": [], "forgot": 0}

    async def get(conn, user_id):
        return Memory(progress=KEPT)

    async def save_progress(conn, user_id, progress):
        seen["saved"].append(progress)
        return Memory(progress=progress)

    async def forget_progress(conn, user_id):
        seen["forgot"] += 1

    async def upsert(conn, user_id, **fields):
        seen["profile"] = fields
        from mani.models.rows import Profile

        return Profile(user_id=USER, remember_progress=fields.get("remember_progress") is not False)

    monkeypatch.setattr(memory_db, "get", get)
    monkeypatch.setattr(memory_db, "save_progress", save_progress)
    monkeypatch.setattr(memory_db, "forget_progress", forget_progress)
    monkeypatch.setattr(profiles, "upsert", upsert)

    class _Conn:
        pass

    async def user_conn():
        yield _Conn()

    from mani.db.deps import user_conn as real

    app = create_app()
    app.dependency_overrides[real] = user_conn
    return TestClient(app), {"Authorization": f"Bearer {_token(secret)}"}, seen


def test_they_can_read_correct_and_delete_what_mani_carries_forward(wired):
    client, headers, seen = wired
    with client:
        read = client.get("/v1/memory/progress", headers=headers)
        assert read.status_code == 200 and read.json()["realised"] == ["I can be capable without being perfect"]
        fixed = client.put("/v1/memory/progress", json={"realised": ["mistakes don't define me"]}, headers=headers)
        assert fixed.status_code == 200 and fixed.json()["realised"] == ["mistakes don't define me"]
        assert client.delete("/v1/memory/progress", headers=headers).status_code == 204
        assert client.put("/v1/memory/progress", json={"realised": ["x" * 161]}, headers=headers).status_code == 422
    assert seen["saved"] == [ProgressMemory(realised=["mistakes don't define me"])] and seen["forgot"] == 1


def test_switching_remember_progress_off_forgets_what_was_kept_at_once(wired):
    client, headers, seen = wired
    with client:
        response = client.put("/v1/profile", json={"remember_progress": False}, headers=headers)
    assert response.status_code == 200 and response.json()["remember_progress"] is False
    assert seen["forgot"] == 1


def test_progress_is_bounded_and_dropped_when_it_is_not_to_be_kept():
    many = Memory(progress=ProgressMemory(trying=[f"step {n}" for n in range(9)], realised=["  ", "x" * 300]))
    assert len(memory.bounded(many).progress.trying) == memory.MAX_ENTRIES
    assert memory.bounded(many).progress.realised == ["x" * memory.MAX_ENTRY_CHARS]
    assert memory.bounded(many, keep_progress=False).progress == ProgressMemory()
