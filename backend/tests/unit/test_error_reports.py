# ABOUTME: An error report sent to Sentry carries neither the request body nor a frame's variables.
# ABOUTME: A chat turn's body is the person's message, which must not leave the process.

import sentry_sdk
from fastapi.testclient import TestClient
from sentry_sdk.transport import Transport

from main import create_app
from mani.config import get_settings

SAID = "my manager keeps changing the deadline"


class Captured(Transport):
    """Keeps what would have been sent to Sentry instead of sending it."""

    def __init__(self) -> None:
        super().__init__()
        self.sent: list[bytes] = []

    def capture_envelope(self, envelope) -> None:
        self.sent.append(envelope.serialize())


def test_an_error_during_a_request_reports_nothing_the_person_said(monkeypatch):
    monkeypatch.setattr(get_settings(), "sentry_dsn", "https://public@o0.ingest.sentry.io/0")
    app = create_app()
    captured = Captured()
    sentry_sdk.get_client().transport = captured

    @app.post("/fails-mid-request")
    async def fails(body: dict) -> None:
        content = body["content"]
        raise RuntimeError(f"failed after reading {len(content)} characters")

    try:
        TestClient(app, raise_server_exceptions=False).post("/fails-mid-request", json={"content": SAID})
        sentry_sdk.flush()
    finally:
        sentry_sdk.init()

    assert captured.sent, "the error was not reported at all"
    assert not any(SAID.encode() in envelope for envelope in captured.sent)
