# ABOUTME: Checks complete()'s own logic - the schema retry and what gets recorded.
# ABOUTME: The provider call is faked; nothing here needs a database or a network call.

from __future__ import annotations

import uuid

import pytest

from mani.config import Settings
from mani.db import llm_calls
from mani.errors import ServiceError
from mani.llm import client
from mani.llm.schema import Reply


def settings() -> Settings:
    return Settings(
        database_url="postgresql://localhost/none",
        supabase_url="https://example.supabase.co",
        supabase_jwt_secret="secret",
        openrouter_api_key="sk-test-not-a-real-key",
    )


class FakeRunnable:
    """Stands in for chain.build()'s Runnable - one scripted result per ainvoke() call."""

    def __init__(self, *results: dict) -> None:
        self._results = list(results)
        self.calls = 0

    async def ainvoke(self, messages: list[dict]) -> dict:
        self.calls += 1
        return self._results[min(self.calls - 1, len(self._results) - 1)]


def valid(text: str = "hi") -> dict:
    return {"raw": None, "parsed": Reply(text=text), "parsing_error": None}


def invalid(error: str = "bad json") -> dict:
    return {"raw": None, "parsed": None, "parsing_error": error}


@pytest.fixture
def recorded(monkeypatch):
    """Every call `complete()` makes to _record, without touching a database."""
    calls: list[dict] = []

    async def fake_record(**kwargs) -> uuid.UUID:
        calls.append(kwargs)
        return uuid.uuid4()

    monkeypatch.setattr(client, "_record", fake_record)
    return calls


def install(monkeypatch, runnable) -> None:
    monkeypatch.setattr(client.chain, "build", lambda *a, **kw: runnable)


async def test_a_valid_first_reply_needs_no_retry(monkeypatch, recorded):
    runnable = FakeRunnable(valid())
    install(monkeypatch, runnable)

    call = await client.complete(
        [], Reply, model="m", purpose=llm_calls.Purpose.CHAT, settings=settings()
    )

    assert runnable.calls == 1
    assert call.value.text == "hi"
    assert [c["outcome"] for c in recorded] == [llm_calls.Outcome.OK]


async def test_one_schema_failure_is_retried_and_both_attempts_are_recorded(
    monkeypatch, recorded
):
    """A malformed reply otherwise loses the person's message - complete() is called
    before anything is written, so the retry has to happen here, not one layer up."""
    runnable = FakeRunnable(invalid(), valid("recovered"))
    install(monkeypatch, runnable)

    call = await client.complete(
        [], Reply, model="m", purpose=llm_calls.Purpose.CHAT, settings=settings()
    )

    assert runnable.calls == 2
    assert call.value.text == "recovered"
    assert [c["outcome"] for c in recorded] == [
        llm_calls.Outcome.SCHEMA_INVALID,
        llm_calls.Outcome.OK,
    ]


async def test_two_schema_failures_raise_and_record_both_attempts(monkeypatch, recorded):
    runnable = FakeRunnable(invalid("first"), invalid("second"))
    install(monkeypatch, runnable)

    with pytest.raises(ServiceError):
        await client.complete(
            [], Reply, model="m", purpose=llm_calls.Purpose.CHAT, settings=settings()
        )

    assert runnable.calls == client.MAX_SCHEMA_ATTEMPTS == 2
    assert [c["outcome"] for c in recorded] == [
        llm_calls.Outcome.SCHEMA_INVALID,
        llm_calls.Outcome.SCHEMA_INVALID,
    ]


async def test_a_provider_error_is_not_retried_by_the_schema_loop(monkeypatch, recorded):
    """The retry is scoped to a schema failure - anything else must still surface on the
    first attempt, exactly as it did before this loop existed."""

    class Boom(FakeRunnable):
        async def ainvoke(self, messages: list[dict]) -> dict:
            self.calls += 1
            raise RuntimeError("provider unreachable")

    runnable = Boom()
    install(monkeypatch, runnable)

    with pytest.raises(ServiceError):
        await client.complete(
            [], Reply, model="m", purpose=llm_calls.Purpose.CHAT, settings=settings()
        )

    assert runnable.calls == 1
    assert [c["outcome"] for c in recorded] == [llm_calls.Outcome.PROVIDER_ERROR]
