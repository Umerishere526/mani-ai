# ABOUTME: The OpenRouter call - at most two requests, a real timeout, and a logged cost row each.
# ABOUTME: Structured output is parsed into a Pydantic model; anything else is an error.

from __future__ import annotations

import asyncio
import functools
import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

import openai
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.exceptions import OutputParserException
from langchain_openai import StreamChunkTimeoutError
from pydantic import BaseModel, ValidationError

from mani.config import Settings, get_settings
from mani.db import llm_calls
from mani.errors import ErrorCategory, ServiceError
from mani.llm import chain

logger = logging.getLogger(__name__)

DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 2048

# One retry, shared by a malformed reply, a provider that is briefly down, a call that sent
# nothing for too long and a chat call raced on a second host. Without it any of them loses the person's typed message entirely -
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
    # From the answering attempt's start to its first streamed chunk; None when none arrived.
    first_token_ms: int | None = None
    # The sentences the reply check rewrote or took out (mani/chat/check.py), for the turn's trace.
    checked: tuple[str, ...] = ()


# A provider that is briefly down or unreachable. APITimeoutError is a subclass of
# APIConnectionError and is excluded where this is caught: the full wait has already happened.
_TRANSIENT = (openai.InternalServerError, openai.APIConnectionError)
TRANSIENT_RETRY_DELAY_SECONDS = 1.0

# LangChain's words for a reply with no content and no refusal (a host that spent the call on reasoning). It raises a
# plain ValueError for it, so the message is the only mark; the client tests run the installed LangChain against an empty
# reply, so a version that words it differently fails there, not in a chat.
NO_CONTENT = "does not have a 'parsed' field nor a 'refusal' field"

_SCHEMA_FAILURES = (
    openai.LengthFinishReasonError,
    openai.ContentFilterFinishReasonError,
    ValidationError,
)


# Failures whose message quotes the reply itself: pydantic's carries `input_value=` excerpts, LangChain's
# parser the completion it could not parse. Only their type and where they failed are kept.
_QUOTES_THE_REPLY = (ValidationError, OutputParserException)
# Failures whose message carries the provider's response body, which can quote the person's own words (a moderation
# refusal's `flagged_input`). Only their type and status are kept.
_QUOTES_THEIR_WORDS = (openai.APIStatusError,)


def _described(failure: BaseException | None) -> str:
    """A failure as it may be stored and logged: what went wrong and where, never what the reply or they said."""
    if failure is None:
        return "empty"
    if isinstance(failure, ValidationError):
        return f"ValidationError: {[(e.get('type'), e.get('loc')) for e in failure.errors()]}"
    if isinstance(failure, _QUOTES_THE_REPLY):
        return type(failure).__name__
    if isinstance(failure, _QUOTES_THEIR_WORDS):
        host, own = _host_of(failure), _openrouters_own(failure)
        return (f"{type(failure).__name__}: {failure.status_code}" + (f" from {host}" if host else "")
                + (f" ({own})" if own else ""))
    return f"{type(failure).__name__}: {failure}"


def _openrouters_own(failure: openai.APIStatusError) -> str | None:
    """OpenRouter's own message for an error no provider raised: one with no metadata, which is where a provider's raw
    body (and anything it quotes of what they wrote) is carried. None otherwise."""
    error = failure.body.get("error") if isinstance(failure.body, dict) else None
    if not isinstance(error, dict) or "metadata" in error:
        return None
    message = error.get("message")
    return message if isinstance(message, str) and message else None


# OpenRouter refusing to pass a request on, with no provider involved: seen on 2026-11-25 as 23 of 25 calls in one
# minute failing, every call before and after answering. Nothing was billed, so one retry costs nothing.
RELAY_REFUSALS = ("Request path cannot be relayed",)


def _relay_refused(failure: openai.BadRequestError) -> bool:
    return _openrouters_own(failure) in RELAY_REFUSALS


def _host_of(failure: openai.APIStatusError) -> str | None:
    """The host OpenRouter names in an error's metadata, which quotes nothing anyone wrote; None when it names none."""
    error = failure.body.get("error") if isinstance(failure.body, dict) else None
    metadata = error.get("metadata") if isinstance(error, dict) else None
    host = metadata.get("provider_name") if isinstance(metadata, dict) else None
    return host if isinstance(host, str) and host else None


# The model calls this instance has in flight, made on first use in the running loop.
_slots: tuple[asyncio.AbstractEventLoop, int, asyncio.Semaphore] | None = None


@asynccontextmanager
async def _model_slot(settings: Settings) -> AsyncIterator[None]:
    """One of the instance's model call slots, or a quick retryable refusal when none frees up in time."""
    global _slots
    loop = asyncio.get_running_loop()
    if _slots is None or _slots[0] is not loop or _slots[1] != settings.model_calls_in_flight:
        _slots = (loop, settings.model_calls_in_flight, asyncio.Semaphore(settings.model_calls_in_flight))
    slots = _slots[2]
    try:
        await asyncio.wait_for(slots.acquire(), settings.model_slot_wait_seconds)
    except TimeoutError as exc:
        raise ServiceError(
            f"no model call slot free within {settings.model_slot_wait_seconds} s",
            ErrorCategory.RATE_LIMITED,
            retryable=True,
            user_message="Mani is busy right now. Please try again in a moment.",
        ) from exc
    try:
        yield
    finally:
        slots.release()


def _generation_id_of(exc: BaseException) -> str | None:
    """OpenRouter's id for a failed attempt, when the SDK kept the completion."""
    return getattr(getattr(exc, "completion", None), "id", None)


def _usage_of(exc: BaseException) -> llm_calls.Usage:
    """The tokens a failed attempt was billed for, and what it cost, when the SDK kept the completion."""
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
        # OpenRouter's own field; the SDK keeps fields it does not declare as attributes.
        cost_usd=getattr(usage, "cost", None),
    )


class _FirstChunk(AsyncCallbackHandler):
    """Notes when an attempt's first streamed chunk arrives. The structured stream hands back the reply whole at the
    end, so the model's own per-chunk callback is the only place the first one shows."""

    def __init__(self) -> None:
        self.at: float | None = None

    async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        if self.at is None:
            self.at = time.perf_counter()


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
                f"model returned a reply that does not fit the schema: {_described(exc)}",
                ErrorCategory.LLM_UNAVAILABLE,
                retryable=True,
                user_message="Mani had trouble responding. Please try again.",
            ),
            llm_calls.Outcome.SCHEMA_INVALID,
        )
    return (
        ServiceError(
            f"provider call failed: {_described(exc)}",
            ErrorCategory.LLM_UNAVAILABLE,
            retryable=True,
            user_message="Mani had trouble responding. Please try again.",
        ),
        llm_calls.Outcome.PROVIDER_ERROR,
    )


def _apply_model_quirks(messages: list[dict[str, str]], model: str) -> list[dict[str, str]]:
    """Per-model workarounds, kept here rather than in the conversation logic.

    Qwen models reason inline unless told not to, which lands `<think>` blocks in a
    reply meant for a person. Handled here, so no chat code needs to know which model it talks to.
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
    second provider. One provider request, plus at most one more: after a reply that does not
    parse, a silence, a provider blip or a relay refusal, or beside the first when a chat call
    has sent nothing for `chat_hedge_seconds` and another host is allowed. A chat call's second
    request goes to the other hosts, and the first to answer is the reply. Each request is
    billed and recorded on its own row, a cancelled one included.
    """
    from mani.db import pool

    pool.refuse_while_holding("a model call was made")
    settings = settings or get_settings()
    if not settings.openrouter_api_key:
        raise ServiceError(
            "OPENROUTER_API_KEY is not set",
            ErrorCategory.CONFIG_ERROR,
            user_message="Mani is not available right now.",
        )

    chat = purpose is llm_calls.Purpose.CHAT
    second_routing = _other_hosts(routing, settings) if chat else None

    def build(routing: dict[str, Any] | None, session: str | None):
        return chain.build(
            schema,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            reasoning_effort=reasoning_effort,
            routing=routing,
            settings=settings,
            chunk_timeout=settings.chat_first_token_seconds if chat else settings.llm_timeout_seconds,
            # Only the reply the person waits on pays for the faster tier.
            priority=chat and settings.openrouter_chat_service_tier == "priority",
            session=session,
        )

    # One key per thread and purpose: chat may use the priority endpoint and the other calls may not,
    # so a key they shared would pin the conversation to a different endpoint after every call, and
    # their prompts never share a cached prefix anyway (each starts from its own reply schema).
    runnable = build(routing, f"{thread_id}:{purpose.value}" if thread_id else None)
    row = functools.partial(
        _record, purpose=purpose, model=model, user_id=user_id, thread_id=thread_id,
        prompt_version_id=prompt_version_id,
    )

    async with _model_slot(settings):
        messages = _apply_model_quirks(messages, model)
        began = time.perf_counter()
        running: dict[asyncio.Task[_Attempt], _Attempt] = {}

        def start(number: int) -> None:
            # The second request of a chat call goes to the other hosts, with no sticky keys, so a host that won
            # one race never pins the conversation away from the first host's warm cache.
            attempt = _Attempt(number, runnable if number == 1 or second_routing is None
                               else build(second_routing, None))
            # A chat reply has a deadline for the whole call; the per read timeout alone let one run for 102 s. The
            # background calls (summaries) keep only that. A second request gets the deadline or what is left of
            # the budget, whichever is shorter.
            deadline = (min(settings.chat_deadline_seconds, settings.chat_budget_seconds - (time.perf_counter() - began))
                        if chat else None)
            running[asyncio.create_task(_run(attempt, messages, deadline))] = attempt

        start(1)
        started = 1
        hedge_at = began + settings.chat_hedge_seconds if second_routing is not None else None
        last: _Attempt | None = None
        try:
            while running:
                wait = max(0.0, hedge_at - time.perf_counter()) if hedge_at is not None and started == 1 else None
                done, _ = await asyncio.wait(running, timeout=wait, return_when=asyncio.FIRST_COMPLETED)
                if not done:
                    # Nothing yet from the first host: a slow provider, seen at 20 to 27 s (2026-11-25). The other
                    # host starts beside it, and whichever answers first is the reply.
                    hedge_at = None
                    if running[next(iter(running))].first_chunk.at is None:
                        start(2)
                        started = 2
                    continue
                # A failure finished in the same moment as an answer is recorded before the answer returns.
                for task in sorted(done, key=lambda t: running[t].answered):
                    attempt = running.pop(task)
                    if attempt.answered:
                        await _settle_losers(running, attempt, row)
                        call_id = await row(
                            outcome=llm_calls.Outcome.OK, usage=attempt.usage, latency_ms=attempt.latency_ms(),
                            error_message=None, generation_id=attempt.generation_id,
                        )
                        return Call(
                            value=attempt.parsed, model=model, usage=attempt.usage, latency_ms=attempt.latency_ms(),
                            call_id=call_id, first_token_ms=attempt.first_token_ms(),
                        )
                    retrying = started == 1 and attempt.worth_retrying()
                    await _record_failed(row, attempt, retrying=retrying)
                    last = attempt
                    if retrying:
                        if attempt.pause_before_retry():
                            await asyncio.sleep(TRANSIENT_RETRY_DELAY_SECONDS)
                        start(2)
                        started = 2
        finally:
            for task in running:
                task.cancel()

        assert last is not None
        error = _final_error(last, started)
        # The cause rides along on the log and the error report, so one that quotes the reply or them is dropped.
        quoting = last.unparsed or isinstance(last.failure, _QUOTES_THE_REPLY + _QUOTES_THEIR_WORDS)
        raise error from (None if quoting else last.failure)


def _other_hosts(routing: dict[str, Any] | None, settings: Settings) -> dict[str, Any] | None:
    """Where a chat call's second request goes: the hosts after the first in `only`. None when only one is allowed,
    and the second request then goes where the first did."""
    hosts = (routing or {}).get("only", settings.openrouter_providers)
    return {**(routing or {}), "only": hosts[1:]} if len(hosts) > 1 else None


@dataclass
class _Attempt:
    """One request of a call: what it was sent to, when it started, and how it ended."""

    number: int
    runnable: Any
    started: float = field(default_factory=time.perf_counter)
    ended: float | None = None
    first_chunk: _FirstChunk = field(default_factory=_FirstChunk)
    parsed: BaseModel | None = None
    # What it raised, or the reply's own parsing error. None with no parsed reply is an empty one.
    failure: BaseException | None = None
    # A reply came back and did not parse: malformed, cut off, filtered or empty.
    unparsed: bool = False
    usage: llm_calls.Usage = field(default_factory=llm_calls.Usage)
    generation_id: str | None = None

    @property
    def answered(self) -> bool:
        return self.parsed is not None and self.failure is None

    def latency_ms(self) -> int:
        return int(((self.ended or time.perf_counter()) - self.started) * 1000)

    def first_token_ms(self) -> int | None:
        """From the attempt's start to its first streamed chunk; None when none arrived."""
        return int((self.first_chunk.at - self.started) * 1000) if self.first_chunk.at is not None else None

    def worth_retrying(self) -> bool:
        """A reply that did not parse, a call that sent nothing for too long, a provider briefly down and OpenRouter
        refusing to relay get one more request. A full read timeout already cost the whole wait, and anything else
        would fail again."""
        failure = self.failure
        if self.unparsed or isinstance(failure, StreamChunkTimeoutError):
            return True
        if isinstance(failure, _TRANSIENT):
            return not isinstance(failure, openai.APITimeoutError)
        return isinstance(failure, openai.BadRequestError) and _relay_refused(failure)

    def pause_before_retry(self) -> bool:
        """A provider blip and a relay refusal billed nothing, and a moment's pause lets them clear."""
        return isinstance(self.failure, (*_TRANSIENT, openai.BadRequestError))


async def _run(attempt: _Attempt, messages: list[dict[str, str]], deadline: float | None) -> _Attempt:
    """One request, streamed and folded into one reply; every way it can end is kept on the attempt, never raised."""
    stream = _folded(attempt.runnable.astream(messages, {"callbacks": [attempt.first_chunk]}))
    try:
        result = await (stream if deadline is None else asyncio.wait_for(stream, deadline))
    except _SCHEMA_FAILURES as exc:
        # With a response_format, LangChain calls the SDK's parse(), which validates inside the model step: a reply
        # cut off at max_tokens, stopped by a content filter or not matching the schema raises here and never
        # reaches parsing_error. It is the same failure, so it gets the same one retry.
        attempt.failure, attempt.unparsed = exc, True
        attempt.usage, attempt.generation_id = _usage_of(exc), _generation_id_of(exc)
    except ValueError as exc:
        # An empty reply is a reply that does not parse. LangChain keeps no completion on this error, so the
        # attempt's tokens and id are not known.
        attempt.failure, attempt.unparsed = exc, NO_CONTENT in str(exc)
    except Exception as exc:
        attempt.failure = exc
    else:
        attempt.usage = chain.usage_from(result.get("raw"))
        attempt.generation_id = chain.generation_id_from(result.get("raw"))
        attempt.parsed, attempt.failure = result.get("parsed"), result.get("parsing_error")
        attempt.unparsed = not attempt.answered
    attempt.ended = time.perf_counter()
    return attempt


async def _record_failed(row, attempt: _Attempt, *, retrying: bool) -> None:
    """A failed request's own row: a schema failure still cost a real provider call, so it is never absorbed into
    whichever request answers, and its latency is its own, not the requests and the pause before it."""
    outcome = llm_calls.Outcome.SCHEMA_INVALID if attempt.unparsed else _as_service_error(attempt.failure)[1]
    await row(
        outcome=outcome, usage=attempt.usage, latency_ms=attempt.latency_ms(), generation_id=attempt.generation_id,
        error_message=(f"attempt {attempt.number}/{MAX_SCHEMA_ATTEMPTS}{', retrying' if retrying else ''}: "
                       f"{_described(attempt.failure)}"),
    )


async def _settle_losers(running: dict[asyncio.Task[_Attempt], _Attempt], winner: _Attempt, row) -> None:
    """Stops the requests still running once one has answered, and records each: a cancelled one as a timeout of
    its own (it was slower, and it is probably billed), one that finished meanwhile as what it was."""
    for task, attempt in list(running.items()):
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        del running[task]
        note = f"attempt {attempt.number}/{MAX_SCHEMA_ATTEMPTS}: not used, attempt {winner.number} answered first"
        if task.cancelled():
            await row(outcome=llm_calls.Outcome.TIMEOUT, usage=llm_calls.Usage(), latency_ms=attempt.latency_ms(),
                      error_message=f"{note} and this one was cancelled", generation_id=None)
        else:
            outcome = (llm_calls.Outcome.OK if attempt.answered else llm_calls.Outcome.SCHEMA_INVALID
                       if attempt.unparsed else _as_service_error(attempt.failure)[1])
            await row(outcome=outcome, usage=attempt.usage, latency_ms=attempt.latency_ms(),
                      error_message=note, generation_id=attempt.generation_id)


def _final_error(last: _Attempt, attempts: int) -> ServiceError:
    """What the caller is told when no request answered: the last one to fail decides."""
    if last.unparsed:
        return ServiceError(
            f"model returned no parseable reply after {attempts} attempts: {_described(last.failure)}",
            ErrorCategory.LLM_UNAVAILABLE,
            retryable=True,
            user_message="Mani had trouble responding. Please try again.",
        )
    return _as_service_error(last.failure)[0]
