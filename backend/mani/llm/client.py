# ABOUTME: The OpenRouter call - one attempt, a real timeout, and a logged cost row.
# ABOUTME: Structured output is parsed into a Pydantic model; anything else is an error.

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import openai
from langchain_openai import StreamChunkTimeoutError
from pydantic import BaseModel, ValidationError

from mani.config import Settings, get_settings
from mani.db import llm_calls
from mani.errors import ErrorCategory, ServiceError
from mani.llm import chain

logger = logging.getLogger(__name__)

DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 2048

# One retry, shared by a malformed reply, a provider that is briefly down and a call that sent
# nothing for too long. Without it any of them loses the person's typed message entirely -
# complete() is called before the turn writes anything, so a raise here leaves nothing in the
# thread to show for the turn.
MAX_SCHEMA_ATTEMPTS = 2


@dataclass(frozen=True)
class Call[T: BaseModel]:
    """A completed model call: what came back, and what it cost."""

    value: T
    model: str
    usage: llm_calls.Usage
    latency_ms: int
    call_id: uuid.UUID | None


# A provider that is briefly down or unreachable. APITimeoutError is a subclass of
# APIConnectionError and is excluded where this is caught: the full wait has already happened.
_TRANSIENT = (openai.InternalServerError, openai.APIConnectionError)
TRANSIENT_RETRY_DELAY_SECONDS = 1.0

_SCHEMA_FAILURES = (
    openai.LengthFinishReasonError,
    openai.ContentFilterFinishReasonError,
    ValidationError,
)


def _generation_id_of(exc: BaseException) -> str | None:
    """OpenRouter's id for a failed attempt, when the SDK kept the completion."""
    return getattr(getattr(exc, "completion", None), "id", None)


def _usage_of(exc: BaseException) -> llm_calls.Usage:
    """The tokens a failed attempt was billed for, when the SDK kept the completion."""
    usage = getattr(getattr(exc, "completion", None), "usage", None)
    if usage is None:
        return llm_calls.Usage()
    return llm_calls.Usage(
        input_tokens=usage.prompt_tokens or 0,
        output_tokens=usage.completion_tokens or 0,
        cached_input_tokens=getattr(usage.prompt_tokens_details, "cached_tokens", None) or 0,
        reasoning_tokens=(
            getattr(usage.completion_tokens_details, "reasoning_tokens", None) or 0
        ),
    )


async def _folded(stream) -> dict:
    """The one reply a structured stream amounts to: its pieces, raw, parsing_error and parsed, each
    arriving once, folded into the dict the call used to return whole."""
    result: dict = {}
    async for piece in stream:
        result.update(piece)
    return result


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
    if isinstance(exc, (openai.APITimeoutError, TimeoutError)):
        return (
            ServiceError(
                f"provider timed out: {exc or 'past the chat deadline'}",
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
    generation_id: str | None = None,
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
                generation_id=generation_id,
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
    reasoning_effort: str | None = None,
    routing: dict[str, Any] | None = None,
    user_id: uuid.UUID | str | None = None,
    thread_id: uuid.UUID | str | None = None,
    prompt_version_id: uuid.UUID | str | None = None,
    settings: Settings | None = None,
) -> Call[T]:
    """Ask the model for one structured reply.

    OpenRouter is the only provider. LangChain composes the call and parses the reply into
    the schema; the base_url points at OpenRouter, so it is one protocol and one bill, not a
    second provider. One provider call, plus at most one retry when the reply does not
    parse - each attempt billed and recorded on its own row.
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
        reasoning_effort=reasoning_effort,
        routing=routing,
        settings=settings,
        chunk_timeout=(
            settings.chat_first_token_seconds
            if purpose is llm_calls.Purpose.CHAT else settings.llm_timeout_seconds
        ),
    )

    messages = _apply_model_quirks(messages, model)

    usage = llm_calls.Usage()
    generation_id: str | None = None
    try:
        parsed = None
        for attempt in range(1, MAX_SCHEMA_ATTEMPTS + 1):
            # Reset per attempt, so an attempt that raises is never recorded with the tokens
            # of the one before it, and each row's latency is that attempt's own time, not
            # the attempts and the retry pause before it.
            usage = llm_calls.Usage()
            generation_id = None
            started = time.perf_counter()
            try:
                # A chat reply has a deadline for the whole call; the per read timeout alone let one
                # run for 102 s. The background calls (summaries, the memory fold) keep only that.
                if purpose is llm_calls.Purpose.CHAT:
                    result = await asyncio.wait_for(_folded(runnable.astream(messages)), settings.chat_deadline_seconds)
                else:
                    result = await _folded(runnable.astream(messages))
            except StreamChunkTimeoutError as exc:
                if attempt == MAX_SCHEMA_ATTEMPTS:
                    raise
                # Nothing came for the whole wait: a reasoning model thinking far longer than its
                # neighbours. The cut attempt gets its own row, and one more try usually answers
                # sooner than waiting out the first (2026-10-21).
                await _record(
                    purpose=purpose, model=model, outcome=llm_calls.Outcome.TIMEOUT,
                    usage=llm_calls.Usage(), latency_ms=int((time.perf_counter() - started) * 1000),
                    user_id=user_id, thread_id=thread_id, prompt_version_id=prompt_version_id,
                    error_message=f"attempt {attempt}/{MAX_SCHEMA_ATTEMPTS}, retrying: {exc}",
                )
                continue
            except _TRANSIENT as exc:
                if isinstance(exc, openai.APITimeoutError) or attempt == MAX_SCHEMA_ATTEMPTS:
                    raise
                # The provider was briefly unavailable - seen live, 1 call in 265, from one
                # upstream. It billed nothing, so one retry costs nothing and
                # keeps a blip from reaching the person as an error. Recorded as its own row.
                await _record(
                    purpose=purpose, model=model, outcome=llm_calls.Outcome.PROVIDER_ERROR,
                    usage=llm_calls.Usage(), latency_ms=int((time.perf_counter() - started) * 1000),
                    user_id=user_id, thread_id=thread_id, prompt_version_id=prompt_version_id,
                    error_message=f"attempt {attempt}/{MAX_SCHEMA_ATTEMPTS}, retrying: {exc}",
                )
                await asyncio.sleep(TRANSIENT_RETRY_DELAY_SECONDS)
                continue
            except _SCHEMA_FAILURES as exc:
                # With a response_format, LangChain calls the SDK's parse(), which validates
                # inside the model step: a reply cut off at max_tokens, stopped by a content
                # filter or not matching the schema raises here and never reaches
                # parsing_error. It is the same failure, so it gets the same one retry.
                result = {"raw": None, "parsed": None, "parsing_error": exc}
                usage = _usage_of(exc)
                generation_id = _generation_id_of(exc)
            else:
                usage = chain.usage_from(result.get("raw"))
                generation_id = chain.generation_id_from(result.get("raw"))
            parsed = result.get("parsed")
            failure = result.get("parsing_error")
            if failure is None and parsed is not None:
                break

            # A schema failure still cost a real provider call, so it gets its own row
            # rather than being silently absorbed into whichever attempt finally works -
            # both a retried success and an exhausted retry are fully accounted for.
            latency_ms = int((time.perf_counter() - started) * 1000)
            await _record(
                purpose=purpose, model=model, outcome=llm_calls.Outcome.SCHEMA_INVALID,
                usage=usage, latency_ms=latency_ms, user_id=user_id, thread_id=thread_id,
                prompt_version_id=prompt_version_id,
                error_message=f"attempt {attempt}/{MAX_SCHEMA_ATTEMPTS}: {failure or 'empty'}",
                generation_id=generation_id,
            )
            if attempt == MAX_SCHEMA_ATTEMPTS:
                raise ServiceError(
                    f"model returned no parseable reply after {MAX_SCHEMA_ATTEMPTS} "
                    f"attempts: {failure or 'empty'}",
                    ErrorCategory.LLM_UNAVAILABLE,
                    retryable=True,
                    user_message="Mani had trouble responding. Please try again.",
                )
    except ServiceError:
        # Already recorded above, per attempt - re-raising bare avoids a second row for
        # the same failure and keeps this from falling through to the generic handler
        # below, which would call _as_service_error() on an error that already is one.
        raise
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        error, outcome = _as_service_error(exc)
        await _record(
            purpose=purpose, model=model, outcome=outcome, usage=usage,
            latency_ms=latency_ms, user_id=user_id, thread_id=thread_id,
            prompt_version_id=prompt_version_id, error_message=str(exc),
            generation_id=generation_id,
        )
        raise error from exc

    latency_ms = int((time.perf_counter() - started) * 1000)
    call_id = await _record(
        purpose=purpose, model=model, outcome=llm_calls.Outcome.OK, usage=usage,
        latency_ms=latency_ms, user_id=user_id, thread_id=thread_id,
        prompt_version_id=prompt_version_id, error_message=None, generation_id=generation_id,
    )
    return Call(
        value=parsed, model=model, usage=usage, latency_ms=latency_ms, call_id=call_id
    )
