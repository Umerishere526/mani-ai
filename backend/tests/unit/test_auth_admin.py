# ABOUTME: Checks delete_user()'s own logic - the request it sends and what it raises.
# ABOUTME: The HTTP client is faked; nothing here needs a database or a network call.

from __future__ import annotations

import httpx
import pytest

from mani import auth_admin
from mani.config import Settings
from mani.errors import ErrorCategory, ServiceError


def settings() -> Settings:
    return Settings(
        database_url="postgresql://localhost/none",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role-key",
        supabase_jwt_secret="secret",
    )


class FakeResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"status {self.status_code}", request=None, response=self  # type: ignore[arg-type]
            )


class FakeClient:
    """Stands in for httpx.AsyncClient - records the call, returns a scripted response."""

    def __init__(self, response: FakeResponse | Exception) -> None:
        self._response = response
        self.calls: list[dict] = []

    async def delete(self, url: str, *, headers: dict) -> FakeResponse:
        self.calls.append({"url": url, "headers": headers})
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


def install(monkeypatch, fake: FakeClient) -> None:
    monkeypatch.setattr(auth_admin, "_http", lambda: fake)
    monkeypatch.setattr(auth_admin, "get_settings", settings)


async def test_delete_user_sends_the_service_role_key_as_both_headers(monkeypatch):
    fake = FakeClient(FakeResponse(204))
    install(monkeypatch, fake)

    await auth_admin.delete_user("a0000000-0000-4000-8000-00000000000a")

    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["url"] == (
        "https://example.supabase.co/auth/v1/admin/users/"
        "a0000000-0000-4000-8000-00000000000a"
    )
    assert call["headers"]["Authorization"] == "Bearer service-role-key"
    assert call["headers"]["apikey"] == "service-role-key"


async def test_a_failed_delete_raises_rather_than_leaving_the_account_in_place(monkeypatch):
    """Unlike storage.signed_audio_url, this must never degrade silently - a failure here
    means the account still exists."""
    install(monkeypatch, FakeClient(FakeResponse(404)))

    with pytest.raises(ServiceError) as exc_info:
        await auth_admin.delete_user("a0000000-0000-4000-8000-00000000000a")
    assert exc_info.value.category == ErrorCategory.AUTH_PROVIDER_ERROR
    assert exc_info.value.retryable is True


async def test_a_connection_failure_raises_the_same_way(monkeypatch):
    install(monkeypatch, FakeClient(httpx.ConnectError("no route to host")))

    with pytest.raises(ServiceError) as exc_info:
        await auth_admin.delete_user("a0000000-0000-4000-8000-00000000000a")
    assert exc_info.value.category == ErrorCategory.AUTH_PROVIDER_ERROR
