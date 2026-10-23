# ABOUTME: Checks the streaming text extractor and complete_streaming()'s own logic.
# ABOUTME: The provider stream is faked; nothing here needs a database or a network call.

from __future__ import annotations

import uuid

import httpx
import openai
import pytest

from mani.config import Settings
from mani.db import llm_calls
from mani.errors import ServiceError
from mani.llm import client
from mani.llm.schema import Reply
from mani.llm.streaming import TextFieldExtractor


def feed_all(*chunks: str) -> tuple[list[str], TextFieldExtractor]:
    """Every delta the extractor emits for the chunk series, and the extractor itself."""
    extractor = TextFieldExtractor("text")
    return [d for d in (extractor.feed(c) for c in chunks) if d], extractor


def test_text_after_earlier_fields_is_decoded_in_one_chunk():
    deltas, extractor = feed_all('{"reasoning": "hidden", "style": "warm", "text": "hello world"}')
    assert deltas == ["hello world"]
    assert extractor.closed


def test_a_key_split_across_chunks_still_finds_the_field():
    deltas, _ = feed_all('{"reasoning": "x", "te', 'xt": "he', 'llo', '"}')
    assert "".join(deltas) == "hello"


def test_escapes_and_unicode_decode():
    deltas, _ = feed_all('"text": "a\\nb \\"c\\" \\u00e9 \\t end"}')
    assert "".join(deltas) == 'a\nb "c" é \t end'


def test_an_escape_split_at_the_chunk_end_waits_for_the_rest():
    deltas, _ = feed_all('"text": "a\\', 'nb \\u00', '41 done"}')
    assert "".join(deltas) == "a\nb A done"


def test_a_surrogate_pair_split_across_chunks_decodes_as_one_character():
    deltas, _ = feed_all('"text": "\\ud83d\\', 'ude00!"}')
    assert "".join(deltas) == "\U0001f600!"


def test_a_lone_high_surrogate_becomes_the_replacement_character():
    deltas, _ = feed_all('"text": "\\ud83d x"}')
    assert "".join(deltas) == "\ufffd x"


def test_an_invalid_escape_is_a_schema_failure_for_the_caller():
    with pytest.raises(ValueError):
        feed_all('"text": "a\\xb"}')


def test_nothing_after_the_closing_quote_is_emitted():
    extractor = TextFieldExtractor("text")
    assert extractor.feed('"text": "hi"} trailing') == "hi"
    assert extractor.feed('{"other": 1}') == ""


def test_a_reply_without_the_field_emits_nothing():
    deltas, extractor = feed_all('{"reasoning": "all of it"}')
    assert deltas == []
    assert extractor.text == ""


class FakeChunk:
    """One streamed piece: content, plus usage on the final chunk as providers send it."""

    def __init__(self, content: str, usage: dict | None = None) -> None:
        self.content = content
        self.usage_metadata = usage or {}

    def __add__(self, other: "FakeChunk") -> "FakeChunk":
        return FakeChunk(self.content + other.content, other.usage_metadata or self.usage_metadata)


class FakeStreamRunnable:
    """Stands in for chain.build_stream()'s runnable - one scripted stream per astream() call."""

    def __init__(self, *scripts: list) -> None:
        self._scripts = list(scripts)
        self.calls = 0

    async def astream(self, messages: list[dict]):
        self.calls += 1
        script = self._scripts[min(self.calls - 1, len(self._scripts) - 1)]
        for item in script:
            if isinstance(item, BaseException):
                raise item
            yield item


def settings() -> Settings:
    return Settings(
        database_url="postgresql://localhost/none",
        supabase_url="https://example.supabase.co",
        supabase_jwt_secret="secret",
        openrouter_api_key="sk-test-not-a-real-key",
    )


def chunks(*pieces, usage: dict | None = None) -> list:
    """A scripted stream: strings become chunks, exceptions pass through to be raised."""
    items = [FakeChunk(p) if isinstance(p, str) else p for p in pieces]
    if usage:
        for item in reversed(items):
            if isinstance(item, FakeChunk):
                item.usage_metadata = usage
                break
    return items


@pytest.fixture
def recorded(monkeypatch):
    """Every call `complete_streaming()` makes to _record, without touching a database."""
    calls: list[dict] = []

    async def fake_record(**kwargs) -> uuid.UUID:
        calls.append(kwargs)
        return uuid.uuid4()

    monkeypatch.setattr(client, "_record", fake_record)
    return calls


@pytest.fixture
def deltas():
    """The delta/reset callbacks, collected."""
    events: list[tuple[str, str]] = []

    async def on_delta(text: str) -> None:
        events.append(("delta", text))

    async def on_reset() -> None:
        events.append(("reset", ""))

    return events, on_delta, on_reset


async def test_a_streamed_reply_reaches_the_caller_in_order(monkeypatch, recorded, deltas):
    usage = {"input_tokens": 10, "output_tokens": 5, "input_token_details": {"cache_read": 3}}
    runnable = FakeStreamRunnable(
        chunks('{"reasoning": "hidden", "te', 'xt": "he', 'llo wor', 'ld"}', usage=usage)
    )
    monkeypatch.setattr(client.chain, "build_stream", lambda *a, **kw: runnable)
    events, on_delta, on_reset = deltas

    call = await client.complete_streaming(
        [], Reply, model="m", purpose=llm_calls.Purpose.CHAT,
        on_delta=on_delta, on_reset=on_reset, settings=settings(),
    )

    assert runnable.calls == 1
    assert call.value.text == "hello world"
    assert events == [("delta", "he"), ("delta", "llo wor"), ("delta", "ld")]
    assert call.usage.input_tokens == 10 and call.usage.cached_input_tokens == 3
    assert [c["outcome"] for c in recorded] == [llm_calls.Outcome.OK]


async def test_a_malformed_first_attempt_resets_the_client_and_streams_again(
    monkeypatch, recorded, deltas
):
    runnable = FakeStreamRunnable(
        chunks('{"text": "cut off bef'), chunks('{"text": "whole"}')
    )
    monkeypatch.setattr(client.chain, "build_stream", lambda *a, **kw: runnable)
    events, on_delta, on_reset = deltas

    call = await client.complete_streaming(
        [], Reply, model="m", purpose=llm_calls.Purpose.CHAT,
        on_delta=on_delta, on_reset=on_reset, settings=settings(),
    )

    assert runnable.calls == 2
    assert call.value.text == "whole"
    assert events == [("delta", "cut off bef"), ("reset", ""), ("delta", "whole")]
    assert [c["outcome"] for c in recorded] == [
        llm_calls.Outcome.SCHEMA_INVALID,
        llm_calls.Outcome.OK,
    ]


async def test_two_malformed_attempts_raise_and_record_both(monkeypatch, recorded, deltas):
    runnable = FakeStreamRunnable(chunks('{"text": "one'), chunks('{"text": "two'))
    monkeypatch.setattr(client.chain, "build_stream", lambda *a, **kw: runnable)
    events, on_delta, on_reset = deltas

    with pytest.raises(ServiceError):
        await client.complete_streaming(
            [], Reply, model="m", purpose=llm_calls.Purpose.CHAT,
            on_delta=on_delta, on_reset=on_reset, settings=settings(),
        )

    assert runnable.calls == client.MAX_SCHEMA_ATTEMPTS == 2
    assert [c["outcome"] for c in recorded] == [
        llm_calls.Outcome.SCHEMA_INVALID,
        llm_calls.Outcome.SCHEMA_INVALID,
    ]


async def test_a_provider_blip_mid_stream_is_retried_once(monkeypatch, recorded, deltas):
    blip = openai.APIConnectionError(request=httpx.Request("POST", "https://x"))
    runnable = FakeStreamRunnable(
        chunks('{"text": "partial', blip), chunks('{"text": "fine"}')
    )
    monkeypatch.setattr(client.chain, "build_stream", lambda *a, **kw: runnable)
    events, on_delta, on_reset = deltas

    call = await client.complete_streaming(
        [], Reply, model="m", purpose=llm_calls.Purpose.CHAT,
        on_delta=on_delta, on_reset=on_reset, settings=settings(),
    )

    assert runnable.calls == 2
    assert call.value.text == "fine"
    assert ("reset", "") in events
    assert [c["outcome"] for c in recorded] == [
        llm_calls.Outcome.PROVIDER_ERROR,
        llm_calls.Outcome.OK,
    ]
