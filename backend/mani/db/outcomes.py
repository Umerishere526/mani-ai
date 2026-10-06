# ABOUTME: Writes how a person said they felt after the practice that ends a framework (spec 0010, AC-8).
# ABOUTME: Runs on the turn's own connection, so the row lands with the turn or not at all.

import uuid

import asyncpg


async def record(
    conn: asyncpg.Connection,
    *,
    user_id: uuid.UUID | str,
    thread_id: uuid.UUID | str,
    message_id: uuid.UUID | str,
    framework_id: str,
    conversation_style: str,
    ending: str,
    body_place: str | None,
    outcome: str,
) -> bool:
    """Insert one outcome row. False when a row for the same message, or the same ending of the
    same framework in the thread, already exists: a retried turn writes nothing twice."""
    written = await conn.fetchval(
        """
        insert into public.framework_outcomes
            (user_id, thread_id, message_id, framework_id, conversation_style, ending,
             body_place, outcome)
        values ($1, $2, $3, $4, $5, $6, $7, $8)
        on conflict do nothing
        returning id
        """,
        user_id, thread_id, message_id, framework_id, conversation_style, ending,
        body_place, outcome,
    )
    return written is not None
