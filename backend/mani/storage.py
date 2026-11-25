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


async def signed_audio_urls(paths: list[str]) -> dict[str, str]:
    """Time-limited links to many audio files, signed in one request, keyed by path.

    A path that cannot be signed is absent, and a failed request signs nothing: a missing link degrades
    that exercise to its text, which is worth serving; it is not worth failing the whole catalog over.
    """
    if not paths:
        return {}

    settings = get_settings()
    base = settings.supabase_url.rstrip("/")
    try:
        response = await _http().post(
            f"{base}/storage/v1/object/sign/{BUCKET}",
            json={"expiresIn": SIGNED_URL_TTL_SECONDS, "paths": [path.lstrip("/") for path in paths]},
            headers={
                "Authorization": f"Bearer {settings.supabase_service_role_key}",
                "apikey": settings.supabase_service_role_key,
            },
        )
        response.raise_for_status()
        signed = response.json()
    except (httpx.HTTPError, httpx.InvalidURL, ValueError):
        logger.exception("failed to sign %d storage paths", len(paths))
        return {}

    links = {}
    for item in signed:
        url = item.get("signedURL")
        if not url:
            logger.warning("storage path %s was not signed: %s", item.get("path"), item.get("error"))
            continue
        links[item["path"]] = f"{base}/storage/v1{url}" if url.startswith("/") else url
    return links
