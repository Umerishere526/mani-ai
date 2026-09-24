# ABOUTME: Calls Supabase's Auth Admin API - the only place this backend manages auth.users.
# ABOUTME: The one thing GoTrue will not do for a user's own session: delete their account.

from __future__ import annotations

import httpx

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


async def delete_user(user_id: str) -> None:
    """Deletes the auth.users row. Every user table cascades from it, so this is the
    entire account teardown - there is nothing left for this backend to clean up.

    Unlike storage.signed_audio_url, this must never degrade silently: a failure here
    means the account still exists, so it raises rather than swallowing the error.
    """
    settings = get_settings()
    base = settings.supabase_url.rstrip("/")
    try:
        response = await _http().delete(
            f"{base}/auth/v1/admin/users/{user_id}",
            headers={
                "Authorization": f"Bearer {settings.supabase_service_role_key}",
                "apikey": settings.supabase_service_role_key,
            },
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ServiceError(
            f"failed to delete auth user {user_id}: {exc}",
            ErrorCategory.AUTH_PROVIDER_ERROR,
            retryable=True,
            user_message="We couldn't delete your account. Please try again.",
        ) from exc
