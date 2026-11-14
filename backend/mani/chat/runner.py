# ABOUTME: Runs a turn as read, think, write: a short transaction, the model call holding no connection, a short one.
# ABOUTME: The turn's steps run once to learn what to ask, and again with the reply to write it, if nothing changed.

from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field, replace
from typing import Any

import asyncpg

from mani.auth.jwt import Claims
from mani.chat import orchestrator, rewind
from mani.chat.greeting import STYLE_OPTIONS
from mani.db import llm_calls, pool, threads
from mani.db import messages as messages_db
from mani.errors import ErrorCategory, ServiceError
from mani.llm import client
from mani.models.rows import SupportStyle, Thread
from mani.one_at_a_time import one_at_a_time
from mani.prompts import cache

logger = logging.getLogger(__name__)

Steps = Callable[[asyncpg.Connection, "Model"], Awaitable[orchestrator.Turn]]


@dataclass(frozen=True)
class _Request:
    """What the turn asked the model, and the thread as it stood when it asked."""

    messages: list[dict[str, str]]
    schema: type
    kwargs: dict[str, Any]
    version: tuple
    # What goes out if the model fails, on a turn that must never go unanswered (a safety turn); None elsewhere.
    fallback: str | None = None


class _ModelNeeded(Exception):
    """Ends the read: the turn reached its model call. Raised inside the transaction, so it rolls back."""

    def __init__(self, request: _Request) -> None:
        super().__init__("the turn needs the model")
        self.request = request


@dataclass
class Model:
    """What a turn calls in place of client.complete. On the read it records the request and stops the pass;
    on the write it hands back the reply the model gave, once it has checked that the thread is as it was."""

    conn: asyncpg.Connection
    thread_id: uuid.UUID | str
    request: _Request | None = None
    call: client.Call | None = None
    _answered: bool = field(default=False, init=False)

    async def __call__(self, messages, schema, *, fallback: str | None = None, **kwargs) -> client.Call:
        version = await thread_version(self.conn, self.thread_id)
        if self.call is None:
            raise _ModelNeeded(_Request(messages, schema, kwargs, version, fallback))
        if self._answered:
            raise RuntimeError("a turn asked the model twice")
        self._answered = True
        # The thread is locked by now (orchestrator._lock_thread). A message that landed while the model
        # thought, or a reply asked for in another shape, means this reply answers a conversation that has moved.
        if version != self.request.version or schema.model_json_schema() != self.request.schema.model_json_schema():
            raise ServiceError(
                f"thread {self.thread_id} changed during the model call",
                ErrorCategory.CONFLICT,
                retryable=True,
                user_message="Mani is still answering your last message. Please try again.",
            )
        return replace(self.call, value=schema.model_validate(self.call.value.model_dump()))


async def thread_version(conn: asyncpg.Connection, thread_id: uuid.UUID | str) -> tuple:
    """How many messages the thread holds and which is the newest: any message written, edited away or
    replaced since changes it. What Mani has understood of them is not in it: the write rebuilds from that
    as it is then, so a reading that lands meanwhile is kept."""
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


async def run(claims: Claims, thread_id: uuid.UUID | str, steps: Steps) -> orchestrator.Turn:
    """Run a turn's steps with no connection held while the model thinks.

    Read: the steps run in a transaction up to the model call, which records what they ask and rolls back.
    A turn that never asks (a crisis, a style button, a duplicate) commits right there. Think: the model is
    called holding nothing. Write: the steps run again in a fresh transaction under the thread's lock, and
    are answered with that reply when the thread is unchanged; otherwise the turn is refused as a conflict."""
    try:
        async with pool.as_user(claims) as conn:
            return await steps(conn, Model(conn, thread_id))
    except _ModelNeeded as needed:
        request = needed.request
    try:
        call = await client.complete(request.messages, request.schema, **request.kwargs)
    except ServiceError:
        if request.fallback is None:
            raise
        # Someone who may not be safe gets words rather than an error: the write stores them as Mani's reply, read
        # as a reply that reports nothing, so the safety state stays where it was.
        logger.exception("model failed on a safety turn for thread %s; sending the fallback", thread_id)
        call = client.Call(
            value=request.schema.model_validate({"text": request.fallback}), model="fallback",
            usage=llm_calls.Usage(), latency_ms=0, call_id=None,
        )
    async with pool.as_user(claims) as conn:
        return await steps(conn, Model(conn, thread_id, request=request, call=call))


async def send(
    claims: Claims, thread_id: uuid.UUID | str, content: str, client_message_id: uuid.UUID | str | None = None
) -> orchestrator.Turn:
    """One message in, one reply out."""
    # Read before any connection is taken: a stale cache reloads on a connection of its own.
    config = await cache.load()

    async def steps(conn: asyncpg.Connection, model: Model) -> orchestrator.Turn:
        return await orchestrator.send(
            conn, claims, thread_id, content, client_message_id, ask=model, config=config
        )

    if client_message_id is None:
        return await run(claims, thread_id, steps)
    # The database's lock on the id cannot span the model call, so a retry arriving mid-call waits here and
    # then finds the stored turn, instead of paying for a second reply. One that reaches another instance pays
    # once more; the write still stores one turn.
    async with one_at_a_time(("send", claims.user_id, str(client_message_id))):
        return await run(claims, thread_id, steps)


async def start(
    claims: Claims, content: str, client_message_id: uuid.UUID | str | None, style: SupportStyle | None
) -> tuple[Thread, orchestrator.Turn]:
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
) -> tuple[Thread, orchestrator.Turn]:
    async with pool.as_user(claims) as conn:
        thread_id = (
            await messages_db.thread_of_client_message(conn, claims.user_id, client_message_id)
            if client_message_id is not None
            else None
        )
        created = thread_id is None
        if created:
            thread_id = (await orchestrator.start_thread(conn, claims)).id
    try:
        if created and style is not None:
            tap = next(option["label"] for option in STYLE_OPTIONS if option["style"] == style.value)
            await send(claims, thread_id, tap)
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
) -> orchestrator.Turn:
    """Replace the person's last message and Mani's reply with a turn on the new text. The read takes the turn
    back in a transaction that rolls back; the write takes it back again and runs the new text in one, so a
    failed edit leaves the original exchange in place."""
    config = await cache.load()

    async def steps(conn: asyncpg.Connection, model: Model) -> orchestrator.Turn:
        await rewind.undo_last_turn(conn, claims.user_id, thread_id, message_id)
        return await orchestrator.send(conn, claims, thread_id, content, ask=model, config=config)

    return await run(claims, thread_id, steps)
