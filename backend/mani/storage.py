# ABOUTME: Signs Supabase Storage URLs for exercise audio, from the backend only.
# ABOUTME: The bucket stays private; a signed link is the only way a file is reachable.

from __future__ import annotations

import logging

import httpx

from mani.config import get_settings

logger = logging.getLogger(__name__)

BUCKET = "exercises"
SIGNED_URL_TTL_SECONDS = 3600

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


async def signed_audio_url(path: str | None) -> str | None:
    """A time-limited link to one audio file, or None if it cannot be signed.

    A missing link degrades the exercise to its text, which is worth serving; it is not
    worth failing the whole catalog over.
    """
    if not path:
        return None

    settings = get_settings()
    base = settings.supabase_url.rstrip("/")
    try:
        response = await _http().post(
            f"{base}/storage/v1/object/sign/{BUCKET}/{path.lstrip('/')}",
            json={"expiresIn": SIGNED_URL_TTL_SECONDS},
            headers={
                "Authorization": f"Bearer {settings.supabase_service_role_key}",
                "apikey": settings.supabase_service_role_key,
            },
        )
        response.raise_for_status()
        signed = response.json().get("signedURL")
    except (httpx.HTTPError, ValueError):
        logger.exception("failed to sign storage path %s", path)
        return None

    if not signed:
        return None
    return f"{base}/storage/v1{signed}" if signed.startswith("/") else signed
