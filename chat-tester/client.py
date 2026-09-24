# ABOUTME: A thin HTTP client for the real Mani API, plus a local-only way to get a token.
# ABOUTME: Everything a conversation does goes through the same endpoints a real app calls.

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any

import asyncpg
import jwt
import requests
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")

# A stable namespace so the same test-user name always mints the same id, and the same
# conversations are there next time you run this with that name.
_NAMESPACE = uuid.UUID("a0000000-0000-4000-8000-000000000000")


class ApiError(Exception):
    """What the backend actually said, in its own error shape."""

    def __init__(self, status: int, body: dict[str, Any]) -> None:
        self.status = status
        self.body = body
        error = body.get("error", {})
        super().__init__(f"{status} {error.get('category', 'unknown')}: {error.get('message')}")


def user_id_for(name: str) -> str:
    """A stable uuid for a test-user name, so re-entering the same name resumes it."""
    return str(uuid.uuid5(_NAMESPACE, name))


async def ensure_test_user(user_id: str, name: str) -> None:
    """The one thing a real sign-in does that this tool has to do by hand.

    A direct write to auth.users, which nothing in the application itself ever does -
    Supabase Auth owns that table. Fine here only because this talks to a local database
    this tool's own .env points at; it is not a path the backend or any real client takes.
    """
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set - copy .env.example to .env")
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute(
            """
            insert into auth.users (id, email) values ($1, $2)
            on conflict (id) do nothing
            """,
            uuid.UUID(user_id), f"{name}@chat-tester.local",
        )
    finally:
        await conn.close()


def mint_token(user_id: str) -> str:
    """A token shaped exactly like one Supabase would issue for this user.

    Signed with the same secret the backend verifies against - real verification, a
    substitute only for the sign-in step in front of it.
    """
    if not SUPABASE_JWT_SECRET:
        raise RuntimeError("SUPABASE_JWT_SECRET is not set - copy .env.example to .env")
    now = int(time.time())
    payload = {
        "sub": user_id, "role": "authenticated", "aud": "authenticated",
        "iat": now, "exp": now + 12 * 3600,
    }
    return jwt.encode(payload, SUPABASE_JWT_SECRET, algorithm="HS256")


@dataclass
class ManiClient:
    """Every call here is exactly what a real client's chat screen would make."""

    token: str
    base_url: str = API_BASE_URL

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def _call(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        response = requests.request(
            method, f"{self.base_url}{path}", headers=self._headers(), timeout=90, **kwargs
        )
        if not response.ok:
            raise ApiError(response.status_code, response.json())
        return response.json() if response.content else {}

    def start_or_resume_thread(self) -> dict[str, Any]:
        """POST /v1/threads/current - what a real app calls on opening the app."""
        return self._call("POST", "/v1/threads/current")

    def start_new_thread(self) -> dict[str, Any]:
        """POST /v1/threads - reuses an empty thread if the caller already has one,
        exactly as the backend does for a real "new chat" tap."""
        return self._call("POST", "/v1/threads", json={})

    def send_message(self, thread_id: str, content: str, client_message_id: str | None = None) -> dict[str, Any]:
        return self._call(
            "POST", f"/v1/threads/{thread_id}/messages",
            json={"content": content, "client_message_id": client_message_id or str(uuid.uuid4())},
        )

    def list_messages(self, thread_id: str) -> dict[str, Any]:
        return self._call("GET", f"/v1/threads/{thread_id}/messages")

    def set_profile(self, nickname: str) -> dict[str, Any]:
        """PUT /v1/profile - what onboarding calls, so the greeting can use their name."""
        return self._call("PUT", "/v1/profile", json={"nickname": nickname})

    def set_conversation_style(self, thread_id: str, style: str) -> dict[str, Any]:
        """PATCH /v1/threads/{id} - the same endpoint a style-picker screen would call."""
        return self._call("PATCH", f"/v1/threads/{thread_id}", json={"conversation_style": style})


async def framework_debug_state(thread_id: str) -> dict[str, Any] | None:
    """Direct read of thread_technique_state - not something a real client ever does.

    This is the one deliberate exception to "talk to the API like a real client": the
    whole point of this tool is watching when and which framework activates, and that
    state is not exposed on any response today. A dev-only inspector, read-only, clearly
    separate from the client calls above.
    """
    if not DATABASE_URL:
        return None
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow(
            "select framework_id, outcome, phase, at_message_count, library_offered_since "
            "from public.thread_technique_state where thread_id = $1",
            uuid.UUID(thread_id),
        )
        return dict(row) if row else None
    finally:
        await conn.close()


async def recent_call_costs(thread_id: str, limit: int = 5) -> list[dict[str, Any]]:
    """The last few admin.llm_calls rows for this thread - same caveat as above."""
    if not DATABASE_URL:
        return []
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        rows = await conn.fetch(
            "select purpose, outcome, model, input_tokens, output_tokens, "
            "cached_input_tokens, latency_ms, created_at "
            "from admin.llm_calls where thread_id = $1 order by created_at desc limit $2",
            uuid.UUID(thread_id), limit,
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def remembered(user_id: str) -> dict[str, Any] | None:
    """What Mani has folded together about this person across chats - admin.user_memory.

    Same caveat as the reads above: a dev-only window onto state no client response carries,
    here so a demo can show that a returning person's patterns were kept.
    """
    if not DATABASE_URL:
        return None
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow(
            "select memory, updated_at from admin.user_memory where user_id = $1",
            uuid.UUID(user_id),
        )
        if row is None:
            return None
        # A bare asyncpg connection returns jsonb as text; the backend's pool decodes it with a
        # codec this tool does not register.
        memory = row["memory"]
        return {"memory": json.loads(memory) if isinstance(memory, str) else memory,
                "updated_at": row["updated_at"]}
    finally:
        await conn.close()
