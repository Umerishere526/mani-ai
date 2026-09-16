# ABOUTME: Reads and writes messages. Every read carries its own ownership predicate.
# ABOUTME: Writes go through security-definer functions so Mani's turns cannot be forged.

import datetime as dt
import uuid
from dataclasses import dataclass
from typing import Any

import asyncpg

from mani.models.rows import Message

COLUMNS = (
    "id, thread_id, user_id, role, content, prompt_options, "
    "selected_prompt, client_message_id, created_at"
)

DEFAULT_PAGE = 50
# How much raw history the model sees. Matches the previous system's window.
CONTEXT_WINDOW = 20


@dataclass(frozen=True)
class Page:
    messages: list[Message]
    next_cursor: str | None


async def list_for_thread(
    conn: asyncpg.Connection,
    thread_id: uuid.UUID | str,
    user_id: uuid.UUID | str,
    limit: int = DEFAULT_PAGE,
    cursor: dt.datetime | None = None,
) -> Page:
    """A page of a thread's messages, newest first.

    `user_id` is not optional. The equivalent in the previous system filtered on
    thread_id alone and ran on a connection that bypassed RLS, which is how one user
    read another's transcript. RLS would now stop that on its own; the predicate is
    here as well because a single control is not a control.
    """
    rows = await conn.fetch(
        f"""
        select {COLUMNS} from public.messages
         where thread_id = $1
           and user_id = $2
           and ($3::timestamptz is null or created_at < $3)
         order by created_at desc
         limit $4
        """,
        thread_id, user_id, cursor, limit + 1,
    )

    has_more = len(rows) > limit
    page = Message.from_records(rows[:limit])
    next_cursor = page[-1].created_at.isoformat() if has_more and page else None
    return Page(messages=page, next_cursor=next_cursor)


async def recent_for_context(
    conn: asyncpg.Connection,
    thread_id: uuid.UUID | str,
    user_id: uuid.UUID | str,
    limit: int = CONTEXT_WINDOW,
) -> list[Message]:
    """The tail of a thread, oldest first, for the model's view of the conversation.

    Bounded unconditionally. The previous implementation dropped its limit once a
    summary existed, so a thread with a stale checkpoint resent every message after it
    on every turn.
    """
    rows = await conn.fetch(
        f"""
        select * from (
            select {COLUMNS} from public.messages
             where thread_id = $1 and user_id = $2
             order by created_at desc
             limit $3
        ) recent order by created_at
        """,
        thread_id, user_id, limit,
    )
    return Message.from_records(rows)


async def latest_mani_id(
    conn: asyncpg.Connection, thread_id: uuid.UUID | str, user_id: uuid.UUID | str
) -> uuid.UUID | None:
    """The newest message from Mani in a thread.

    Its buttons are the only live ones. Knowing which message that is has to come from
    the thread rather than from whatever page is being rendered, or page two would
    present its own newest reply as though its offer were still open.
    """
    return await conn.fetchval(
        "select id from public.messages "
        "where thread_id = $1 and user_id = $2 and role = 'mani' "
        "order by created_at desc limit 1",
        thread_id, user_id,
    )


async def find_by_client_id(
    conn: asyncpg.Connection,
    user_id: uuid.UUID | str,
    client_message_id: uuid.UUID | str,
) -> Message | None:
    """The idempotency lookup, scoped to the caller.

    The previous version looked this up globally, so a guessed or colliding id returned
    a stranger's message.
    """
    row = await conn.fetchrow(
        f"select {COLUMNS} from public.messages "
        "where user_id = $1 and client_message_id = $2",
        user_id, client_message_id,
    )
    return Message.from_record(row)


async def find_pair_by_client_id(
    conn: asyncpg.Connection,
    user_id: uuid.UUID | str,
    client_message_id: uuid.UUID | str,
) -> tuple[Message, Message | None] | None:
    """The turn a retried request already produced, if it produced one.

    Checked before the model is called rather than after it, which is where the previous
    implementation checked: a retry there had already paid for a second generation and
    then thrown it away.
    """
    user_message = await find_by_client_id(conn, user_id, client_message_id)
    if user_message is None:
        return None

    row = await conn.fetchrow(
        f"select {COLUMNS} from public.messages "
        "where thread_id = $1 and user_id = $2 and role = 'mani' and created_at >= $3 "
        "order by created_at limit 1",
        user_message.thread_id, user_id, user_message.created_at,
    )
    return user_message, Message.from_record(row)


@dataclass(frozen=True)
class Pair:
    user_message_id: uuid.UUID
    mani_message_id: uuid.UUID | None
    created_at: Any
    was_duplicate: bool


async def create_pair(
    conn: asyncpg.Connection,
    thread_id: uuid.UUID | str,
    user_content: str,
    mani_content: str,
    *,
    selected_prompt: str | None = None,
    prompt_options: list[dict[str, Any]] | None = None,
    client_message_id: uuid.UUID | str | None = None,
) -> Pair:
    """Write both sides of a turn in one statement.

    The user id comes from the verified session inside the function, never from here.
    """
    row = await conn.fetchrow(
        "select * from public.create_message_pair($1, $2, $3, $4, $5::jsonb, $6)",
        thread_id, user_content, mani_content, selected_prompt,
        prompt_options, client_message_id,
    )
    return Pair(
        user_message_id=row["user_message_id"],
        mani_message_id=row["mani_message_id"],
        created_at=row["created_at"],
        was_duplicate=row["was_duplicate"],
    )


async def create_greeting(
    conn: asyncpg.Connection, thread_id: uuid.UUID | str, content: str
) -> uuid.UUID:
    """Mani's opening line. Refused once the thread has started."""
    return await conn.fetchval(
        "select public.create_greeting($1, $2)", thread_id, content
    )
