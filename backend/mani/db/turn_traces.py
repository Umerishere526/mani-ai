# ABOUTME: Each chat turn's trace, what code decided and why, and in debug the model's raw reply for a while.
# ABOUTME: Written after the turn on an admin connection; read by the admin transcript and scripts/trace.py.

from __future__ import annotations

import datetime as dt
import json
import uuid

import asyncpg

# How long the model's raw reply, which carries their words, is kept (muhammad, 2026-11-03).
RAW_REPLY_DAYS = 14


async def record(
    conn: asyncpg.Connection,
    *,
    thread_id: uuid.UUID | str,
    message_id: uuid.UUID | str,
    llm_call_id: uuid.UUID | str | None,
    trace: dict,
    raw_reply: dict | None,
) -> None:
    """Store one turn's trace, and its raw reply when given, expiring after RAW_REPLY_DAYS. Every write first clears
    the raw replies already past their time, so none outlives it by more than the gap to the next turn anywhere."""
    await conn.execute(
        "update admin.turn_traces set raw_reply = null, raw_expires_at = null "
        "where raw_reply is not null and raw_expires_at < now()"
    )
    expires = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=RAW_REPLY_DAYS) if raw_reply is not None else None
    await conn.execute(
        """
        insert into admin.turn_traces (thread_id, message_id, llm_call_id, trace, raw_reply, raw_expires_at)
        values ($1, $2, $3, $4::jsonb, $5::jsonb, $6)
        on conflict (message_id) do nothing
        """,
        # The pool's jsonb codec encodes these (db/pool.py); both hold only JSON values.
        thread_id, message_id, llm_call_id, trace, raw_reply, expires,
    )


async def for_thread(conn: asyncpg.Connection, thread_id: uuid.UUID | str) -> dict[str, dict]:
    """Every trace in a conversation by the id of the reply it explains, with the raw reply while it is kept."""
    rows = await conn.fetch(
        "select message_id, trace, raw_reply, created_at from admin.turn_traces "
        "where thread_id = $1 order by created_at",
        thread_id,
    )
    return {
        str(r["message_id"]): {
            "trace": _json(r["trace"]),
            **({"raw_reply": _json(r["raw_reply"])} if r["raw_reply"] is not None else {}),
        }
        for r in rows
    }


def _json(value):
    return json.loads(value) if isinstance(value, str) else value
