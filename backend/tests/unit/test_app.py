# ABOUTME: Checks the app boots and turns a ServiceError into its HTTP shape.
# ABOUTME: The error contract is what every frontend branches on, so it is asserted here.

import logging

import asyncpg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from main import create_app
from mani.errors import ErrorCategory, ServiceError


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


@pytest.mark.parametrize(
    ("constraint", "status"),
    [("threads_user_id_fkey", 401), ("messages_thread_id_fkey", 500)],
)
def test_only_a_write_for_an_account_that_is_gone_is_told_to_sign_in(constraint, status):
    """A missing account is the person's to fix by signing in again. Any other missing row is a
    fault of ours, and must not be passed off to them as an expired session."""
    app = create_app()

    @app.post("/write")
    def write():
        raise asyncpg.ForeignKeyViolationError.new({"C": "23503", "M": "violates", "n": constraint})

    response = TestClient(app, raise_server_exceptions=False).post("/write")
    assert response.status_code == status


def test_internal_message_is_not_sent_to_the_client(client):
    app: FastAPI = client.app

    @app.get("/leak")
    def leak():
        raise ServiceError("connection string postgres://secret@host", ErrorCategory.STORAGE_ERROR)

    response = client.get("/leak")
    assert response.status_code == 500
    assert "secret" not in response.text


def test_an_unhandled_exception_still_gets_the_shaped_error(client):
    """FastAPI's default for anything that isn't caught is `{"detail": "Internal Server
    Error"}` - a shape no client here branches on."""
    app: FastAPI = client.app

    @app.get("/crash")
    def crash():
        raise ValueError("boom, not a ServiceError")

    response = TestClient(app, raise_server_exceptions=False).get("/crash")
    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "category": "unknown",
            "message": "Something went wrong on our end. Please try again.",
            "retryable": True,
        }
    }


def test_a_service_error_is_not_caught_by_the_catch_all(client):
    """The catch-all is registered last; FastAPI must still dispatch to the more
    specific ServiceError handler first."""
    app: FastAPI = client.app

    @app.get("/boom")
    def boom():
        raise ServiceError("provider refused the request", ErrorCategory.RATE_LIMITED)

    response = client.get("/boom")
    assert response.json()["error"]["category"] == "rate_limited"


def test_a_validation_error_is_not_caught_by_the_catch_all(client):
    app: FastAPI = client.app

    class Body(BaseModel):
        n: int

    @app.post("/probe2")
    def probe2(b: Body):
        return {"ok": True}

    response = client.post("/probe2", json={"n": "not-a-number"})
    assert response.json()["error"]["category"] == "invalid_request"


def test_a_foreign_key_violation_is_not_caught_by_the_catch_all():
    app = create_app()

    @app.post("/write2")
    def write2():
        raise asyncpg.ForeignKeyViolationError.new(
            {"C": "23503", "M": "violates", "n": "threads_user_id_fkey"}
        )

    response = TestClient(app, raise_server_exceptions=False).post("/write2")
    assert response.json()["error"]["category"] == "unauthenticated"
