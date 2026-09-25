# ABOUTME: Checks complete()'s own logic - the schema retry and what gets recorded.
# ABOUTME: The provider call is faked; nothing here needs a database or a network call.

from __future__ import annotations

import uuid
from types import SimpleNamespace

import openai
import pytest
from openai.types import CompletionUsage
from openai.types.chat import ChatCompletion

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
        result = self._results[min(self.calls - 1, len(self._results) - 1)]
        if isinstance(result, BaseException):
            raise result
        return result


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


class FakeToolMessage:
    """What a bind_tools() runnable hands back - an AIMessage with tool_calls on it."""

    def __init__(self, *, exercise_id: str | None) -> None:
        self.tool_calls = (
            [{"name": "StartExercise", "args": {"exercise_id": exercise_id}, "id": "1"}]
            if exercise_id is not None
            else []
        )
        self.usage_metadata = {"input_tokens": 40, "output_tokens": 8}
        self.response_metadata: dict = {}


class FakeToolRunnable:
    def __init__(self, message: FakeToolMessage) -> None:
        self._message = message
        self.calls = 0

    async def ainvoke(self, messages: list[dict]) -> FakeToolMessage:
        self.calls += 1
        return self._message


CANDIDATES = [
    {"id": "11111111-1111-4111-8111-111111111111", "title": "One", "subtitle": ""},
    {"id": "22222222-2222-4222-8222-222222222222", "title": "Two", "subtitle": ""},
]


async def test_the_chosen_exercise_is_the_one_the_tool_call_named(monkeypatch, recorded):
    runnable = FakeToolRunnable(FakeToolMessage(exercise_id=CANDIDATES[1]["id"]))
    monkeypatch.setattr(client.chain, "build_tool_choice", lambda *a, **kw: runnable)

    chosen = await client.choose_exercise(
        CANDIDATES, "ABCDE", model="m",
        purpose=llm_calls.Purpose.EXERCISE_SELECT, settings=settings(),
    )

    assert chosen == CANDIDATES[1]["id"]
    assert [c["outcome"] for c in recorded] == [llm_calls.Outcome.OK]


async def test_an_invented_exercise_id_is_corrected_not_trusted(monkeypatch, recorded):
    """A model-supplied identifier is checked against the closed list it was given, the
    same rule repairs.py already applies to a technique id. It corrects; it never fails."""
    runnable = FakeToolRunnable(FakeToolMessage(exercise_id="not-in-the-catalogue"))
    monkeypatch.setattr(client.chain, "build_tool_choice", lambda *a, **kw: runnable)

    chosen = await client.choose_exercise(
        CANDIDATES, "ABCDE", model="m",
        purpose=llm_calls.Purpose.EXERCISE_SELECT, settings=settings(),
    )

    assert chosen == CANDIDATES[0]["id"]


async def test_no_tool_call_offers_no_exercise(monkeypatch, recorded):
    runnable = FakeToolRunnable(FakeToolMessage(exercise_id=None))
    monkeypatch.setattr(client.chain, "build_tool_choice", lambda *a, **kw: runnable)

    chosen = await client.choose_exercise(
        CANDIDATES, "ABCDE", model="m",
        purpose=llm_calls.Purpose.EXERCISE_SELECT, settings=settings(),
    )

    assert chosen is None
    assert [c["outcome"] for c in recorded] == [llm_calls.Outcome.SCHEMA_INVALID]


async def test_an_empty_candidate_list_costs_no_call_at_all(monkeypatch, recorded):
    """The production case today: the catalog has nothing for this framework, so the
    second call never happens and the turn stays at exactly one."""

    def explode(*a, **kw):
        raise AssertionError("no runnable should be built with nothing to choose from")

    monkeypatch.setattr(client.chain, "build_tool_choice", explode)

    chosen = await client.choose_exercise(
        [], "ABCDE", model="m",
        purpose=llm_calls.Purpose.EXERCISE_SELECT, settings=settings(),
    )

    assert chosen is None
    assert recorded == []


async def test_a_failed_selection_call_costs_the_offer_not_the_turn(monkeypatch, recorded):
    class Boom(FakeToolRunnable):
        async def ainvoke(self, messages: list[dict]):
            self.calls += 1
            raise RuntimeError("provider unreachable")

    runnable = Boom(FakeToolMessage(exercise_id=None))
    monkeypatch.setattr(client.chain, "build_tool_choice", lambda *a, **kw: runnable)

    chosen = await client.choose_exercise(
        CANDIDATES, "ABCDE", model="m",
        purpose=llm_calls.Purpose.EXERCISE_SELECT, settings=settings(),
    )

    assert chosen is None
    assert [c["outcome"] for c in recorded] == [llm_calls.Outcome.PROVIDER_ERROR]


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


def cut_off(output_tokens: int = 2048) -> openai.LengthFinishReasonError:
    """What the SDK raises from inside the model step when the reply hits max_tokens.

    Raised, not returned: with a response_format LangChain calls the SDK's parse(), which
    validates before LangChain's own parser ever sees the reply, so parsing_error stays
    empty and the failure arrives as an exception.
    """
    return openai.LengthFinishReasonError(
        completion=ChatCompletion(
            id="x", choices=[], created=0, model="m", object="chat.completion",
            usage=CompletionUsage(
                prompt_tokens=100, completion_tokens=output_tokens,
                total_tokens=100 + output_tokens,
            ),
        )
    )


async def test_a_reply_cut_off_by_the_token_limit_is_retried(monkeypatch, recorded):
    runnable = FakeRunnable(cut_off(), valid("second try"))
    install(monkeypatch, runnable)

    call = await client.complete(
        [{"role": "user", "content": "hi"}], Reply, model="m",
        purpose=llm_calls.Purpose.CHAT, settings=settings(),
    )

    assert call.value.text == "second try"
    assert runnable.calls == 2
    failed = recorded[0]
    assert failed["outcome"] is llm_calls.Outcome.SCHEMA_INVALID
    # The cut-off attempt was generated and billed in full; recording 0 would hide it.
    assert failed["usage"].output_tokens == 2048


async def test_a_failed_second_attempt_does_not_repeat_the_first_attempts_tokens(
    monkeypatch, recorded
):
    billed = SimpleNamespace(usage_metadata={"input_tokens": 100, "output_tokens": 20})
    install(monkeypatch, FakeRunnable(
        {"raw": billed, "parsed": None, "parsing_error": "bad json"},
        RuntimeError("connection reset"),
    ))

    with pytest.raises(ServiceError):
        await client.complete(
            [{"role": "user", "content": "hi"}], Reply, model="m",
            purpose=llm_calls.Purpose.CHAT, settings=settings(),
        )

    assert recorded[-1]["outcome"] is llm_calls.Outcome.PROVIDER_ERROR
    assert recorded[-1]["usage"] == llm_calls.Usage()


def provider_down(status: int = 503) -> openai.InternalServerError:
    """What the SDK raises when the upstream provider answers 5xx - seen live from Google AI
    Studio ("The service is currently unavailable") once in 265 calls."""
    import httpx

    request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
    return openai.InternalServerError(
        "Provider returned error", response=httpx.Response(status, request=request), body=None
    )


async def test_a_provider_blip_is_retried_once(monkeypatch, recorded):
    runnable = FakeRunnable(provider_down(), valid("answered on the retry"))
    install(monkeypatch, runnable)
    monkeypatch.setattr(client, "TRANSIENT_RETRY_DELAY_SECONDS", 0)

    call = await client.complete(
        [{"role": "user", "content": "hi"}], Reply, model="m",
        purpose=llm_calls.Purpose.CHAT, settings=settings(),
    )

    assert call.value.text == "answered on the retry"
    assert runnable.calls == 2
    assert recorded[0]["outcome"] is llm_calls.Outcome.PROVIDER_ERROR


async def test_a_provider_down_twice_fails_the_turn(monkeypatch, recorded):
    install(monkeypatch, FakeRunnable(provider_down(), provider_down()))
    monkeypatch.setattr(client, "TRANSIENT_RETRY_DELAY_SECONDS", 0)

    with pytest.raises(ServiceError) as failed:
        await client.complete(
            [{"role": "user", "content": "hi"}], Reply, model="m",
            purpose=llm_calls.Purpose.CHAT, settings=settings(),
        )
    assert failed.value.retryable


async def test_a_timeout_is_not_retried(monkeypatch, recorded):
    """A timeout already cost the full wait; a retry would make the person wait twice as long."""
    import httpx

    runnable = FakeRunnable(
        openai.APITimeoutError(request=httpx.Request("POST", "https://openrouter.ai")),
        valid("too late"),
    )
    install(monkeypatch, runnable)

    with pytest.raises(ServiceError):
        await client.complete(
            [{"role": "user", "content": "hi"}], Reply, model="m",
            purpose=llm_calls.Purpose.CHAT, settings=settings(),
        )
    assert runnable.calls == 1
