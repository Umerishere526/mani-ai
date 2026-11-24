# ABOUTME: Helpers for whole-turn tests: a scripted model that serves the turn's reply and counts its calls, the test
# ABOUTME: person, and the reads a test makes of what a turn stored. Pytest fixtures live in conftest.py beside it.

from __future__ import annotations

import uuid

import asyncpg

from mani.auth.jwt import Claims
from mani.chat import runner
from mani.chat.reply import Safety, TurnReply
from mani.config import get_settings
from mani.db import llm_calls, profiles, threads
from mani.llm import client

ALICE = uuid.UUID("a0000000-0000-4000-8000-0000000000d1")


def claims_for(user_id: uuid.UUID) -> Claims:
    return Claims.acting_as(user_id)


def said(text: str, *, level: str = "none", notes: str = "", **fields) -> TurnReply:
    """A reply as the model would fill it; `safety` may be passed whole instead of `level`."""
    safety = fields.pop("safety", None) or Safety(level=level)
    return TurnReply(text=text, safety=safety, notes=notes, **fields)


class ScriptedModel:
    """A model that answers from a script, in order, and keeps what each call was sent."""

    def __init__(self, *replies: TurnReply) -> None:
        self._replies = list(replies)
        self.calls = 0
        self.sent: list[list[dict]] = []
        self.kwargs: dict = {}

    @property
    def last_messages(self) -> list[dict] | None:
        return self.sent[-1] if self.sent else None

    async def __call__(self, messages, schema, **kwargs):
        self.calls += 1
        self.sent.append(messages)
        self.kwargs = kwargs
        reply = self._replies[min(self.calls - 1, len(self._replies) - 1)]
        return client.Call(
            value=schema.model_validate(reply.model_dump()), model="test/model",
            usage=llm_calls.Usage(input_tokens=100, output_tokens=20), latency_ms=1, call_id=uuid.uuid4(),
            first_token_ms=1,
        )


async def reachable() -> bool:
    try:
        conn = await asyncpg.connect(get_settings().database_url, timeout=3)
    except (OSError, asyncpg.PostgresError):
        return False
    await conn.close()
    return True


async def start(claims: Claims, style: str | None = "Supportive"):
    """A conversation opened, with its style chosen by a tap when `style` is given, as the app does."""
    from mani.chat import turn
    from mani.db import pool

    async with pool.as_user(claims) as conn:
        await profiles.upsert(conn, ALICE, nickname="Al")
        thread = await turn.start_thread(conn, claims)
    if style:
        await runner.send(claims, thread.id, style)
    return thread


async def send(claims: Claims, thread_id, content, **kwargs):
    return await runner.send(claims, thread_id, content, **kwargs)


async def thread_row(claims: Claims, thread_id):
    from mani.db import pool

    async with pool.as_user(claims) as conn:
        return (await threads.load_turn_context(conn, thread_id, ALICE)).thread


async def last_user_message_id(thread_id):
    from mani.db import pool

    async with pool.as_admin() as conn:
        return await conn.fetchval(
            "select id from public.messages where thread_id = $1 and role = 'user' order by created_at desc limit 1",
            thread_id,
        )


async def user_messages(thread_id) -> list[str]:
    from mani.db import pool

    async with pool.as_admin() as conn:
        rows = await conn.fetch(
            "select content from public.messages where thread_id = $1 and role = 'user' order by created_at", thread_id
        )
    return [r["content"] for r in rows]
