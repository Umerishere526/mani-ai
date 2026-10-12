# ABOUTME: Signs Supabase Storage URLs for exercise audio, from the backend only.
# ABOUTME: The bucket stays private; a signed link is the only way a file is reachable.

from __future__ import annotations

import logging

import httpx

from mani import supabase_http
from mani.config import get_settings

logger = logging.getLogger(__name__)

BUCKET = "exercises"
SIGNED_URL_TTL_SECONDS = 3600

async def signed_audio_url(path: str | None) -> str | None:
    """A time-limited link to one audio file, or None if it cannot be signed.

    A missing link degrades the exercise to its text, which is worth serving; it is not
    worth failing the whole catalog over.
    """
    if not path:
        return None

    settings = get_settings()
    base = supabase_http.base_url(settings)
    try:
        response = await supabase_http.client().post(
            f"{base}/storage/v1/object/sign/{BUCKET}/{path.lstrip('/')}",
            json={"expiresIn": SIGNED_URL_TTL_SECONDS},
            headers=supabase_http.service_headers(settings),
        )
        response.raise_for_status()
        signed = response.json().get("signedURL")
    except (httpx.HTTPError, httpx.InvalidURL, ValueError):
        logger.exception("failed to sign storage path %s", path)
        return None

    if not signed:
        return None
    return f"{base}/storage/v1{signed}" if signed.startswith("/") else signed
