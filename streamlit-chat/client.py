# ABOUTME: A thin HTTP client for the local Mani API, signed in through local Supabase
# ABOUTME: Auth, plus the streaming message endpoint, consumed as raw SSE frames.

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import httpx
import httpx_sse


def _load_env() -> None:
    """The .env beside this file, KEY=VALUE per line; real environment variables win.

    Hand-rolled so the tool needs no python-dotenv dependency.
    """
    try:
        with open(os.path.join(os.path.dirname(__file__), ".env")) as handle:
            for line in handle:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip().strip("\"'"))
    except FileNotFoundError:
        pass


_load_env()

API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8001")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "http://127.0.0.1:54341")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

# A turn can stream for a long while; only the gaps between reads are bounded.
STREAM_TIMEOUT = httpx.Timeout(connect=10.0, read=300.0, write=30.0, pool=30.0)


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


def _error_body(response: httpx.Response) -> dict[str, Any]:
    try:
        return response.json()
    except ValueError:
        return {"raw": response.text[:300]}


@dataclass
class Session:
    user_id: str
    access_token: str
    refresh_token: str


def _auth(path: str, body: dict[str, Any], key: str) -> httpx.Response:
    try:
        return httpx.post(
            f"{SUPABASE_URL}/auth/v1/{path}", json=body,
            headers={"apikey": key, "Authorization": f"Bearer {key}"}, timeout=10,
        )
    except httpx.ConnectError as exc:
        raise RuntimeError(
            f"Supabase Auth is not reachable at {SUPABASE_URL} - is `supabase start` running?"
        ) from exc


def _session(body: dict[str, Any]) -> Session:
    return Session(body["user"]["id"], body["access_token"], body["refresh_token"])


def _reason(response: httpx.Response) -> str:
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
            "`supabase status -o env` prints both"
        )


def sign_in_with_password(email: str, password: str) -> Session:
    """A real Supabase sign-in, so the backend verifies these tokens exactly as a phone's."""
    _require_keys()
    response = _auth(
        "token?grant_type=password", {"email": email.strip(), "password": password},
        SUPABASE_ANON_KEY,
    )
    if not response.is_success:
        raise RuntimeError(f"Could not sign in: {_reason(response)}")
    return _session(response.json())


def sign_up(email: str, password: str) -> Session:
    """A new test account, created confirmed through the Admin API, then signed in.

    Admin-created users need no confirming and send no mail, so the demo never touches
    the project's email rate limit - the same two calls chat-tester makes.
    """
    _require_keys()
    email = email.strip()
    created = httpx.post(
        f"{SUPABASE_URL}/auth/v1/admin/users",
        json={"email": email, "password": password, "email_confirm": True},
        headers={"apikey": SUPABASE_SERVICE_ROLE_KEY,
                 "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}"},
        timeout=10,
    )
    if not created.is_success:
        raise RuntimeError(f"Could not sign up: {_reason(created)}")
    return sign_in_with_password(email, password)


def refresh(session: Session) -> Session:
    """A new access token for the same session, as a real app gets one when it expires."""
    response = _auth(
        "token?grant_type=refresh_token", {"refresh_token": session.refresh_token},
        SUPABASE_ANON_KEY,
    )
    if not response.is_success:
        raise RuntimeError(f"could not refresh the session: {response.text}")
    return _session(response.json())


@dataclass
class ManiClient:
    """Every call here is exactly what a real client's chat screen would make."""

    session: Session
    base_url: str = API_BASE_URL

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.session.access_token}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        try:
            return httpx.request(
                method, f"{self.base_url}{path}", headers=self._headers(), timeout=90, **kwargs
            )
        except httpx.ConnectError as exc:
            raise RuntimeError(
                f"Could not reach the backend at {self.base_url} - is it running?"
            ) from exc

    def _call(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        response = self._request(method, path, **kwargs)
        if response.status_code == 401:
            # Supabase access tokens last an hour; a demo runs longer than that.
            self.session = refresh(self.session)
            response = self._request(method, path, **kwargs)
        if not response.is_success:
            raise ApiError(response.status_code, _error_body(response))
        return response.json() if response.content else {}

    def start_new_thread(self) -> dict[str, Any]:
        """POST /v1/threads - a fresh conversation, returned with its messages."""
        return self._call("POST", "/v1/threads", json={})

    def list_threads(self, limit: int = 20) -> list[dict[str, Any]]:
        """GET /v1/threads - the person's conversations, most recently active first."""
        return self._call("GET", "/v1/threads", params={"limit": limit})["threads"]

    def list_messages(self, thread_id: str, limit: int = 100) -> list[dict[str, Any]]:
        """A conversation's messages, oldest first (the endpoint answers newest first).
        Buttons come back live only on Mani's newest message, as in the apps."""
        page = self._call("GET", f"/v1/threads/{thread_id}/messages", params={"limit": limit})
        return list(reversed(page["messages"]))

    def set_profile(self, nickname: str) -> dict[str, Any]:
        """PUT /v1/profile - what onboarding calls, so the greeting can use their name."""
        return self._call("PUT", "/v1/profile", json={"nickname": nickname})

    def list_exercises(self) -> list[dict[str, Any]]:
        """GET /v1/exercises - the library, each item with a signed audio link."""
        body = self._call("GET", "/v1/exercises")
        return body if isinstance(body, list) else body["exercises"]

    def send_message(self, thread_id: str, content: str) -> dict[str, Any]:
        """POST /v1/threads/{id}/messages - one turn, the whole reply at once.

        The current mani backend has no client stream. This is how a ChatGPT-style
        screen still gets the real turn: wait, then show the committed reply.
        """
        return self._call(
            "POST", f"/v1/threads/{thread_id}/messages",
            json={"content": content, "client_message_id": str(uuid.uuid4())},
        )

    def stream_message(self, thread_id: str, content: str) -> Iterator[tuple[str, str]]:
        """POST /v1/threads/{id}/messages/stream, yielding (event, raw data) per SSE frame.

        A non-200 status is an ordinary API error: 401 refreshes the token and retries
        once, exactly like _call; anything else raises ApiError with the response body.
        """
        payload = {"content": content, "client_message_id": str(uuid.uuid4())}
        for attempt in (1, 2):
            try:
                with httpx.Client(base_url=self.base_url, timeout=STREAM_TIMEOUT) as http:
                    with httpx_sse.connect_sse(
                        http, "POST", f"/v1/threads/{thread_id}/messages/stream",
                        json=payload, headers=self._headers(),
                    ) as source:
                        if source.response.status_code == 401 and attempt == 1:
                            self.session = refresh(self.session)
                            continue
                        if source.response.status_code != 200:
                            source.response.read()
                            raise ApiError(
                                source.response.status_code, _error_body(source.response)
                            )
                        for sse in source.iter_sse():
                            yield sse.event, sse.data
                        return
            except httpx.ConnectError as exc:
                raise RuntimeError(
                    f"Could not reach the backend at {self.base_url} - is it running?"
                ) from exc
            except httpx.HTTPError as exc:
                raise RuntimeError(
                    f"The connection to the backend dropped mid-stream: {exc}"
                ) from exc
            except httpx_sse.SSEError as exc:
                raise RuntimeError(f"The stream was not valid SSE: {exc}") from exc
