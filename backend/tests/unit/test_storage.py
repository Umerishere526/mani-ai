# ABOUTME: Checks signing exercise audio links degrades to "no link" rather than failing.
# ABOUTME: A link that cannot be signed must never take the whole library page down.

from mani import storage
from mani.config import Settings


async def test_a_malformed_storage_url_signs_nothing_instead_of_raising(monkeypatch):
    """A control character inside the configured URL survives trimming; httpx refuses to
    build that request. The catalog must still be served, with this one link missing."""
    broken = Settings(
        _env_file=None,
        database_url="postgresql://postgres:postgres@127.0.0.1:5432/postgres",
        supabase_url="https://heqenombgkihfeggrxqc\x07.supabase.co",
        supabase_service_role_key="sb_secret_example",
    )
    monkeypatch.setattr(storage, "get_settings", lambda: broken)

    assert await storage.signed_audio_url("home-ground.mp3") is None
    await storage.close()
