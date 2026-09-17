# ABOUTME: The OpenRouter call - one attempt, a real timeout, and a logged cost row.
# ABOUTME: Structured output is parsed into a Pydantic model; anything else is an error.

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any

import openai
from pydantic import BaseModel, ValidationError

from mani.config import Settings, get_settings
from mani.db import llm_calls
from mani.errors import ErrorCategory, ServiceError
from mani.llm import chain

logger = logging.getLogger(__name__)

DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 2048


@dataclass(frozen=True)
class Call[T: BaseModel]:
    """A completed model call: what came back, and what it cost."""

    value: T
    model: str
    usage: llm_calls.Usage
    latency_ms: int
    call_id: uuid.UUID | None


def _as_service_error(exc: Exception) -> tuple[ServiceError, llm_calls.Outcome]:
    if isinstance(exc, openai.RateLimitError):
        return (
            ServiceError(
                f"provider rate limited: {exc}",
                ErrorCategory.RATE_LIMITED,
                retryable=True,
                user_message="Mani is busy right now. Please try again in a moment.",
            ),
            llm_calls.Outcome.PROVIDER_ERROR,
        )
    if isinstance(exc, openai.APITimeoutError):
        return (
            ServiceError(
                f"provider timed out: {exc}",
                ErrorCategory.LLM_TIMEOUT,
                retryable=True,
                user_message="Mani took too long to answer. Please try again.",
            ),
            llm_calls.Outcome.TIMEOUT,
        )
    if isinstance(exc, ValidationError):
        return (
            ServiceError(
                f"model returned a reply that does not fit the schema: {exc}",
                ErrorCategory.LLM_UNAVAILABLE,
                retryable=True,
                user_message="Mani had trouble responding. Please try again.",
            ),
            llm_calls.Outcome.SCHEMA_INVALID,
        )
    return (
        ServiceError(
            f"provider call failed: {exc}",
            ErrorCategory.LLM_UNAVAILABLE,
            retryable=True,
            user_message="Mani had trouble responding. Please try again.",
        ),
        llm_calls.Outcome.PROVIDER_ERROR,
    )


def _apply_model_quirks(messages: list[dict[str, str]], model: str) -> list[dict[str, str]]:
    """Per-model workarounds, kept here rather than in the conversation logic.

    Qwen models reason inline unless told not to, which lands `<think>` blocks in a
    reply meant for a person. The reference sniffed the model id from inside the chat
    orchestrator and edited the user's own message there.
    """
    if "qwen" not in model.lower() or not messages:
        return messages
    tail = messages[-1]
    if tail.get("role") != "user":
        return messages
    return messages[:-1] + [tail | {"content": f"{tail['content']} /no_think"}]


async def _record(
    *,
    purpose: llm_calls.Purpose,
    model: str,
    outcome: llm_calls.Outcome,
    usage: llm_calls.Usage,
    latency_ms: int,
    user_id: uuid.UUID | str | None,
    thread_id: uuid.UUID | str | None,
    prompt_version_id: uuid.UUID | str | None,
    error_message: str | None,
) -> uuid.UUID | None:
    """Write the cost row for a call, successful or not.

    Done here rather than at each call site so it cannot be forgotten - usage previously
    went to a debug log and was gone by the time anyone asked what a turn cost. It takes
    its own admin connection because admin.llm_calls is deliberately unreadable by users,
    and it never fails a turn that otherwise succeeded.
    """
    from mani.db import pool

    try:
        async with pool.as_admin() as conn:
            return await llm_calls.record(
                conn,
                purpose=purpose,
                model=model,
                outcome=outcome,
                usage=usage,
                latency_ms=latency_ms,
                user_id=user_id,
                thread_id=thread_id,
                prompt_version_id=prompt_version_id,
                error_message=error_message,
            )
    except Exception:
        logger.exception("failed to record llm call")
        return None


async def complete[T: BaseModel](
    messages: list[dict[str, str]],
    schema: type[T],
    *,
    model: str,
    purpose: llm_calls.Purpose,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    routing: dict[str, Any] | None = None,
    user_id: uuid.UUID | str | None = None,
    thread_id: uuid.UUID | str | None = None,
    prompt_version_id: uuid.UUID | str | None = None,
    settings: Settings | None = None,
) -> Call[T]:
    """Ask the model for one structured reply.

    OpenRouter is the only provider. LangChain composes the call and parses the reply into
    the schema; the base_url points at OpenRouter, so it is one protocol and one bill, not a
    second provider. Exactly one provider call happens here, which is the whole design.
    """
    settings = settings or get_settings()
    if not settings.openrouter_api_key:
        raise ServiceError(
            "OPENROUTER_API_KEY is not set",
            ErrorCategory.CONFIG_ERROR,
            user_message="Mani is not available right now.",
        )

    runnable = chain.build(
        schema,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        routing=routing,
        settings=settings,
    )

    messages = _apply_model_quirks(messages, model)

    started = time.perf_counter()
    usage = llm_calls.Usage()
    try:
        result = await runnable.ainvoke(messages)
        usage = chain.usage_from(result.get("raw"))
        parsed = result.get("parsed")
        failure = result.get("parsing_error")
        if failure is not None or parsed is None:
            raise ServiceError(
                f"model returned no parseable reply: {failure or 'empty'}",
                ErrorCategory.LLM_UNAVAILABLE,
                retryable=True,
                user_message="Mani had trouble responding. Please try again.",
            )
    except ServiceError as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        await _record(
            purpose=purpose, model=model, outcome=llm_calls.Outcome.SCHEMA_INVALID,
            usage=usage, latency_ms=latency_ms, user_id=user_id, thread_id=thread_id,
            prompt_version_id=prompt_version_id, error_message=str(exc),
        )
        raise
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        error, outcome = _as_service_error(exc)
        await _record(
            purpose=purpose, model=model, outcome=outcome, usage=usage,
            latency_ms=latency_ms, user_id=user_id, thread_id=thread_id,
            prompt_version_id=prompt_version_id, error_message=str(exc),
        )
        raise error from exc

    latency_ms = int((time.perf_counter() - started) * 1000)
    call_id = await _record(
        purpose=purpose, model=model, outcome=llm_calls.Outcome.OK, usage=usage,
        latency_ms=latency_ms, user_id=user_id, thread_id=thread_id,
        prompt_version_id=prompt_version_id, error_message=None,
    )
    return Call(
        value=parsed, model=model, usage=usage, latency_ms=latency_ms, call_id=call_id
    )
