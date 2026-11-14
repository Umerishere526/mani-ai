# ABOUTME: Starts, finds and marks the pauses on a person's chat after a crisis.
# ABOUTME: Every write runs as mani_service; RLS scopes it to the caller's own rows.

from __future__ import annotations

import uuid

import asyncpg

from mani.models.rows import Pause


async def start(
    conn: asyncpg.Connection,
    user_id: uuid.UUID | str,
    thread_id: uuid.UUID | str,
    minutes: int,
    reason: str | None,
) -> Pause:
    record = await conn.fetchrow(
        "insert into public.chat_pauses (user_id, thread_id, ends_at, reason) "
        "values ($1, $2, now() + make_interval(mins => $3), $4) returning *",
        user_id, thread_id, minutes, reason,
    )
    return Pause.model_validate(dict(record))


async def active(conn: asyncpg.Connection, user_id: uuid.UUID | str) -> Pause | None:
    return Pause.from_record(await conn.fetchrow(
        # No reason: it is read only by the turns of the conversation the pause began in (threads.load_turn_context).
        "select id, user_id, thread_id, started_at, ends_at, checked_at from public.chat_pauses "
        "where user_id = $1 and ends_at > now() "
        "order by started_at desc limit 1",
        user_id,
    ))


async def mark_checked(conn: asyncpg.Connection, pause_id: uuid.UUID | str) -> None:
    await conn.execute(
        "update public.chat_pauses set checked_at = now() where id = $1", pause_id
    )
