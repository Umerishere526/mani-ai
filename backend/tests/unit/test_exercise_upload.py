# ABOUTME: Checks the portal's exercise upload link: an admin gets a fresh MP3 path and an absolute signed upload URL,
# ABOUTME: a name that is not an MP3 is refused, and a storage refusal is an error the admin sees, never a dead link.

import logging

import httpx
import pytest
from fastapi.testclient import TestClient

from main import create_app
from mani import storage
from mani.auth.deps import require_admin
from mani.auth.jwt import Claims
from mani.config import Settings

ADMIN = Claims(sub="a0000000-0000-4000-8000-0000000000a1", raw={"sub": "a0000000-0000-4000-8000-0000000000a1"})


@pytest.fixture
def storage_api(monkeypatch):
    """The Storage API's upload signing, answering as the local storage-api does; each request is recorded."""
    requests: list[httpx.Request] = []
    answer = {"status": 200}

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if answer["status"] != 200:
            return httpx.Response(answer["status"], json={"message": "Bucket not found"})
        path = request.url.path.removeprefix("/storage/v1")
        return httpx.Response(200, json={"url": f"{path}?token=t", "token": "t"})

    monkeypatch.setattr(storage, "get_settings", lambda: Settings(
        _env_file=None, database_url="postgresql://postgres:postgres@127.0.0.1:5432/postgres",
        supabase_url="http://storage.test", supabase_service_role_key="sb_secret_example",
    ))
    monkeypatch.setattr(storage, "_client", httpx.AsyncClient(transport=httpx.MockTransport(handle)))
    return requests, answer


@pytest.fixture
def portal() -> TestClient:
    app = create_app()
    app.dependency_overrides[require_admin] = lambda: ADMIN
    return TestClient(app)


def test_an_admin_gets_a_fresh_mp3_path_and_its_absolute_upload_link(portal, storage_api):
    requests, _ = storage_api

    body = portal.post(
        "/v1/admin/exercises/upload-url", json={"filename": "The Gardener's Shed.MP3", "content_type": "audio/mpeg"}
    ).json()

    assert body["path"].startswith("the-gardener-s-shed-") and body["path"].endswith(".mp3")
    assert body["upload_url"] == f"http://storage.test/storage/v1/object/upload/sign/exercises/{body['path']}?token=t"
    assert [(r.method, r.headers["apikey"]) for r in requests] == [("POST", "sb_secret_example")]


def test_two_uploads_of_one_name_never_share_a_path(storage_api):
    assert storage.audio_path_for("calm.mp3") != storage.audio_path_for("calm.mp3")


@pytest.mark.parametrize("body", [
    {"filename": "notes.wav", "content_type": "audio/mpeg"},
    {"filename": "!!!.mp3", "content_type": "audio/mpeg"},
    {"filename": "calm.mp3", "content_type": "audio/wav"},
])
def test_anything_but_an_mp3_is_refused_before_storage_is_asked(portal, storage_api, body):
    requests, _ = storage_api

    response = portal.post("/v1/admin/exercises/upload-url", json=body)

    assert response.status_code == 422 and requests == []


def test_a_storage_refusal_is_an_error_the_admin_can_retry(portal, storage_api, caplog):
    requests, answer = storage_api
    answer["status"] = 400

    with caplog.at_level(logging.ERROR, logger="main"):
        response = portal.post(
            "/v1/admin/exercises/upload-url", json={"filename": "calm.mp3", "content_type": "audio/mpeg"}
        )

    assert (response.status_code, response.json()["error"]["retryable"]) == (500, True)
    assert len(requests) == 1
    assert [r.getMessage().split(":")[0] for r in caplog.records] == ["storage_error"]
