# ABOUTME: Calls Supabase's Auth Admin API - the only place this backend manages auth.users.
# ABOUTME: What GoTrue will not do for a user's own session: delete their account, or make them an admin.

from __future__ import annotations

import httpx

from mani.auth.jwt import ADMIN_ROLE
from mani.config import get_settings
from mani.errors import ErrorCategory, ServiceError

_client: httpx.AsyncClient | None = None


def _http() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=10.0)
    return _client


async def close() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def _service_headers() -> dict[str, str]:
    key = get_settings().supabase_service_role_key
    return {"Authorization": f"Bearer {key}", "apikey": key}


def _user_url(user_id: str) -> str:
    return f"{get_settings().supabase_url.rstrip('/')}/auth/v1/admin/users/{user_id}"


async def set_admin(user_id: str, granted: bool) -> None:
    """Grants or removes the admin claim. It lives in app_metadata, which only the service role
    can write, and reaches the person's token when they next sign in or refresh."""
    try:
        response = await _http().put(
            _user_url(user_id),
            json={"app_metadata": {"admin_role": ADMIN_ROLE if granted else None}},
            headers=_service_headers(),
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ServiceError(
            f"failed to set admin={granted} on auth user {user_id}: {exc}",
            ErrorCategory.AUTH_PROVIDER_ERROR,
            retryable=True,
        ) from exc


async def delete_user(user_id: str) -> None:
    """Deletes the auth.users row. Every user table cascades from it, so this is the
    entire account teardown - there is nothing left for this backend to clean up.

    Unlike storage.signed_audio_url, this must never degrade silently: a failure here
    means the account still exists, so it raises rather than swallowing the error.
    """
    try:
        response = await _http().delete(_user_url(user_id), headers=_service_headers())
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ServiceError(
            f"failed to delete auth user {user_id}: {exc}",
            ErrorCategory.AUTH_PROVIDER_ERROR,
            retryable=True,
            user_message="We couldn't delete your account. Please try again.",
        ) from exc
