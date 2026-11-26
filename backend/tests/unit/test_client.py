# ABOUTME: Checks complete()'s own logic - the schema retry and what gets recorded.
# ABOUTME: The provider call is faked; nothing here needs a database or a network call.

from __future__ import annotations

import asyncio
import json
import uuid
from types import SimpleNamespace

import openai
import pytest
from openai.types import CompletionUsage
from openai.types.chat import ChatCompletion
from pydantic import BaseModel

from mani.config import Settings
from mani.db import llm_calls
from mani.errors import ServiceError
from mani.llm import client


class Said(BaseModel):
    """Any structured reply: the client is schema-agnostic."""

    text: str


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

    async def astream(self, messages: list[dict], config=None):
        for key, value in (await self.scripted(messages)).items():
            yield {key: value}


def valid(text: str = "hi") -> dict:
    return {"raw": None, "parsed": Said(text=text), "parsing_error": None}


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
        [], Said, model="m", purpose=llm_calls.Purpose.CHAT, settings=settings()
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
        [], Said, model="m", purpose=llm_calls.Purpose.CHAT, settings=settings()
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
            [], Said, model="m", purpose=llm_calls.Purpose.CHAT, settings=settings()
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
            [], Said, model="m", purpose=llm_calls.Purpose.CHAT, settings=settings()
        )

    assert runnable.calls == 1
    assert [c["outcome"] for c in recorded] == [llm_calls.Outcome.PROVIDER_ERROR]


def cut_off(output_tokens: int = 2048, reasoning: int = 0, cost: float | None = None) -> openai.LengthFinishReasonError:
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
                cost=cost,
            ),
        )
    )


async def test_a_reply_cut_off_by_the_token_limit_is_retried(monkeypatch, recorded):
    runnable = FakeRunnable(cut_off(reasoning=1955, cost=0.0061), valid("second try"))
    install(monkeypatch, runnable)

    call = await client.complete(
        [{"role": "user", "content": "hi"}], Said, model="m",
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
    assert failed["usage"].cost_usd == 0.0061


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
            [{"role": "user", "content": "hi"}], Said, model="m",
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
        [{"role": "user", "content": "hi"}], Said, model="m",
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
        [{"role": "user", "content": "hi"}], Said, model="m",
        purpose=llm_calls.Purpose.CHAT, settings=settings(),
    )

    assert call.value.text == "answered on the retry"
    assert runnable.calls == 2
    assert recorded[0]["outcome"] is llm_calls.Outcome.PROVIDER_ERROR


def bad_request(body: dict) -> openai.BadRequestError:
    import httpx

    request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
    return openai.BadRequestError("Error code: 400", response=httpx.Response(400, request=request), body=body)


async def test_openrouter_refusing_to_relay_is_retried_once_and_says_why(monkeypatch, recorded):
    """2026-11-25: 23 of 25 calls in one minute came back 400 "Request path cannot be relayed", OpenRouter's own
    refusal with no provider involved, and each reached the person as the fixed error reply."""
    relay = bad_request({"error": {"message": "Request path cannot be relayed", "code": 400}})
    runnable = FakeRunnable(relay, valid("answered on the retry"))
    install(monkeypatch, runnable)
    monkeypatch.setattr(client, "TRANSIENT_RETRY_DELAY_SECONDS", 0)

    call = await client.complete(
        [{"role": "user", "content": "hi"}], Said, model="m",
        purpose=llm_calls.Purpose.CHAT, settings=settings(),
    )

    assert call.value.text == "answered on the retry"
    assert runnable.calls == 2
    assert "Request path cannot be relayed" in recorded[0]["error_message"]


async def test_a_providers_400_is_not_retried_and_keeps_its_body_out(monkeypatch, recorded):
    """A 400 a provider raised carries its raw body in metadata, which can quote what they wrote: not retried, and
    only its host is stored."""
    words = "I keep snapping at my partner"
    refused = bad_request({"error": {"message": "Provider returned error",
                                     "metadata": {"provider_name": "DeepInfra", "raw": f"bad input: {words}"}}})
    runnable = FakeRunnable(refused, valid("never reached"))
    install(monkeypatch, runnable)

    with pytest.raises(ServiceError):
        await client.complete(
            [{"role": "user", "content": "hi"}], Said, model="m",
            purpose=llm_calls.Purpose.CHAT, settings=settings(),
        )
    assert runnable.calls == 1
    assert words not in recorded[0]["error_message"] and "DeepInfra" in recorded[0]["error_message"]


async def test_a_provider_down_twice_fails_the_turn(monkeypatch, recorded):
    install(monkeypatch, FakeRunnable(provider_down(), provider_down()))
    monkeypatch.setattr(client, "TRANSIENT_RETRY_DELAY_SECONDS", 0)

    with pytest.raises(ServiceError) as failed:
        await client.complete(
            [{"role": "user", "content": "hi"}], Said, model="m",
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
            [{"role": "user", "content": "hi"}], Said, model="m",
            purpose=llm_calls.Purpose.CHAT, settings=settings(),
        )
    assert runnable.calls == 1


async def test_a_chat_reply_past_its_deadline_fails_as_too_slow_and_is_recorded(monkeypatch, recorded):
    """2026-10-14: a provider kept the connection open and replied after 102 s, past the per read timeout
    and the chat tester's 90 s. A chat call now has a deadline for the whole call; a resend is safe."""
    class Stalled:
        calls = 0

        async def astream(self, messages, config=None):
            Stalled.calls += 1
            await asyncio.sleep(10)
            yield {}

    install(monkeypatch, Stalled())
    quick = settings().model_copy(update={"chat_deadline_seconds": 0.05})
    with pytest.raises(ServiceError) as raised:
        await client.complete(
            [{"role": "user", "content": "hi"}], Said, model="m",
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
        usage = {"prompt_tokens": 7000, "completion_tokens": 300, "total_tokens": 7300, "cost": 0.0042, "is_byok": False,
                 "prompt_tokens_details": {"cached_tokens": 0}, "cost_details": {"upstream_inference_cost": None}}
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
    install(monkeypatch, model.with_structured_output(Said, method="json_schema", include_raw=True))
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
        [{"role": "user", "content": "hi"}], Said, model="openai/gpt-6-luna",
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
        [{"role": "user", "content": "hi"}], Said, model="openai/gpt-6-luna",
        purpose=llm_calls.Purpose.CHAT, settings=settings(),
    )

    assert call.value.text == "hello"
    assert (call.usage.input_tokens, call.usage.output_tokens) == (7000, 300)
    assert call.usage.cost_usd == 0.0042, "OpenRouter's billed cost survives LangChain's stream"


async def test_a_streamed_reply_records_when_its_first_chunk_arrived(monkeypatch, recorded):
    """The reply is parsed whole at the end, so the time to its first chunk, the model thinking, is measured apart
    from the whole call."""
    over_openrouter(monkeypatch, openrouter_stream('{"text": "hello"}', "gen-streamed", wait=0.2))

    call = await client.complete(
        [{"role": "user", "content": "hi"}], Said, model="openai/gpt-6-luna",
        purpose=llm_calls.Purpose.CHAT, settings=settings(),
    )

    assert 200 <= call.first_token_ms <= call.latency_ms
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
        [{"role": "user", "content": "hi"}], Said, model="openai/gpt-6-luna",
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
            [{"role": "user", "content": "hi"}], Said, model="openai/gpt-6-luna",
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
        await client.complete([], Said, model="m", purpose=purpose, settings=settings())

    assert seen == [settings().chat_first_token_seconds, settings().llm_timeout_seconds]


@pytest.fixture
def sent_headers() -> list[dict]:
    """The headers of each request that reached the fake OpenRouter, in the order sent_bodies keeps its bodies."""
    return []


@pytest.fixture
def sent_bodies(monkeypatch, sent_headers):
    """chain.build, langchain-openai and the OpenAI SDK as they run, with only the HTTP replies scripted: every
    model chain.build makes talks to a fake OpenRouter that answers each request with a valid reply. Yields the
    JSON body of each request that reached the network."""
    import functools

    import httpx
    from langchain_openai import ChatOpenAI

    bodies: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        sent_headers.append(dict(request.headers))
        stream = openrouter_stream('{"text": "hi"}', f"gen-{len(bodies)}")
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=stream())

    transport = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(client.chain, "ChatOpenAI", functools.partial(ChatOpenAI, http_async_client=transport))
    # Models cached by other tests hold a real HTTP client; none may be reused here, nor these leak out.
    client.chain._model.cache_clear()
    yield bodies
    client.chain._model.cache_clear()


THREAD = uuid.UUID("7e5a0000-0000-4000-8000-000000000001")
OTHER_THREAD = uuid.UUID("7e5a0000-0000-4000-8000-000000000002")


async def test_a_call_with_a_thread_carries_its_sticky_keys_beside_the_provider_reasoning_and_usage(
    sent_bodies, recorded
):
    """2026-11-05: OpenRouter recorded session_id null on every call and turn 2 of a thread was almost never
    cached. The keys ride on the call itself, merged into what every call sends, and the configured model is
    still one per configuration, not one per conversation."""
    for thread in (THREAD, OTHER_THREAD):
        await client.complete(
            [{"role": "user", "content": "hi"}], Said, model="openai/gpt-6-luna",
            purpose=llm_calls.Purpose.CHAT, reasoning_effort="medium", thread_id=thread, settings=settings(),
        )

    first, second = sent_bodies
    assert first["session_id"] == first["prompt_cache_key"] == f"{THREAD}:chat"
    assert second["session_id"] == second["prompt_cache_key"] == f"{OTHER_THREAD}:chat"
    assert first["provider"]["data_collection"] == "deny" and "order" not in first["provider"]
    assert first["reasoning"] == {"effort": "medium"}
    assert first["usage"] == {"include": True}
    assert first["stream"] is True
    assert client.chain._model.cache_info().currsize == 1, "one model for both threads"


async def test_a_chat_call_never_opts_into_openrouters_response_cache(sent_bodies, sent_headers, recorded):
    """A stored reply could reach another chat. OpenRouter replays one only on X-OpenRouter-Cache or a preset."""
    for thread in (THREAD, OTHER_THREAD):
        await client.complete([{"role": "user", "content": "hi"}], Said, model="minimax/minimax-m3.1-flash",
                              purpose=llm_calls.Purpose.CHAT, thread_id=thread, settings=settings())
    for body, sent in zip(sent_bodies, sent_headers, strict=True):
        assert not any(name.lower().startswith("x-openrouter-cache") for name in sent)
        assert "preset" not in body and "cache_enabled" not in json.dumps(body)
    assert [b["prompt_cache_key"] for b in sent_bodies] == [f"{THREAD}:chat", f"{OTHER_THREAD}:chat"]


async def test_a_call_with_no_thread_sends_no_sticky_keys(sent_bodies, recorded):
    await client.complete(
        [{"role": "user", "content": "hi"}], Said, model="openai/gpt-6-luna",
        purpose=llm_calls.Purpose.SUMMARIZE, settings=settings(),
    )

    assert "session_id" not in sent_bodies[0] and "prompt_cache_key" not in sent_bodies[0]


async def test_only_the_chat_reply_asks_for_the_priority_tier_and_each_purpose_keeps_its_own_key(
    sent_bodies, recorded
):
    """The person waits on the chat reply alone: it asks for OpenAI's priority endpoint and may fall back to the
    standard one, never to Azure, Bedrock or flex. The calls after the reply stay on the default tier, under a
    key of their own, so they never re-pin the chat's conversation to another endpoint."""
    purposes = (llm_calls.Purpose.CHAT, llm_calls.Purpose.SUMMARIZE)
    for purpose in purposes:
        await client.complete(
            [{"role": "user", "content": "hi"}], Said, model="openai/gpt-6-luna",
            purpose=purpose, thread_id=THREAD, settings=settings(),
        )

    chat, *background = sent_bodies
    assert chat["service_tier"] == "priority"
    assert chat["provider"] == {
        "only": ["openai", "openai/priority"], "sort": "latency", "allow_fallbacks": True,
        "data_collection": "deny", "zdr": True,
    }
    for purpose, body in zip(purposes[1:], background, strict=True):
        assert "service_tier" not in body, purpose
        assert body["provider"]["only"] == ["openai"], purpose
        assert body["provider"]["zdr"] is True, purpose
        assert body["session_id"] == body["prompt_cache_key"] == f"{THREAD}:{purpose.value}"


async def test_the_priority_tier_is_switched_off_by_configuration(sent_bodies, recorded):
    await client.complete(
        [{"role": "user", "content": "hi"}], Said, model="openai/gpt-6-luna", purpose=llm_calls.Purpose.CHAT,
        thread_id=THREAD, settings=settings().model_copy(update={"openrouter_chat_service_tier": "default"}),
    )

    assert "service_tier" not in sent_bodies[0]
    assert sent_bodies[0]["provider"]["only"] == ["openai"]


async def test_a_retry_gets_only_what_is_left_of_the_chat_budget(monkeypatch, recorded):
    """Both attempts share one budget, so a malformed first reply that came late leaves its retry the rest of
    it, not a whole deadline: every wait on a turn adds up under the chat-tester's 90 s (2026-11-05)."""
    class LateThenStalled(FakeRunnable):
        async def scripted(self, messages):
            self.calls += 1
            await asyncio.sleep(0.2 if self.calls == 1 else 10)
            return invalid()

    install(monkeypatch, LateThenStalled())
    tight = settings().model_copy(update={"chat_deadline_seconds": 10.0, "chat_budget_seconds": 1.5})
    began = asyncio.get_running_loop().time()

    with pytest.raises(ServiceError) as raised:
        await client.complete([], Said, model="m", purpose=llm_calls.Purpose.CHAT, settings=tight)

    assert asyncio.get_running_loop().time() - began < 4.0, "the retry was cut at the budget, not the deadline"
    assert raised.value.user_message == "Mani took too long to answer. Please try again."
    assert [r["outcome"] for r in recorded] == [llm_calls.Outcome.SCHEMA_INVALID, llm_calls.Outcome.TIMEOUT]


async def test_a_call_that_finds_every_slot_taken_is_refused_quickly_as_busy(monkeypatch, recorded):
    """An instance caps the model calls it has in flight; past the cap a call is refused fast and retryable,
    never queued behind the provider."""
    from mani.errors import ErrorCategory

    class Stalled(FakeRunnable):
        async def scripted(self, messages):
            await asyncio.sleep(10)

    install(monkeypatch, Stalled())
    one_slot = settings().model_copy(update={"model_calls_in_flight": 1, "model_slot_wait_seconds": 0.05})
    holding = asyncio.create_task(
        client.complete([], Said, model="m", purpose=llm_calls.Purpose.SUMMARIZE, settings=one_slot)
    )
    await asyncio.sleep(0.01)
    try:
        with pytest.raises(ServiceError) as raised:
            await client.complete([], Said, model="m", purpose=llm_calls.Purpose.CHAT, settings=one_slot)
    finally:
        holding.cancel()

    assert raised.value.category is ErrorCategory.RATE_LIMITED and raised.value.status_code == 429
    assert raised.value.retryable
    assert raised.value.user_message == "Mani is busy right now. Please try again in a moment."


def _quoting(words: str) -> list[BaseException]:
    """The two failures whose own text quotes the reply: pydantic's, and LangChain's parser."""
    from langchain_core.exceptions import OutputParserException
    from pydantic import ValidationError

    try:
        Said.model_validate({"text": [words]})
    except ValidationError as exc:
        return [exc, OutputParserException(f"Failed to parse Said from completion {words}")]
    raise AssertionError("expected the reply to be refused")


@pytest.mark.parametrize("which", [0, 1])
async def test_a_reply_that_does_not_fit_is_recorded_and_raised_without_its_words(monkeypatch, recorded, which):
    """Audit #5: the cost row and the error kept pydantic's message, whose `input_value=` quotes the reply.
    Only the kind of failure and where it failed are kept, as for a request that fails validation."""
    words = "I told my sister about the diagnosis"
    failure = _quoting(words)[which]
    install(monkeypatch, FakeRunnable({"raw": None, "parsed": None, "parsing_error": failure}))

    with pytest.raises(ServiceError) as raised:
        await client.complete([], Said, model="m", purpose=llm_calls.Purpose.CHAT, settings=settings())

    kept = [r["error_message"] for r in recorded] + [str(raised.value)]
    assert all(words not in k and "input_value" not in k for k in kept), kept
    assert type(failure).__name__ in recorded[0]["error_message"]
    if which == 0:
        assert "('string_type', ('text',))" in recorded[0]["error_message"], "what and where it failed are kept"


def test_a_provider_error_is_stored_without_the_body_that_can_quote_their_message():
    """A moderation refusal's body can carry the flagged input, which is the person's own words. What is stored and
    logged is the error's type and status, never its body."""
    import httpx

    words = "I keep thinking about ending it"
    response = httpx.Response(403, request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions"))
    refused = openai.PermissionDeniedError(
        f"Error code: 403 - {{'error': {{'metadata': {{'flagged_input': '{words}'}}}}}}",
        response=response, body={"error": {"metadata": {"flagged_input": words}}},
    )

    described = client._described(refused)

    assert words not in described
    assert described == "PermissionDeniedError: 403"


def test_a_provider_error_names_the_host_that_refused_and_still_quotes_nothing():
    """2026-11-25: 19 chat calls failed with a bare 400 and nothing said which host refused them. The host OpenRouter
    names is kept; the raw body, which can quote what they wrote, is not."""
    import httpx

    words = "my manager keeps adding tasks"
    response = httpx.Response(400, request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions"))
    refused = openai.BadRequestError(
        f"Error code: 400 - raw: {words}", response=response,
        body={"error": {"code": 400, "message": "Provider returned error",
                        "metadata": {"provider_name": "Fireworks", "raw": f"invalid schema near '{words}'"}}},
    )

    described = client._described(refused)

    assert words not in described
    assert described == "BadRequestError: 400 from Fireworks"


async def test_an_empty_reply_is_retried_like_any_reply_that_does_not_parse(monkeypatch, recorded):
    """2026-11-23: a host answered with reasoning tokens and no content. LangChain raises a plain ValueError for that,
    which no retry caught, so a person who wrote "i want to talk about thanksgiving" got the fixed reply with a crisis
    line. An empty reply is a reply that does not parse: it gets the same one retry. LangChain keeps no completion on
    that error, so the empty attempt's id is not known."""
    over_openrouter(
        monkeypatch,
        openrouter_stream("", "gen-empty"),
        openrouter_stream('{"text": "second try"}', "gen-answered"),
    )

    call = await client.complete(
        [{"role": "user", "content": "hi"}], Said, model="openai/gpt-6-luna",
        purpose=llm_calls.Purpose.CHAT, settings=settings(),
    )

    assert call.value.text == "second try"
    assert [(r["outcome"], r["generation_id"]) for r in recorded] == [
        (llm_calls.Outcome.SCHEMA_INVALID, None),
        (llm_calls.Outcome.OK, "gen-answered"),
    ]


class Host:
    """One host's answer to a request, as chain.build()'s Runnable streams it: `chunk_at` is when its first chunk
    arrives (never, when None), `wait` how long it takes in all, and `result` what it comes back with."""

    def __init__(self, result, *, wait: float = 0.0, chunk_at: float | None = None) -> None:
        self.result, self.wait, self.chunk_at = result, wait, chunk_at
        self.calls = 0
        self.cancelled = False

    async def astream(self, messages, config=None):
        self.calls += 1
        began = asyncio.get_running_loop().time()
        try:
            if self.chunk_at is not None:
                await asyncio.sleep(self.chunk_at)
                for callback in config["callbacks"]:
                    await callback.on_llm_new_token("")
            await asyncio.sleep(self.wait - (asyncio.get_running_loop().time() - began))
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        if isinstance(self.result, BaseException):
            raise self.result
        for key, value in self.result.items():
            yield {key: value}


TWO_HOSTS = {"only": ["sail-research", "deepinfra"], "sort": "price"}


def hosts(monkeypatch, first: Host, other: Host) -> list[dict]:
    """chain.build answering with `first` for the prompt row's routing and `other` for any other; returns what each
    build was asked for."""
    built: list[dict] = []

    def build(*args, routing, session, **kwargs):
        built.append({"only": routing["only"], "session": session})
        return first if routing == TWO_HOSTS else other

    monkeypatch.setattr(client.chain, "build", build)
    return built


def racing(**update) -> Settings:
    return settings().model_copy(update={"chat_hedge_seconds": 0.05, **update})


async def test_a_host_that_sends_nothing_is_raced_on_the_other_host_and_the_slower_is_cancelled(monkeypatch, recorded):
    """REL-2, 2026-11-25: providers slowed to 20 to 27 s with the first chunk past 15 s, and nothing tried elsewhere.
    Past the hedge wait the other host starts beside the first; its answer is the reply, the stalled request is
    cancelled, and both are recorded."""
    stalled, other = Host(valid("too slow"), wait=10), Host(valid("from the other host"), wait=0.05)
    built = hosts(monkeypatch, stalled, other)
    began = asyncio.get_running_loop().time()

    call = await client.complete([], Said, model="m", purpose=llm_calls.Purpose.CHAT, routing=TWO_HOSTS,
                                 thread_id=THREAD, settings=racing())

    assert call.value.text == "from the other host"
    assert asyncio.get_running_loop().time() - began < 1.0
    assert built == [{"only": ["sail-research", "deepinfra"], "session": f"{THREAD}:chat"},
                     {"only": ["deepinfra"], "session": None}], "no sticky key, so the race never re-pins the thread"
    assert stalled.cancelled
    assert [(r["outcome"], r["error_message"]) for r in recorded] == [
        (llm_calls.Outcome.TIMEOUT, "attempt 1/2: not used, attempt 2 answered first and this one was cancelled"),
        (llm_calls.Outcome.OK, None),
    ]


async def test_a_host_that_has_begun_streaming_is_not_raced(monkeypatch, recorded):
    streaming, other = Host(valid("streaming"), chunk_at=0.01, wait=0.2), Host(valid("never asked"))
    built = hosts(monkeypatch, streaming, other)

    call = await client.complete([], Said, model="m", purpose=llm_calls.Purpose.CHAT, routing=TWO_HOSTS,
                                 settings=racing())

    assert call.value.text == "streaming" and other.calls == 0 and len(built) == 1
    assert [r["outcome"] for r in recorded] == [llm_calls.Outcome.OK]


async def test_the_first_host_still_answers_when_the_raced_host_fails(monkeypatch, recorded):
    slow, broken = Host(valid("slow but there"), wait=0.3), Host(provider_down())
    hosts(monkeypatch, slow, broken)

    call = await client.complete([], Said, model="m", purpose=llm_calls.Purpose.CHAT, routing=TWO_HOSTS,
                                 settings=racing())

    assert call.value.text == "slow but there"
    assert [(r["outcome"], r["error_message"]) for r in recorded] == [
        (llm_calls.Outcome.PROVIDER_ERROR, "attempt 2/2: InternalServerError: 503"),
        (llm_calls.Outcome.OK, None),
    ]


async def test_an_empty_reply_is_retried_on_the_other_host(monkeypatch, recorded):
    """2026-11-23: a host answered with reasoning and no content. Its retry goes to the host it did not come from."""
    empty = Host(ValueError(f"Structured Output response {client.NO_CONTENT}"))
    other = Host(valid("second host"))
    built = hosts(monkeypatch, empty, other)

    call = await client.complete([], Said, model="m", purpose=llm_calls.Purpose.CHAT, routing=TWO_HOSTS,
                                 settings=racing(chat_hedge_seconds=8.0))

    assert call.value.text == "second host"
    assert [b["only"] for b in built] == [["sail-research", "deepinfra"], ["deepinfra"]]
    assert [r["outcome"] for r in recorded] == [llm_calls.Outcome.SCHEMA_INVALID, llm_calls.Outcome.OK]


async def test_with_one_host_allowed_a_silent_call_is_never_raced(monkeypatch, recorded):
    """A background call, or a chat row naming one host, has nowhere else to go: it keeps waiting on its one request."""
    slow = Host(valid("one host"), wait=0.2)
    built: list = []
    monkeypatch.setattr(client.chain, "build", lambda *a, **kw: built.append(kw["routing"]) or slow)

    call = await client.complete([], Said, model="m", purpose=llm_calls.Purpose.CHAT, routing={"only": ["deepinfra"]},
                                 settings=racing())

    assert call.value.text == "one host" and slow.calls == 1 and len(built) == 1
