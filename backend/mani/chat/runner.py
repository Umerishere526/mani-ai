# ABOUTME: Runs a turn as read, think, write: a short transaction, the model call holding no connection, a short one.
# ABOUTME: The turn's steps run once to learn what to ask, and again with the reply to write it, if nothing changed.

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field, replace
from typing import Any

import asyncpg

from mani.auth.jwt import Claims
from mani.chat import check, rewind, turn as chat_turn
from mani.chat.greeting import style_label
from mani.chat.reply import TurnReply
from mani.config import get_settings
from mani.db import pool, threads
from mani.db import messages as messages_db
from mani.errors import ErrorCategory, ServiceError
from mani.llm import client
from mani.models.rows import SupportStyle, Thread
from mani.one_at_a_time import one_at_a_time
from mani.prompts import cache

logger = logging.getLogger(__name__)

Steps = Callable[[asyncpg.Connection, "Model"], Awaitable[chat_turn.Turn]]


@dataclass(frozen=True)
class _Request:
    """What the turn asked the model, and the thread as it stood when it asked."""

    messages: list[dict[str, str]]
    schema: type
    kwargs: dict[str, Any]
    version: tuple


class _ModelNeeded(Exception):
    """Ends the read: the turn reached its model call. Raised inside the transaction, so it rolls back."""

    def __init__(self, request: _Request) -> None:
        super().__init__("the turn needs the model")
        self.request = request


@dataclass
class Model:
    """What a turn calls in place of client.complete. On the read it records the request and stops the pass;
    on the write it hands back the reply the model gave, once it has checked that the thread is as it was, or None
    when no host answered."""

    conn: asyncpg.Connection
    thread_id: uuid.UUID | str
    request: _Request | None = None
    call: client.Call | None = None
    _answered: bool = field(default=False, init=False)

    async def __call__(self, messages, schema, **kwargs) -> client.Call | None:
        version = await thread_version(self.conn, self.thread_id)
        if self.request is None:
            raise _ModelNeeded(_Request(messages, schema, kwargs, version))
        if self._answered:
            raise RuntimeError("a turn asked the model twice")
        self._answered = True
        # The thread is locked by now (threads.lock). A message that landed while the model
        # thought, or a reply asked for in another shape, means this reply answers a conversation that has moved.
        if version != self.request.version or schema.model_json_schema() != self.request.schema.model_json_schema():
            raise ServiceError(
                f"thread {self.thread_id} changed during the model call",
                ErrorCategory.CONFLICT,
                retryable=True,
                user_message="Mani is still answering your last message. Please try again.",
            )
        if self.call is None:
            return None
        return replace(self.call, value=schema.model_validate(self.call.value.model_dump()))


async def thread_version(conn: asyncpg.Connection, thread_id: uuid.UUID | str) -> tuple:
    """How many messages the thread holds and which is the newest: any message written, edited away or
    replaced since changes it."""
    row = await conn.fetchrow(
        """
        select t.message_count,
               (select m.id from public.messages m where m.thread_id = t.id
                order by m.created_at desc, m.id desc limit 1) as newest
        from public.threads t where t.id = $1
        """,
        thread_id,
    )
    return (row["message_count"], row["newest"]) if row else (None, None)


def _ms_since(began: float) -> int:
    return int((time.perf_counter() - began) * 1000)


def _timed(turn: chat_turn.Turn, **timings: int) -> chat_turn.Turn:
    """The turn with its stage timings added to the trace it already carries; a turn with no trace records none."""
    return replace(turn, trace={**turn.trace, **timings}) if turn.trace else turn


async def run(
    claims: Claims, thread_id: uuid.UUID | str, steps: Steps, *, answer_failure: bool,
) -> chat_turn.Turn:
    """Run a turn's steps with no connection held while the model thinks.

    Read: the steps run in a transaction up to the model call, which records what they ask and rolls back.
    A turn that never asks (a style button, a lead-in button or the example, a duplicate) commits right there. Think: the model is
    called holding nothing. Write: the steps run again in a fresh transaction under the thread's lock, and
    are answered with that reply when the thread is unchanged; otherwise the turn is refused as a conflict.
    `answer_failure`: when no host answers, the write still runs and the turn sends its fixed words; otherwise the
    failure is raised and nothing is written.
    The trace gets each pass's milliseconds, connection wait included, and `total_ms` from the read's start to the
    write's commit."""
    began = time.perf_counter()
    try:
        async with pool.as_user(claims) as conn:
            turn = await steps(conn, Model(conn, thread_id))
    except _ModelNeeded as needed:
        request = needed.request
    else:
        took = _ms_since(began)
        return _timed(turn, read_ms=took, total_ms=took)
    read_ms = _ms_since(began)
    try:
        call = await client.complete(request.messages, request.schema, **request.kwargs)
    except ServiceError:
        if not answer_failure:
            raise
        logger.exception("model failed for thread %s; the turn sends its fixed words", thread_id)
        call = None
    if call is not None and isinstance(call.value, TurnReply):
        theirs = [m["content"] for m in request.messages if m.get("role") == "user"]
        call, changed = await check.checked(call, said=theirs[-1] if theirs else "", everything="\n".join(theirs),
                                            kwargs=request.kwargs, settings=get_settings())
        call = replace(call, checked=tuple(changed))
    writing = time.perf_counter()
    async with pool.as_user(claims) as conn:
        turn = await steps(conn, Model(conn, thread_id, request=request, call=call))
    return _timed(turn, read_ms=read_ms, write_ms=_ms_since(writing), total_ms=_ms_since(began))


async def send(
    claims: Claims, thread_id: uuid.UUID | str, content: str, client_message_id: uuid.UUID | str | None = None
) -> chat_turn.Turn:
    """One message in, one reply out."""
    # Read before any connection is taken: a stale cache reloads on a connection of its own.
    config = await cache.load()

    async def steps(conn: asyncpg.Connection, model: Model) -> chat_turn.Turn:
        return await chat_turn.send(
            conn, claims, thread_id, content, client_message_id, ask=model, config=config, answer_failure=True
        )

    if client_message_id is None:
        return await run(claims, thread_id, steps, answer_failure=True)
    # The database's lock on the id cannot span the model call, so a retry arriving mid-call waits here and
    # then finds the stored turn, instead of paying for a second reply. One that reaches another instance pays
    # once more; the write still stores one turn.
    async with one_at_a_time(("send", claims.user_id, str(client_message_id))):
        return await run(claims, thread_id, steps, answer_failure=True)


async def start(
    claims: Claims, content: str, client_message_id: uuid.UUID | str | None, style: SupportStyle | None
) -> tuple[Thread, chat_turn.Turn]:
    """A person's first message: the conversation it opens is created with it, holding Mani's greeting and, when they
    tapped one, the style they chose, and then the message runs as the turn it is.

    A retry with the same `client_message_id` goes to the conversation its first try made and gets that turn back.
    A start that fails leaves no conversation behind: the one it created is deleted.
    """
    if client_message_id is None:
        return await _start(claims, content, None, style)
    # A retry arriving while the first try waits on the model would find no conversation yet and make a second, so
    # it waits here for the first to finish, as a retried send does.
    async with one_at_a_time(("start", claims.user_id, str(client_message_id))):
        return await _start(claims, content, client_message_id, style)


async def _start(
    claims: Claims, content: str, client_message_id: uuid.UUID | str | None, style: SupportStyle | None
) -> tuple[Thread, chat_turn.Turn]:
    async with pool.as_user(claims) as conn:
        thread_id = (
            await messages_db.thread_of_client_message(conn, claims.user_id, client_message_id)
            if client_message_id is not None
            else None
        )
        created = thread_id is None
        if created:
            thread_id = (await chat_turn.start_thread(conn, claims)).id
    try:
        if created and style is not None:
            await send(claims, thread_id, style_label(style.value))
        turn = await send(claims, thread_id, content, client_message_id)
    except Exception:
        if created:
            async with pool.as_user(claims) as conn:
                await threads.soft_delete(conn, thread_id, claims.user_id)
        raise
    async with pool.as_user(claims) as conn:
        thread = await threads.get(conn, thread_id, claims.user_id)
    if thread is None:
        raise ServiceError(
            f"thread {thread_id} not found for user {claims.user_id}",
            ErrorCategory.NOT_FOUND,
            user_message="That conversation is not available.",
        )
    return thread, turn


async def edit(
    claims: Claims, thread_id: uuid.UUID | str, message_id: uuid.UUID | str, content: str
) -> chat_turn.Turn:
    """Replace the person's last message and Mani's reply with a turn on the new text. The read takes the turn
    back in a transaction that rolls back; the write takes it back again and runs the new text in one, so a
    failed edit, the model's included, leaves the original exchange in place."""
    config = await cache.load()

    async def steps(conn: asyncpg.Connection, model: Model) -> chat_turn.Turn:
        await rewind.undo_last_turn(conn, claims.user_id, thread_id, message_id)
        return await chat_turn.send(conn, claims, thread_id, content, ask=model, config=config, answer_failure=False)

    return await run(claims, thread_id, steps, answer_failure=False)
