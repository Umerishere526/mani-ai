# ABOUTME: The opening is read-only and a person's first message creates their conversation, over HTTP.
# ABOUTME: Against a live database with a scripted model: what each route writes, and what a failed or retried start leaves.

import asyncio
import datetime as dt
import uuid

import httpx
import pytest

from main import create_app
from mani.auth.deps import current_user
from mani.chat import orchestrator
from mani.chat.greeting import greeting
from mani.config import get_settings
from mani.db import llm_calls, pool, profiles, threads
from mani.db import messages as messages_db
from mani.errors import ErrorCategory, ServiceError
from mani.llm import client
from mani.llm.schema import Memory, Reply
from tests.integration.test_turn import ALICE, ScriptedModel, alice, claims_for, model  # noqa: F401 - alice and model are fixtures

OPENING = "Hi Al. It's MANI. How would you like me to speak with you today?"


@pytest.fixture
async def api(alice):  # noqa: F811
    """The app's routes over HTTP as Alice, on the pool the fixture opened. Sign-in is covered in test_endpoint_auth."""
    async with pool.as_user(alice) as conn:
        await profiles.upsert(conn, ALICE, nickname="Al")
    app = create_app()
    app.dependency_overrides[current_user] = lambda: alice
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield client


async def _threads_kept() -> int:
    async with pool.as_admin() as conn:
        return await conn.fetchval(
            "select count(*) from public.threads where user_id = $1 and deleted_at is null", ALICE
        )


async def _transcript(thread_id) -> list[tuple[str, str, str | None]]:
    async with pool.as_user(claims_for(ALICE)) as conn:
        history = await messages_db.for_context(
            conn, thread_id, ALICE, budget_chars=get_settings().context_budget_chars
        )
    return [(m.role, m.content, m.selected_prompt) for m in history.messages]


async def test_opening_writes_nothing(api):
    response = await api.get("/v1/threads/opening")

    assert response.status_code == 200
    opening = response.json()
    assert opening["greeting"] == OPENING
    assert [option["style"] for option in opening["style_options"]] == ["directive", "supportive", "reflective"]
    assert opening["openers"]["supportive"] == "How can I support you today?"
    assert opening["chat_paused_until"] is None and opening["chat_paused_from"] is None
    assert await _threads_kept() == 0


async def test_the_opening_says_again_once_they_have_written_in_an_earlier_chat(api, model):  # noqa: F811
    model(Reply(text="Go on."))
    await api.post("/v1/threads", json={"content": "work was hard"})

    opening = (await api.get("/v1/threads/opening")).json()

    assert opening["greeting"] == greeting("Al", returning=True)


async def test_current_writes_nothing_for_a_new_account(api):
    response = await api.get("/v1/threads/current")

    assert response.status_code == 200
    assert response.json() == {"thread": None, "messages": []}
    assert await _threads_kept() == 0


async def test_the_first_message_creates_the_thread_with_its_opening(api, model):  # noqa: F811
    model(Reply(text="I'm here. What has been going on?"))

    response = await api.post("/v1/threads", json={"content": "I've been feeling low", "style": "supportive"})

    assert response.status_code == 201
    started = response.json()
    assert started["thread"]["message_count"] == 5
    assert started["thread"]["conversation_style"] == "supportive"
    assert started["turn"]["content"] == "I'm here. What has been going on?"
    assert await _transcript(started["thread"]["id"]) == [
        ("mani", OPENING, None),
        ("user", "Supportive", "Supportive"),
        ("mani", "How can I support you today?", None),
        ("user", "I've been feeling low", None),
        ("mani", "I'm here. What has been going on?", None),
    ]

    current = (await api.get("/v1/threads/current")).json()
    assert current["thread"]["id"] == started["thread"]["id"]
    assert len(current["messages"]) == 5


async def test_the_first_message_without_a_style_writes_no_tap(api, model):  # noqa: F811
    model(Reply(text="I'm here. What has been going on?"))

    response = await api.post("/v1/threads", json={"content": "I've been feeling low"})

    assert response.status_code == 201
    thread = response.json()["thread"]
    assert thread["message_count"] == 3
    assert thread["conversation_style"] is None
    assert [role for role, _, _ in await _transcript(thread["id"])] == ["mani", "user", "mani"]


async def test_a_failed_first_turn_leaves_no_thread_in_view(api, monkeypatch):
    async def down(*args, **kwargs):
        raise ServiceError("the model is down", ErrorCategory.LLM_UNAVAILABLE)

    monkeypatch.setattr(orchestrator.client, "complete", down)

    response = await api.post("/v1/threads", json={"content": "I've been feeling low", "style": "supportive"})

    assert response.status_code == 502
    async with pool.as_user(claims_for(ALICE)) as conn:
        assert (await threads.list_for_user(conn, ALICE)).threads == []
    assert await _threads_kept() == 0


async def test_a_retried_first_message_returns_the_same_thread(api, model):  # noqa: F811
    scripted = model(Reply(text="I'm here. What has been going on?"), Reply(text="A different answer."))
    body = {"content": "I've been feeling low", "style": "supportive", "client_message_id": str(uuid.uuid4())}

    first = (await api.post("/v1/threads", json=body)).json()
    again = (await api.post("/v1/threads", json=body)).json()

    assert again["thread"]["id"] == first["thread"]["id"]
    assert again["turn"]["was_duplicate"] is True
    assert again["turn"]["content"] == first["turn"]["content"]
    assert scripted.calls == 1
    assert await _threads_kept() == 1


async def test_a_retry_arriving_while_the_first_try_waits_on_the_model_gets_that_turn(api, monkeypatch):
    scripted = ScriptedModel(Reply(text="I'm here. What has been going on?"), Reply(text="A different answer."))

    async def slow(messages, schema, **kwargs):
        await asyncio.sleep(0.3)
        return await scripted(messages, schema, **kwargs)

    monkeypatch.setattr(orchestrator.client, "complete", slow)
    body = {"content": "I've been feeling low", "style": "supportive", "client_message_id": str(uuid.uuid4())}

    first, retry = await asyncio.gather(api.post("/v1/threads", json=body), api.post("/v1/threads", json=body))

    assert (first.status_code, retry.status_code) == (201, 201)
    assert retry.json()["thread"]["id"] == first.json()["thread"]["id"]
    assert scripted.calls == 1
    assert await _threads_kept() == 1


async def test_a_chat_begun_while_the_memory_fold_runs_is_not_folded_by_it(api, monkeypatch):
    """The fold is asked for when they open a new conversation, so their first message can land while it still runs."""
    chat = ScriptedModel(Reply(text="Go on."))
    reached_the_model, let_it_answer = asyncio.Event(), asyncio.Event()

    async def answering(messages, schema, **kwargs):
        if schema is not Memory:
            return await chat(messages, schema, **kwargs)
        reached_the_model.set()
        await let_it_answer.wait()
        return client.Call(
            value=Memory(), model="test/model", usage=llm_calls.Usage(), latency_ms=1, call_id=None
        )

    monkeypatch.setattr(orchestrator.client, "complete", answering)
    finished = (await api.post("/v1/threads", json={"content": "work was hard"})).json()["thread"]["id"]
    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.threads set last_message_at = now() - interval '1 minute' where id = $1", finished
        )

    fold = asyncio.create_task(api.post("/v1/threads/memory-fold"))
    await asyncio.wait_for(reached_the_model.wait(), timeout=5)
    begun = (await api.post("/v1/threads", json={"content": "my brother never calls"})).json()["thread"]["id"]
    let_it_answer.set()
    response = await fold

    assert response.json() == {"folded": 1}
    async with pool.as_admin() as conn:
        folded_at = {
            row["id"]: row["memory_folded_at"]
            for row in await conn.fetch(
                "select id::text, memory_folded_at from public.threads where user_id = $1", ALICE
            )
        }
    assert folded_at[finished] is not None
    assert folded_at[begun] is None


async def _paused(thread_id) -> None:
    async with pool.as_admin() as conn:
        await conn.execute(
            "insert into public.chat_pauses (user_id, thread_id, ends_at, reason) "
            "values ($1, $2, now() + interval '15 minutes', 'why')",
            ALICE, thread_id,
        )


def _length(start: str, end: str) -> dt.timedelta:
    """How long a pause runs, from the two times a response gives."""
    return dt.datetime.fromisoformat(end) - dt.datetime.fromisoformat(start)


async def _a_thread() -> uuid.UUID:
    async with pool.as_user(claims_for(ALICE)) as conn:
        return (await orchestrator.start_thread(conn, claims_for(ALICE))).id


async def test_every_chat_route_refuses_while_paused(api, model):  # noqa: F811
    scripted = model(Reply(text="Go on."))
    thread_id = await _a_thread()
    await _paused(thread_id)
    message = f"/v1/threads/{thread_id}/messages"
    asked = uuid.uuid4()

    responses = [
        await api.post("/v1/threads", json={"content": "hello"}),
        await api.post(message, json={"content": "hello"}),
        await api.post(f"{message}/{asked}/edit", json={"content": "hello"}),
        await api.post(f"{message}/{asked}/follow-up"),
    ]

    for response in responses:
        assert response.status_code == 423
        assert response.json()["error"]["category"] == "chat_paused"
        details = response.json()["error"]["details"]
        assert _length(details["paused_from"], details["paused_until"]) == dt.timedelta(minutes=15)
    assert scripted.calls == 0
    assert await _threads_kept() == 1, "the refused create made no conversation"


async def test_the_library_and_profile_stay_open_while_paused(api, monkeypatch):
    async def unsigned(path):
        return None

    # The library's route is under test, not Supabase Storage.
    monkeypatch.setattr("mani.routers.exercises.signed_audio_url", unsigned)
    thread_id = await _a_thread()
    await _paused(thread_id)

    assert (await api.get("/v1/exercises")).status_code == 200
    assert (await api.get("/v1/crisis/resources")).status_code == 200
    profile = await api.get("/v1/profile")
    assert profile.status_code == 200
    assert _length(profile.json()["chat_paused_from"], profile.json()["chat_paused_until"]) == dt.timedelta(minutes=15)
    opening = (await api.get("/v1/threads/opening")).json()
    assert _length(opening["chat_paused_from"], opening["chat_paused_until"]) == dt.timedelta(minutes=15)
    assert (await api.get(f"/v1/threads/{thread_id}/messages")).status_code == 200
