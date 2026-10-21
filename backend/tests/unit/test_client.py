# ABOUTME: Checks complete()'s own logic - the schema retry and what gets recorded.
# ABOUTME: The provider call is faked; nothing here needs a database or a network call.

from __future__ import annotations

import asyncio
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
    """Stands in for chain.build()'s Runnable - one scripted result per astream() call, streamed as the
    pieces the real chain yields (raw, parsing_error, parsed)."""

    def __init__(self, *results: dict) -> None:
        self._results = list(results)
        self.calls = 0

    async def scripted(self, messages: list[dict]) -> dict:
        self.calls += 1
        result = self._results[min(self.calls - 1, len(self._results) - 1)]
        if isinstance(result, BaseException):
            raise result
        return result

    async def astream(self, messages: list[dict]):
        for key, value in (await self.scripted(messages)).items():
            yield {key: value}


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
        async def scripted(self, messages: list[dict]) -> dict:
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


def cut_off(output_tokens: int = 2048, reasoning: int = 0) -> openai.LengthFinishReasonError:
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
                prompt_tokens_details={"cached_tokens": 60},
                completion_tokens_details={"reasoning_tokens": reasoning},
            ),
        )
    )


async def test_a_reply_cut_off_by_the_token_limit_is_retried(monkeypatch, recorded):
    runnable = FakeRunnable(cut_off(reasoning=1955), valid("second try"))
    install(monkeypatch, runnable)

    call = await client.complete(
        [{"role": "user", "content": "hi"}], Reply, model="m",
        purpose=llm_calls.Purpose.CHAT, settings=settings(),
    )

    assert call.value.text == "second try"
    assert runnable.calls == 2
    failed = recorded[0]
    assert failed["outcome"] is llm_calls.Outcome.SCHEMA_INVALID
    # The cut-off attempt was generated and billed in full; recording 0 would hide it, and the
    # thinking that used the budget up is what the effort is chosen from.
    assert failed["usage"].output_tokens == 2048
    assert failed["usage"].reasoning_tokens == 1955
    assert failed["usage"].cached_input_tokens == 60


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


class SlowThenValid(FakeRunnable):
    """The first attempt takes a while and fails to parse; the second answers at once."""

    async def scripted(self, messages: list[dict]) -> dict:
        if self.calls == 0:
            await asyncio.sleep(0.3)
        return await super().scripted(messages)


async def test_a_retried_attempts_latency_is_its_own_not_the_attempts_before_it(
    monkeypatch, recorded
):
    install(monkeypatch, SlowThenValid(invalid(), valid()))

    await client.complete(
        [{"role": "user", "content": "hi"}], Reply, model="m",
        purpose=llm_calls.Purpose.CHAT, settings=settings(),
    )

    failed, succeeded = recorded
    assert failed["latency_ms"] >= 300
    assert succeeded["latency_ms"] < 150


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


async def test_a_chat_reply_past_its_deadline_fails_as_too_slow_and_is_recorded(monkeypatch, recorded):
    """2026-10-14: a provider kept the connection open and replied after 102 s, past the per read timeout
    and the chat tester's 90 s. A chat call now has a deadline for the whole call; a resend is safe."""
    class Stalled:
        calls = 0

        async def astream(self, messages):
            Stalled.calls += 1
            await asyncio.sleep(10)
            yield {}

    install(monkeypatch, Stalled())
    quick = settings().model_copy(update={"chat_deadline_seconds": 0.05})
    with pytest.raises(ServiceError) as raised:
        await client.complete(
            [{"role": "user", "content": "hi"}], Reply, model="m",
            purpose=llm_calls.Purpose.CHAT, settings=quick,
        )
    assert raised.value.retryable and raised.value.user_message == "Mani took too long to answer. Please try again."
    assert Stalled.calls == 1, "never retried: the wait already happened"
    assert [r["outcome"] for r in recorded] == [llm_calls.Outcome.TIMEOUT]
    assert recorded[0]["generation_id"] is None, "no reply came back, so there is no id to trace"


def openrouter_stream(content: str, generation_id: str, finish_reason: str = "stop", wait: float = 0.0):
    """A chat completion as OpenRouter streams it: its own id on every chunk, the content in two pieces,
    and the usage on a last chunk of its own. `wait` is the silence before the first chunk, which is a
    reasoning model thinking."""
    import json

    async def stream():
        await asyncio.sleep(wait)
        base = {"id": generation_id, "object": "chat.completion.chunk", "created": 1_760_400_000,
                "model": "openai/gpt-6-luna", "provider": "Azure"}
        half = len(content) // 2
        for piece in (content[:half], content[half:]):
            delta = {"role": "assistant", "content": piece}
            yield f"data: {json.dumps({**base, 'choices': [{'index': 0, 'delta': delta, 'finish_reason': None}]})}\n\n".encode()
        yield f"data: {json.dumps({**base, 'choices': [{'index': 0, 'delta': {}, 'finish_reason': finish_reason}]})}\n\n".encode()
        usage = {"prompt_tokens": 7000, "completion_tokens": 300, "total_tokens": 7300}
        yield f"data: {json.dumps({**base, 'choices': [], 'usage': usage})}\n\n".encode()
        yield b"data: [DONE]\n\n"

    return stream


def over_openrouter(monkeypatch, *streams, chunk_timeout: float = 5.0) -> list:
    """The real LangChain model and OpenAI SDK, with only the HTTP replies scripted. Returns the requests
    that reached the network."""
    import httpx
    from langchain_openai import ChatOpenAI

    replies, requests = iter(streams), []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=next(replies)())

    model = ChatOpenAI(
        model="openai/gpt-6-luna", base_url="https://openrouter.ai/api/v1",
        api_key="sk-test-not-a-real-key", max_retries=0, stream_chunk_timeout=chunk_timeout,
        http_async_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    install(monkeypatch, model.with_structured_output(Reply, method="json_schema", include_raw=True))
    return requests


async def test_each_call_records_the_generation_that_served_it(monkeypatch, recorded):
    """2026-10-14: a slow turn could not be traced to the endpoint that served it. The id is what
    OpenRouter resolves to that endpoint, so a cut off attempt and its retry each keep their own."""
    over_openrouter(
        monkeypatch,
        openrouter_stream('{"text": "cut', "gen-cut-off", finish_reason="length"),
        openrouter_stream('{"text": "second try"}', "gen-answered"),
    )

    call = await client.complete(
        [{"role": "user", "content": "hi"}], Reply, model="openai/gpt-6-luna",
        purpose=llm_calls.Purpose.CHAT, settings=settings(),
    )

    assert call.value.text == "second try"
    assert [(r["outcome"], r["generation_id"]) for r in recorded] == [
        (llm_calls.Outcome.SCHEMA_INVALID, "gen-cut-off"),
        (llm_calls.Outcome.OK, "gen-answered"),
    ]


async def test_a_streamed_reply_records_its_usage_and_generation(monkeypatch, recorded):
    over_openrouter(monkeypatch, openrouter_stream('{"text": "hello"}', "gen-streamed"))

    call = await client.complete(
        [{"role": "user", "content": "hi"}], Reply, model="openai/gpt-6-luna",
        purpose=llm_calls.Purpose.CHAT, settings=settings(),
    )

    assert call.value.text == "hello"
    assert (call.usage.input_tokens, call.usage.output_tokens) == (7000, 300)
    assert [(r["outcome"], r["generation_id"]) for r in recorded] == [(llm_calls.Outcome.OK, "gen-streamed")]


async def test_a_call_that_sends_nothing_for_too_long_is_cut_and_tried_once_more(monkeypatch, recorded):
    """2026-10-21: a reasoning model thought for 22 s before its first token while its neighbours took 5, and
    the 30 s deadline turned the slowest ones into an error. The silent attempt is recorded as a timeout on its
    own row, and the second try answers."""
    requests = over_openrouter(
        monkeypatch,
        openrouter_stream('{"text": "too late"}', "gen-silent", wait=1.0),
        openrouter_stream('{"text": "answered on the second try"}', "gen-answered"),
        chunk_timeout=0.1,
    )

    call = await client.complete(
        [{"role": "user", "content": "hi"}], Reply, model="openai/gpt-6-luna",
        purpose=llm_calls.Purpose.CHAT, settings=settings(),
    )

    assert call.value.text == "answered on the second try"
    assert len(requests) == 2
    assert [(r["outcome"], r.get("generation_id")) for r in recorded] == [
        (llm_calls.Outcome.TIMEOUT, None), (llm_calls.Outcome.OK, "gen-answered"),
    ]
    assert recorded[0]["usage"] == llm_calls.Usage()


async def test_a_call_silent_twice_fails_as_too_slow_after_two_tries_only(monkeypatch, recorded):
    requests = over_openrouter(
        monkeypatch,
        openrouter_stream('{"text": "a"}', "gen-1", wait=1.0), openrouter_stream('{"text": "b"}', "gen-2", wait=1.0),
        openrouter_stream('{"text": "c"}', "gen-3"),
        chunk_timeout=0.1,
    )

    with pytest.raises(ServiceError) as raised:
        await client.complete(
            [{"role": "user", "content": "hi"}], Reply, model="openai/gpt-6-luna",
            purpose=llm_calls.Purpose.CHAT, settings=settings(),
        )

    assert raised.value.retryable and raised.value.user_message == "Mani took too long to answer. Please try again."
    assert len(requests) == 2, "one retry, never a third try"
    assert [r["outcome"] for r in recorded] == [llm_calls.Outcome.TIMEOUT, llm_calls.Outcome.TIMEOUT]


async def test_the_silence_a_chat_call_may_keep_is_the_first_token_limit_and_a_background_call_keeps_the_read_limit(
    monkeypatch, recorded
):
    seen: list[float] = []

    def build(*args, chunk_timeout, **kwargs):
        seen.append(chunk_timeout)
        return FakeRunnable(valid())

    monkeypatch.setattr(client.chain, "build", build)
    for purpose in (llm_calls.Purpose.CHAT, llm_calls.Purpose.SUMMARIZE):
        await client.complete([], Reply, model="m", purpose=purpose, settings=settings())

    assert seen == [settings().chat_first_token_seconds, settings().llm_timeout_seconds]
