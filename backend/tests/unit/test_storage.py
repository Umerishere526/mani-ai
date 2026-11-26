# ABOUTME: Checks the library's audio links are signed in one request, and that a link which cannot be signed
# ABOUTME: degrades to "no link" for that file, or for all of them, rather than taking the library page down.

import json
import logging

import httpx

from mani import storage
from mani.config import Settings


def _settings(url: str = "http://storage.test") -> Settings:
    return Settings(
        _env_file=None,
        database_url="postgresql://postgres:postgres@127.0.0.1:5432/postgres",
        supabase_url=url,
        supabase_service_role_key="sb_secret_example",
    )


async def test_every_path_is_signed_in_one_request_and_an_unsigned_one_is_left_out(monkeypatch, caplog):
    requests = []

    def storage_api(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=[
            {"error": None, "path": "bee.mp3", "signedURL": "/object/sign/exercises/bee.mp3?token=t1"},
            {"error": "Either the object does not exist", "path": "gone.mp3", "signedURL": None},
        ])

    monkeypatch.setattr(storage, "get_settings", _settings)
    monkeypatch.setattr(storage, "_client", httpx.AsyncClient(transport=httpx.MockTransport(storage_api)))

    with caplog.at_level(logging.WARNING, logger="mani.storage"):
        links = await storage.signed_audio_urls(["bee.mp3", "gone.mp3"])
    await storage.close()

    assert links == {"bee.mp3": "http://storage.test/storage/v1/object/sign/exercises/bee.mp3?token=t1"}
    assert len(requests) == 1 and str(requests[0].url) == "http://storage.test/storage/v1/object/sign/exercises"
    assert json.loads(requests[0].content)["paths"] == ["bee.mp3", "gone.mp3"]
    assert [r.getMessage() for r in caplog.records] == [
        "storage path gone.mp3 was not signed: Either the object does not exist"
    ]


async def test_a_malformed_storage_url_signs_nothing_instead_of_raising(monkeypatch, caplog):
    """A control character inside the configured URL survives trimming; httpx refuses to
    build that request. The catalog must still be served, with its links missing."""
    monkeypatch.setattr(storage, "get_settings", lambda: _settings("https://heqenombgkihfeggrxqc\x07.supabase.co"))

    with caplog.at_level(logging.ERROR, logger="mani.storage"):
        assert await storage.signed_audio_urls(["home-ground.mp3"]) == {}
    await storage.close()

    assert [r.getMessage() for r in caplog.records] == ["failed to sign 1 storage paths"]
