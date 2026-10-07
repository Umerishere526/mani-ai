# ABOUTME: Checks the app boots and turns a ServiceError into its HTTP shape.
# ABOUTME: The error contract is what every frontend branches on, so it is asserted here.

import logging

import pytest
import sentry_sdk
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from mani.config import get_settings
from mani.errors import ErrorCategory, ServiceError
from main import create_app


@pytest.fixture
def client() -> TestClient:
    """A fresh app per test, so routes added below do not leak between tests."""
    return TestClient(create_app())


def test_health_reports_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_a_rejected_message_is_not_written_to_the_log(client, caplog):
    """The rejected value is what the person typed. It must not reach the log."""
    app: FastAPI = client.app
    disclosure = "I have been having thoughts about hurting myself"

    class Body(BaseModel):
        content: str = Field(max_length=10)

    @app.post("/echo")
    def echo(body: Body):  # pragma: no cover - the request never gets this far
        return {}

    with caplog.at_level(logging.WARNING):
        response = client.post("/echo", json={"content": disclosure})

    assert response.status_code == 422
    assert response.json()["error"]["category"] == "invalid_request"
    assert caplog.records, "the rejection was not logged at all"
    assert disclosure not in caplog.text
    # Still diagnostic: which field failed, and how.
    assert "string_too_long" in caplog.text
    assert "content" in caplog.text


def test_service_error_becomes_its_category_status(client):
    app: FastAPI = client.app

    @app.get("/boom")
    def boom():
        raise ServiceError(
            "provider refused the request",
            ErrorCategory.RATE_LIMITED,
            retryable=True,
            user_message="Mani is busy right now. Try again in a moment.",
        )

    response = client.get("/boom")
    assert response.status_code == 429
    assert response.json() == {
        "error": {
            "category": "rate_limited",
            "message": "Mani is busy right now. Try again in a moment.",
            "retryable": True,
        }
    }


def test_a_request_without_a_token_is_401_not_403(client):
    """A client refreshes its session on 401 and gives up on 403. Collapsing the two
    makes an expired token look like a permission failure and signs the person out."""
    response = client.get("/v1/threads")
    assert response.status_code == 401
    assert response.json()["error"]["category"] == "unauthenticated"


def test_a_browser_origin_must_be_listed_to_be_allowed(client):
    """web/ cannot call the API at all until its origin is configured."""
    allowed = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"

    other = client.get("/health", headers={"Origin": "https://not-ours.example"})
    assert "access-control-allow-origin" not in other.headers


def test_a_malformed_request_gets_the_same_error_shape(client):
    """FastAPI's default returns {"detail": [...]}, so a client branching on
    error.category falls through to its unknown-error path on every validation slip."""
    app: FastAPI = client.app

    class Body(BaseModel):
        n: int

    @app.post("/probe")
    def probe(b: Body):
        return {"ok": True}

    response = client.post("/probe", json={"n": "not-a-number"})
    assert response.status_code == 422
    assert response.json()["error"]["category"] == "invalid_request"


def test_a_validation_error_does_not_echo_the_input_back(client):
    """FastAPI's default includes the offending value, which for this service could be
    a fragment of someone's message."""
    app: FastAPI = client.app

    class Body(BaseModel):
        n: int

    @app.post("/echo")
    def echo(b: Body):
        return {"ok": True}

    response = client.post("/echo", json={"n": "i-had-a-hard-day"})
    assert "i-had-a-hard-day" not in response.text


def test_operation_ids_are_unique_and_readable(client):
    """They become the function names in the generated TypeScript client."""
    spec = client.app.openapi()
    ids = [op["operationId"] for path in spec["paths"].values() for op in path.values()]
    assert len(ids) == len(set(ids)), "duplicate operationId breaks client generation"
    assert "send" in ids and "list_threads" in ids


def test_internal_message_is_not_sent_to_the_client(client):
    app: FastAPI = client.app

    @app.get("/leak")
    def leak():
        raise ServiceError("connection string postgres://secret@host", ErrorCategory.STORAGE_ERROR)

    response = client.get("/leak")
    assert response.status_code == 500
    assert "secret" not in response.text


@pytest.fixture
def sentry_options(monkeypatch):
    """The options create_app() initialises Sentry with, given a DSN. The client and the cached
    settings are torn down afterwards so no other test runs with Sentry live."""
    monkeypatch.setenv("SENTRY_DSN", "https://key@o0.ingest.sentry.io/0")
    get_settings.cache_clear()
    create_app()
    try:
        yield sentry_sdk.get_client().options
    finally:
        sentry_sdk.get_client().close()
        sentry_sdk.get_global_scope().set_client(None)
        get_settings.cache_clear()


def test_sentry_collects_no_request_body_and_no_local_variables(sentry_options):
    """sentry-sdk attaches JSON bodies and frame locals by default. Here either one is the
    person's message."""
    assert sentry_options["send_default_pii"] is False
    assert sentry_options["max_request_body_size"] == "never"
    assert sentry_options["include_local_variables"] is False


def test_an_error_report_is_scrubbed_of_content_before_it_is_sent(sentry_options):
    disclosure = "I have been having thoughts about hurting myself"
    event = {
        "request": {"url": "http://testserver/v1/threads/x/messages", "data": {"content": disclosure}},
        "exception": {"values": [{
            "type": "ServiceError",
            "stacktrace": {"frames": [{"function": "send", "vars": {"content": disclosure}}]},
        }]},
        "breadcrumbs": {"values": [{"category": "mani", "message": f"noted: {disclosure}"}]},
    }

    sent = sentry_options["before_send"](event, {})

    assert disclosure not in str(sent)
    # Still diagnostic: where it failed, and what failed.
    assert sent["request"]["url"].endswith("/messages")
    assert sent["exception"]["values"][0]["stacktrace"]["frames"][0]["function"] == "send"
