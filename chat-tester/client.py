# ABOUTME: A thin HTTP client for the real Mani API, signed in through local Supabase Auth.
# ABOUTME: Everything a conversation does goes through the same endpoints a real app calls.

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass
from typing import Any

import asyncpg
import requests
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "http://127.0.0.1:54341")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

# Every test user shares one password: a local tool against a local Supabase, where the name
# is the whole identity. The same name signs back in to the same conversations.
_PASSWORD = "chat-tester-local-only"
_EMAIL_DOMAIN = "tester.mani.local"


class ApiError(Exception):
    """What the backend actually said, in its own error shape."""

    def __init__(self, status: int, body: dict[str, Any]) -> None:
        self.status = status
        self.body = body
        error = body.get("error", {})
        if error:
            super().__init__(f"{status} {error.get('category', 'unknown')}: {error.get('message')}")
        else:
            # Not the backend's own error shape - a platform-level response (a host's
            # generic 404/500 page, a proxy timeout) that never reached our app at all.
            super().__init__(f"{status}: {body.get('raw', 'no body')}")


@dataclass
class Session:
    user_id: str
    access_token: str
    refresh_token: str


def _auth(path: str, body: dict[str, Any], key: str) -> requests.Response:
    try:
        return requests.post(
            f"{SUPABASE_URL}/auth/v1/{path}", json=body,
            headers={"apikey": key, "Authorization": f"Bearer {key}"}, timeout=10,
        )
    except requests.ConnectionError as exc:
        raise RuntimeError(
            f"Supabase Auth is not reachable at {SUPABASE_URL} - is `supabase start` running?"
        ) from exc


def _session(body: dict[str, Any]) -> Session:
    return Session(body["user"]["id"], body["access_token"], body["refresh_token"])


def _reason(response: requests.Response) -> str:
    """Supabase Auth's own words for a refusal, whichever field this endpoint puts them in."""
    try:
        body = response.json()
    except ValueError:
        return response.text
    return body.get("msg") or body.get("error_description") or body.get("message") or response.text


def _require_keys() -> None:
    if not (SUPABASE_ANON_KEY and SUPABASE_SERVICE_ROLE_KEY):
        raise RuntimeError(
            "SUPABASE_ANON_KEY and SUPABASE_SERVICE_ROLE_KEY are not set - "
            "`supabase status -o env` prints both; see .env.example"
        )


def sign_in_with_password(email: str, password: str) -> Session:
    """A real Supabase sign-in, so the backend verifies these tokens exactly as a phone's."""
    _require_keys()
    response = _auth(
        "token?grant_type=password", {"email": email.strip(), "password": password},
        SUPABASE_ANON_KEY,
    )
    if not response.ok:
        raise RuntimeError(f"Could not sign in: {_reason(response)}")
    return _session(response.json())


def sign_up(email: str, password: str) -> Session:
    """A new test account, created confirmed, then signed straight in.

    Created through the Admin API rather than the public signup endpoint. Signup sends a
    real confirmation email even when nothing ever reads it, and the project's default mail
    service allows only two an hour - a limit meant for a handful of early logins, not a demo
    tool creating test accounts. Admin-created users need no confirming and send no mail, so
    the same two calls every deploy target uses (Admin API, then a password sign-in) never
    touch that limit.
    """
    _require_keys()
    email = email.strip()
    created = requests.post(
        f"{SUPABASE_URL}/auth/v1/admin/users",
        json={"email": email, "password": password, "email_confirm": True},
        headers={"apikey": SUPABASE_SERVICE_ROLE_KEY,
                 "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}"},
        timeout=10,
    )
    if not created.ok:
        raise RuntimeError(f"Could not sign up: {_reason(created)}")
    return sign_in_with_password(email, password)


def sign_in(name: str) -> Session:
    """A quick test user by name: the same name signs back in to the same conversations."""
    slug = re.sub(r"[^a-z0-9._-]+", "-", name.strip().lower()).strip("-") or "tester"
    email = f"{slug}@{_EMAIL_DOMAIN}"
    try:
        return sign_in_with_password(email, _PASSWORD)
    except RuntimeError:
        return sign_up(email, _PASSWORD)


def refresh(session: Session) -> Session:
    """A new access token for the same session, as a real app gets one when it expires."""
    response = _auth(
        "token?grant_type=refresh_token", {"refresh_token": session.refresh_token},
        SUPABASE_ANON_KEY,
    )
    if not response.ok:
        raise RuntimeError(f"could not refresh the session: {response.text}")
    return _session(response.json())


@dataclass
class ManiClient:
    """Every call here is exactly what a real client's chat screen would make."""

    session: Session
    base_url: str = API_BASE_URL

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        headers = {
            "Authorization": f"Bearer {self.session.access_token}",
            "Content-Type": "application/json",
        }
        return requests.request(
            method, f"{self.base_url}{path}", headers=headers, timeout=90, **kwargs
        )

    def _call(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        response = self._request(method, path, **kwargs)
        if response.status_code == 401:
            # Supabase access tokens last an hour; a demo runs longer than that.
            self.session = refresh(self.session)
            response = self._request(method, path, **kwargs)
        if not response.ok:
            try:
                body = response.json()
            except requests.exceptions.JSONDecodeError:
                # A platform-level page (host 404, proxy timeout) never shaped like ours.
                body = {"raw": response.text[:300]}
            raise ApiError(response.status_code, body)
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
