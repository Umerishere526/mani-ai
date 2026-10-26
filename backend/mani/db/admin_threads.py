# ABOUTME: Cross-user reads of conversations for admins, and the log of each full read.
# ABOUTME: Runs only on the admin connection; nothing here writes to a conversation.

from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass

import asyncpg
from pydantic import BaseModel

from mani.db import messages as messages_db
from mani.models.rows import Message, SupportStyle

DEFAULT_PAGE = 50
MAX_PAGE = 200


class AdminThread(BaseModel):
    """A conversation as an admin sees it in a list: whose it is and how far it has gone."""

    id: uuid.UUID
    user_id: uuid.UUID
    user_email: str | None = None
    user_nickname: str | None = None
    title: str | None = None
    message_count: int = 0
    crisis_detected: bool = False
    # How Mani speaks in it: the conversation's own choice, else the person's onboarding default,
    # as a turn resolves it. Null when neither has been chosen yet.
    conversation_style: SupportStyle | None = None
    created_at: dt.datetime
    last_message_at: dt.datetime


@dataclass(frozen=True)
class Page:
    threads: list[AdminThread]
    next_cursor: str | None


_SELECT = """
    select t.id, t.user_id, u.email as user_email, p.nickname as user_nickname,
           t.title, t.message_count, t.crisis_detected, t.created_at, t.last_message_at,
           coalesce(t.conversation_style, p.support_style) as conversation_style
      from public.threads t
      join auth.users u on u.id = t.user_id
      left join public.profiles p on p.user_id = t.user_id
"""


async def list_all(
    conn: asyncpg.Connection,
    search: str | None = None,
    limit: int = DEFAULT_PAGE,
    cursor: dt.datetime | None = None,
) -> Page:
    """Every person's conversations, most recently active first.

    A thread the person deleted stays out of view, as it does for them. `search` matches part
    of the owner's email, or their user id exactly.
    """
    term = (search or "").strip() or None
    rows = await conn.fetch(
        f"""
        {_SELECT}
         where t.deleted_at is null
           and ($1::text is null
                or u.email ilike '%' || $1 || '%'
                or t.user_id::text = lower($1))
           and ($2::timestamptz is null or t.last_message_at < $2)
         order by t.last_message_at desc
         limit $3
        """,
        term, cursor, limit + 1,
    )
    has_more = len(rows) > limit
    threads = [AdminThread.model_validate(dict(r)) for r in rows[:limit]]
    next_cursor = threads[-1].last_message_at.isoformat() if has_more and threads else None
    return Page(threads=threads, next_cursor=next_cursor)


async def read_transcript(
    conn: asyncpg.Connection, thread_id: uuid.UUID, admin_id: uuid.UUID | str
) -> tuple[AdminThread, list[Message]] | None:
    """One conversation and every message in it, oldest first, logged as read by `admin_id`.

    The log row is written in the same transaction as the read, so a transcript is never
    returned without its record.
    """
    row = await conn.fetchrow(
        f"{_SELECT} where t.id = $1 and t.deleted_at is null", thread_id
    )
    if row is None:
        return None
    messages = await conn.fetch(
        f"select {messages_db.COLUMNS} from public.messages "
        "where thread_id = $1 order by created_at",
        thread_id,
    )
    await conn.execute(
        "insert into admin.thread_reads (admin_id, thread_id) values ($1, $2)",
        admin_id, thread_id,
    )
    return AdminThread.model_validate(dict(row)), Message.from_records(messages)
