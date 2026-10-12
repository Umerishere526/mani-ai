# ABOUTME: Calls Supabase's Auth Admin API - the only place this backend manages auth.users.
# ABOUTME: The one thing GoTrue will not do for a user's own session: delete their account.

from __future__ import annotations

import httpx

from mani import supabase_http
from mani.config import get_settings
from mani.errors import ErrorCategory, ServiceError


async def delete_user(user_id: str) -> None:
    """Deletes the auth.users row. Every user table cascades from it, so this is the
    entire account teardown - there is nothing left for this backend to clean up.

    Unlike storage.signed_audio_url, this must never degrade silently: a failure here
    means the account still exists, so it raises rather than swallowing the error.
    """
    settings = get_settings()
    try:
        response = await supabase_http.client().delete(
            f"{supabase_http.base_url(settings)}/auth/v1/admin/users/{user_id}",
            headers=supabase_http.service_headers(settings),
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ServiceError(
            f"failed to delete auth user {user_id}: {exc}",
            ErrorCategory.AUTH_PROVIDER_ERROR,
            retryable=True,
            user_message="We couldn't delete your account. Please try again.",
        ) from exc
