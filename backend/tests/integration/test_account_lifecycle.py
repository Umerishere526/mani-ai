# ABOUTME: Signup through account deletion, over real HTTP, as one system rather than parts.
# ABOUTME: The trigger, deletion, and auth enforcement each have narrower tests elsewhere -
# ABOUTME: this is the only place that proves they work together against a real signup.

from __future__ import annotations

import asyncio
import uuid

import asyncpg
import httpx
import pytest
from fastapi.testclient import TestClient

from main import create_app
from mani.chat import orchestrator
from mani.config import get_settings
from mani.llm.schema import Reply

# Deliberately a sync test, not async. TestClient runs the ASGI app on its own internal
# event loop via a background portal - an async test calling into the same shared
# mani.db.pool from a different loop hit `InterfaceError: cannot perform operation:
# another operation is in progress`, because asyncpg pools and connections are bound to
# the loop that created them. Sync test + TestClient used the way it's designed to be
# used, and each DB check below opens its own short-lived connection on whatever loop
# asyncio.run() gives it, independent of TestClient's internal one.


def _gotrue_reachable() -> bool:
    try:
        response = httpx.get(f"{get_settings().supabase_url}/auth/v1/health", timeout=2.0)
        return response.status_code == 200
    except httpx.HTTPError:
        return False


@pytest.fixture
def gotrue() -> str:
    """supabase_anon_key isn't used by this backend at runtime - only this test, to call
    GoTrue's public signup/signin endpoints the way a real client would. `supabase status`
    prints it; it's not a secret for local dev."""
    if not _gotrue_reachable():
        pytest.skip("no local Supabase Auth reachable; run `supabase start`")
    anon_key = get_settings().supabase_anon_key
    if not anon_key:
        pytest.skip("SUPABASE_ANON_KEY not set; run `supabase status` and add it to .env")
    return anon_key


@pytest.fixture
def model(monkeypatch):
    """Same fake test_turn.py uses, installed the same way - a plain module-attribute
    patch, so it applies whether the call originates from orchestrator.send() directly or,
    as here, from a request routed through TestClient's in-process ASGI transport."""
    scripted_calls = {"count": 0}

    async def scripted(messages, schema, **kwargs):
        from mani.db import llm_calls
        from mani.llm import client as client_module

        scripted_calls["count"] += 1
        return client_module.Call(
            value=Reply(text="How can I support you with that today?"),
            model="test/model",
            usage=llm_calls.Usage(input_tokens=100, output_tokens=20),
            latency_ms=1,
            call_id=uuid.uuid4(),
        )

    monkeypatch.setattr(orchestrator.client, "complete", scripted)
    return scripted_calls


def _row_count(database_url: str, table: str, user_id: uuid.UUID) -> int:
    async def query() -> int:
        conn = await asyncpg.connect(database_url, timeout=5)
        try:
            return await conn.fetchval(
                f"select count(*) from {table} where user_id = $1", user_id
            )
        finally:
            await conn.close()

    return asyncio.run(query())


def _remember(database_url: str, user_id: uuid.UUID) -> None:
    async def insert() -> None:
        conn = await asyncpg.connect(database_url, timeout=5)
        try:
            await conn.execute(
                "insert into admin.user_memory (user_id, memory) values ($1, $2)",
                user_id, '{"themes": ["should not survive the account"]}',
            )
        finally:
            await conn.close()

    asyncio.run(insert())


def test_signup_through_deletion_is_one_working_system(gotrue, model):
    anon_key = gotrue
    settings = get_settings()
    database_url = settings.database_url
    email = f"lifecycle-{uuid.uuid4().hex[:12]}@example.test"
    password = "a-genuinely-long-test-password"
    user_id: str | None = None

    try:
        with httpx.Client(timeout=10.0) as auth:
            # Real signup. Confirmed live against this project's GoTrue: with
            # enable_confirmations on, the response is the flat user object at the top
            # level - no "user" wrapper key, no session, no access_token. Don't
            # reintroduce a guessed nested path here.
            signup = auth.post(
                f"{settings.supabase_url}/auth/v1/signup",
                json={"email": email, "password": password},
                headers={"apikey": anon_key},
            )
            signup.raise_for_status()
            user_id = signup.json()["id"]
            assert "access_token" not in signup.json(), (
                "signup returned a session - enable_confirmations is not actually on; "
                "check supabase/config.toml and that Supabase Auth was restarted after "
                "editing it (config.toml is not hot-reloaded into the running container)"
            )

            # This backend doesn't own GoTrue's confirmation UX, only what happens once a
            # confirmed user exists - the Admin API is the correct tool to reach that
            # state directly rather than a bypass of anything this plan builds.
            confirm = auth.put(
                f"{settings.supabase_url}/auth/v1/admin/users/{user_id}",
                json={"email_confirm": True},
                headers={
                    "Authorization": f"Bearer {settings.supabase_service_role_key}",
                    "apikey": settings.supabase_service_role_key,
                },
            )
            confirm.raise_for_status()

            signin = auth.post(
                f"{settings.supabase_url}/auth/v1/token?grant_type=password",
                json={"email": email, "password": password},
                headers={"apikey": anon_key},
            )
            signin.raise_for_status()
            token = signin.json()["access_token"]

        # The signup trigger, proven against a real signup rather than a SQL fixture.
        assert _row_count(database_url, "public.profiles", uuid.UUID(user_id)) == 1, (
            "the signup trigger did not create a profile row"
        )

        headers = {"Authorization": f"Bearer {token}"}

        with TestClient(create_app()) as client:
            unauthenticated = client.post("/v1/threads", json={}, headers={})
            assert unauthenticated.status_code == 401

            start = client.post("/v1/threads", json={}, headers=headers)
            assert start.status_code == 201
            thread_id = start.json()["thread"]["id"]

            turn = client.post(
                f"/v1/threads/{thread_id}/messages",
                json={"content": "I don't know why I keep thinking about it"},
                headers=headers,
            )
            assert turn.status_code == 201
            assert turn.json()["content"]
            assert model["count"] == 1

            refused = client.post(
                f"/v1/threads/{thread_id}/messages",
                json={"content": "trying without a token"},
            )
            assert refused.status_code == 401

            # Real GoTrue deletes as supabase_auth_admin, which RLS applies to - the one path
            # test_rls.sql cannot assume on real Supabase, so the memory is checked here.
            _remember(database_url, uuid.UUID(user_id))

            deletion = client.delete("/v1/account", headers=headers)
            assert deletion.status_code == 204

        for table in (
            "public.profiles", "public.threads", "public.messages", "admin.user_memory",
        ):
            remaining = _row_count(database_url, table, uuid.UUID(user_id))
            assert remaining == 0, f"{table} still has rows after account deletion"
    finally:
        # Best-effort: if an assertion above failed before deletion ran, don't leave a
        # real account behind for the next run.
        if user_id is not None:
            httpx.delete(
                f"{settings.supabase_url}/auth/v1/admin/users/{user_id}",
                headers={
                    "Authorization": f"Bearer {settings.supabase_service_role_key}",
                    "apikey": settings.supabase_service_role_key,
                },
                timeout=10.0,
            )
