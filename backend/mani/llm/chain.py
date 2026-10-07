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


# Reasoning models reject the sampling parameters an ordinary chat model takes. They fix
# their own sampling and read a reasoning effort instead, and Azure names the output budget
# `max_completion_tokens` rather than `max_tokens`. Sending the wrong one is a 400 on every
# call, so the shape of the request follows the model rather than the call site.
REASONING_MODEL_PREFIXES = ("openai/gpt-6", "openai/gpt-5", "openai/o1", "openai/o3")


def is_reasoning_model(model: str) -> bool:
    return model.startswith(REASONING_MODEL_PREFIXES)


def _reasoning(model: str, settings: Settings, effort: str | None = None) -> dict[str, Any]:
    """How hard the model thinks before it answers, for the models that read it.

    A model that does not take a reasoning effort rejects the key, so it is sent only to
    the ones that do. A prompt row names its own effort when the work it does deserves a
    different one; otherwise the configured default stands for all of them.
    """
    if not is_reasoning_model(model):
        return {}
    return {"reasoning": {"effort": effort or settings.reasoning_effort}}


# A reasoning model's output budget covers its thinking and its reply together, and every caller
# sizes `max_tokens` for the reply alone. Measured 2026-10-07 at effort high: a chat turn thought
# for 1,955 of its 2,048 tokens and the reply was cut off. Unused budget is not billed, and
# LLM_TIMEOUT_SECONDS still bounds a turn that thinks for too long.
# ponytail: one allowance for every effort; per-effort allowances if low or max need tuning.
REASONING_ALLOWANCE_TOKENS = 8192


def sampling(model: str, temperature: float, max_tokens: int) -> dict[str, Any]:
    """The output budget, and the temperature for the models that take one."""
    if is_reasoning_model(model):
        return {"max_completion_tokens": max_tokens + REASONING_ALLOWANCE_TOKENS}
    return {"temperature": temperature, "max_tokens": max_tokens}


def request_body(
    model: str,
    settings: Settings,
    routing: dict[str, Any] | None = None,
    effort: str | None = None,
) -> dict[str, Any]:
    """What OpenRouter is told beside the messages: which providers may serve the call, under
    which data policy, and how hard to think. Every call sends this, so none of them reaches
    a provider or a default effort the others refuse."""
    return {
        "provider": settings.routing(routing),
        # Without this OpenRouter omits the cached-token count, which is the only way to tell
        # whether prompt caching is actually happening.
        "usage": {"include": True},
        **_reasoning(model, settings, effort),
    }


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
        # The SDK's own retries multiply the bill and the latency of a turn that is already
        # slow. One attempt; a retry is a decision the caller makes with its own budget.
        max_retries=0,
        extra_body=json.loads(extra_body),
        **sampling(model, temperature, max_tokens),
    )


def build(
    schema: type[BaseModel],
    *,
    model: str,
    temperature: float,
    max_tokens: int,
    routing: dict[str, Any] | None,
    settings: Settings,
    reasoning_effort: str | None = None,
) -> Runnable:
    """A runnable that takes chat messages and returns raw, parsed and parsing_error.

    `include_raw` keeps the provider's own response alongside the parsed object, which is what
    makes the token accounting possible - and turns a malformed reply into a value rather than
    an exception, so the caller can decide what a schema failure is worth.
    """
    extra_body = request_body(model, settings, routing, reasoning_effort)
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


def build_tool_choice(
    tool: type[BaseModel],
    *,
    model: str,
    temperature: float,
    max_tokens: int,
    routing: dict[str, Any] | None,
    settings: Settings,
    reasoning_effort: str | None = None,
) -> Runnable:
    """A runnable bound to exactly one tool, forced - real tool-calling, not structured
    output. `with_structured_output` and `bind_tools` are two different invocation modes
    in langchain-openai and do not merge into one call, so this is kept separate from
    `build()` rather than added as an option to it. Used for exactly one turn shape: the
    exercise hand-off, on the turn a framework completes.

    Returns the model's raw `AIMessage` - `bind_tools` has no `include_raw`/`parsed` split
    of its own, so the caller reads `.tool_calls` directly.
    """
    extra_body = request_body(model, settings, routing, reasoning_effort)
    chat = _model(
        settings.openrouter_api_key,
        settings.openrouter_base_url,
        settings.llm_timeout_seconds,
        model,
        temperature,
        max_tokens,
        json.dumps(extra_body, sort_keys=True),
    )
    return chat.bind_tools([tool], tool_choice=tool.__name__)


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
