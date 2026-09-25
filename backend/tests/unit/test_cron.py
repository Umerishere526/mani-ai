# ABOUTME: The cron endpoints are guarded by a shared secret header, never a JWT.
# ABOUTME: Confirms the guard actually runs on the wire, not just in a unit of the function.

import pytest
from fastapi.testclient import TestClient

from main import create_app
from mani.config import get_settings


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_no_secret_configured_refuses_every_request(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "cron_secret", "")
    response = client.get("/internal/cron/fold-summaries")
    assert response.status_code == 401


def test_the_wrong_secret_is_refused(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "cron_secret", "the-real-one")
    response = client.get(
        "/internal/cron/fold-summaries", headers={"Authorization": "Bearer guess"}
    )
    assert response.status_code == 401


def test_the_right_secret_is_accepted(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "cron_secret", "the-real-one")
    monkeypatch.setattr(
        "mani.routers.cron.reconcile_due", lambda: _immediate(0)
    )
    response = client.get(
        "/internal/cron/fold-summaries",
        headers={"Authorization": "Bearer the-real-one"},
    )
    assert response.status_code == 200
    assert response.json() == {"processed": 0}


async def _immediate(value):
    return value
