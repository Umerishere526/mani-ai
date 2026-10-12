# ABOUTME: The one HTTP client this backend uses to call Supabase's own APIs, with the headers they need.
# ABOUTME: Shared by Auth Admin and Storage, so neither opens a client of its own.

from __future__ import annotations

import httpx

from mani.config import Settings

_client: httpx.AsyncClient | None = None


def client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=10.0)
    return _client


async def close() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def base_url(settings: Settings) -> str:
    return settings.supabase_url.rstrip("/")


def service_headers(settings: Settings) -> dict[str, str]:
    """The service role key, sent as both headers Supabase's APIs read it from."""
    return {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "apikey": settings.supabase_service_role_key,
    }
