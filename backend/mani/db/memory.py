# ABOUTME: Reads and writes the per-person memory, and claims finished threads to fold into it.
# ABOUTME: Every write runs as mani_service; RLS scopes it to the caller's own row.

from __future__ import annotations

import datetime as dt
import uuid

import asyncpg

from mani.db import messages as messages_db
from mani.llm.schema import Memory
from mani.models.rows import Message

# How much of one finished conversation a single fold reads.
FOLD_BATCH = 200

# A thread needs folding when the person has said something in it since it was last folded.
# Mani's greeting alone never counts, and a thread flagged for crisis is never folded: what
# was said there is not carried into a memory read at the start of every later chat.
_NEEDS_FOLD = """
    t.deleted_at is null
    and not t.crisis_detected
    and exists (
      select 1 from public.messages m
       where m.thread_id = t.id and m.role = 'user'
         and m.created_at > coalesce(t.memory_folded_at, '-infinity'::timestamptz)
    )
"""


async def get(conn: asyncpg.Connection, user_id: uuid.UUID | str) -> Memory | None:
    value = await conn.fetchval(
        "select memory from admin.user_memory where user_id = $1", user_id
    )
    return Memory.model_validate(value) if value else None


async def lock(conn: asyncpg.Connection, user_id: uuid.UUID | str) -> Memory:
    """The person's memory, row-locked for the rest of the transaction.

    A fold reads the memory, asks the model to merge, and writes the result back. Two folds
    for the same person at once - a new chat and the idle job - would each merge into the
    same starting point and the second write would drop the first's additions.
    """
    await conn.execute(
        "insert into admin.user_memory (user_id) values ($1) on conflict (user_id) do nothing",
        user_id,
    )
    value = await conn.fetchval(
        "select memory from admin.user_memory where user_id = $1 for update", user_id
    )
    return Memory.model_validate(value or {})


async def save(conn: asyncpg.Connection, user_id: uuid.UUID | str, memory: Memory) -> None:
    await conn.execute(
        "update admin.user_memory set memory = $2::jsonb, updated_at = now() "
        "where user_id = $1",
        user_id, memory.model_dump(),
    )


async def claim_thread(
    conn: asyncpg.Connection,
    user_id: uuid.UUID | str,
    *,
    keep: uuid.UUID | str | None = None,
    idle_before: dt.datetime | None = None,
) -> tuple[uuid.UUID, dt.datetime | None] | None:
    """Claim one of this person's threads that needs folding, and mark it folded.

    Returns the thread and when it was last folded, or None when there is nothing to do.
    `skip locked` means a second caller passes over a thread already being folded, and the
    mark is part of the caller's transaction, so a fold that fails releases it again.
    `keep` is the conversation the person is in now; `idle_before` limits it to threads
    that have gone quiet.
    """
    row = await conn.fetchrow(
        f"""
        with claimed as (
          select t.id, t.memory_folded_at as since
            from public.threads t
           where t.user_id = $1 and {_NEEDS_FOLD}
             and ($2::uuid is null or t.id <> $2)
             and ($3::timestamptz is null or t.last_message_at < $3)
           order by t.last_message_at
           limit 1
             -- NO KEY UPDATE, not UPDATE: still exclusive between two claimers, but it
             -- does not block the key-share lock a foreign key takes. The fold's own cost
             -- row references this thread and is written on another connection while this
             -- transaction is open; FOR UPDATE deadlocked the two through the application.
             for no key update skip locked
        )
        update public.threads t set memory_folded_at = now()
          from claimed
         where t.id = claimed.id
        returning t.id, claimed.since
        """,
        user_id, keep, idle_before,
    )
    return (row["id"], row["since"]) if row else None


async def messages_since(
    conn: asyncpg.Connection,
    thread_id: uuid.UUID | str,
    user_id: uuid.UUID | str,
    since: dt.datetime | None,
) -> list[Message]:
    rows = await conn.fetch(
        f"""
        select {messages_db.COLUMNS} from public.messages
         where thread_id = $1 and user_id = $2
           and created_at > coalesce($3::timestamptz, '-infinity'::timestamptz)
         order by created_at
         limit $4
        """,
        thread_id, user_id, since, FOLD_BATCH,
    )
    return Message.from_records(rows)


async def mark_folded_through(
    conn: asyncpg.Connection, thread_id: uuid.UUID | str, through: dt.datetime
) -> None:
    """Record the last message the fold actually read, not the time it ran.

    A fold reads at most FOLD_BATCH messages; marking the thread folded as of now() would
    silently skip whatever lay beyond that. Marking it at the last message read means the
    rest is picked up by the next fold.
    """
    await conn.execute(
        "update public.threads set memory_folded_at = $2 where id = $1", thread_id, through
    )


async def users_with_idle_threads(
    conn: asyncpg.Connection, idle_before: dt.datetime, limit: int
) -> list[uuid.UUID]:
    """People who have a quiet thread waiting to be folded. Cross-user, so admin-only."""
    rows = await conn.fetch(
        f"""
        select distinct t.user_id from public.threads t
         where {_NEEDS_FOLD}
           and t.last_message_at < $1
         limit $2
        """,
        idle_before, limit,
    )
    return [r["user_id"] for r in rows]
