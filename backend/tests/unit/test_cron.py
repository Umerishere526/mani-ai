# ABOUTME: The cron endpoints are guarded by a shared secret header, never a JWT.
# ABOUTME: Confirms the guard actually runs on the wire, not just in a unit of the function.

import pytest
from fastapi.testclient import TestClient

from main import create_app
from mani.config import get_settings

PATH = "/internal/cron/catch-up"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_no_secret_configured_refuses_every_request(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "cron_secret", "")
    response = client.get(PATH)
    assert response.status_code == 401


def test_the_wrong_secret_is_refused(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "cron_secret", "the-real-one")
    response = client.get(PATH, headers={"Authorization": "Bearer guess"})
    assert response.status_code == 401


def test_the_right_secret_runs_the_catch_up(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "cron_secret", "the-real-one")
    monkeypatch.setattr(
        "mani.routers.cron.catch_up.run", lambda: _immediate({"summaries": 1, "follow_ups": 2, "folded": 3})
    )
    response = client.get(PATH, headers={"Authorization": "Bearer the-real-one"})
    assert response.status_code == 200
    assert response.json() == {"summaries": 1, "follow_ups": 2, "folded": 3}


async def _immediate(value):
    return value
