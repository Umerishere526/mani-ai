# ABOUTME: The LCEL chain behind one turn - an OpenRouter chat model with a typed output.
# ABOUTME: LangChain composes the call; it does not hold conversation state or reach the database.

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from mani.config import Settings
from mani.db import llm_calls

# LangChain's OpenAI package is an OpenAI-*protocol* client, not a second provider or a second
# bill. It takes a base_url, so it speaks to OpenRouter with the OpenRouter key, exactly as the
# bare SDK did - and it depends on the same `openai` package, so nothing is duplicated.
#
# Two things stay out of this layer on purpose:
#   - conversation state, which lives in Postgres under RLS and is loaded in one composed read;
#   - retries, which are the caller's budget to spend. max_retries=0 here, as before.
#
# LangSmith is left off. It is the genuine draw of this ecosystem and it would receive
# conversation transcripts, which are special-category health data.


@lru_cache
def _model(
    api_key: str,
    base_url: str,
    timeout: float,
    model: str,
    temperature: float,
    max_tokens: int,
    extra_body: str,
) -> ChatOpenAI:
    """One configured chat model per distinct configuration, reused across turns.

    Cached because building it parses the schema and constructs an HTTP client; the arguments
    are primitives so the cache key is stable. `extra_body` arrives as JSON for that reason.
    """
    return ChatOpenAI(
        model=model,
        base_url=base_url,
        api_key=api_key,
        timeout=timeout,
        temperature=temperature,
        max_tokens=max_tokens,
        # The SDK's own retries multiply the bill and the latency of a turn that is already
        # slow. One attempt; a retry is a decision the caller makes with its own budget.
        max_retries=0,
        extra_body=json.loads(extra_body),
    )


def build(
    schema: type[BaseModel],
    *,
    model: str,
    temperature: float,
    max_tokens: int,
    routing: dict[str, Any] | None,
    settings: Settings,
) -> Runnable:
    """A runnable that takes chat messages and returns raw, parsed and parsing_error.

    `include_raw` keeps the provider's own response alongside the parsed object, which is what
    makes the token accounting possible - and turns a malformed reply into a value rather than
    an exception, so the caller can decide what a schema failure is worth.
    """
    extra_body = {
        "provider": settings.routing(routing),
        # Without this OpenRouter omits the cached-token count, which is the only way to tell
        # whether prompt caching is actually happening.
        "usage": {"include": True},
    }
    chat = _model(
        settings.openrouter_api_key,
        settings.openrouter_base_url,
        settings.llm_timeout_seconds,
        model,
        temperature,
        max_tokens,
        json.dumps(extra_body, sort_keys=True),
    )
    return chat.with_structured_output(schema, method="json_schema", include_raw=True)


def usage_from(raw: Any) -> llm_calls.Usage:
    """Token counts off the provider's response, whichever shape LangChain hands back."""
    if raw is None:
        return llm_calls.Usage()

    metadata = getattr(raw, "usage_metadata", None) or {}
    if metadata:
        details = metadata.get("input_token_details") or {}
        return llm_calls.Usage(
            input_tokens=metadata.get("input_tokens", 0) or 0,
            output_tokens=metadata.get("output_tokens", 0) or 0,
            cached_input_tokens=details.get("cache_read", 0) or 0,
        )

    token_usage = (getattr(raw, "response_metadata", None) or {}).get("token_usage") or {}
    prompt_details = token_usage.get("prompt_tokens_details") or {}
    return llm_calls.Usage(
        input_tokens=token_usage.get("prompt_tokens", 0) or 0,
        output_tokens=token_usage.get("completion_tokens", 0) or 0,
        cached_input_tokens=prompt_details.get("cached_tokens", 0) or 0,
    )
