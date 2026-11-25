# ABOUTME: Saves the thread state a turn is about to overwrite, and puts it back when that turn's message is edited.
# ABOUTME: One turn back only: the snapshot is replaced by every turn and cleared once used.

from __future__ import annotations

import uuid

import asyncpg

from mani.chat.greeting import OPENING_MESSAGES
from mani.db import threads
from mani.db.threads import TurnContext, load_turn_context
from mani.errors import ErrorCategory, ServiceError
from mani.models.rows import TechniqueState

_REFUSALS = {
    "not_found": (ErrorCategory.NOT_FOUND, "That message is not available."),
    "tapped": (ErrorCategory.CONFLICT, "A message sent by tapping an option cannot be edited."),
    "not_last": (ErrorCategory.CONFLICT, "Only your last message can be edited."),
}

def snapshot_of(ctx: TurnContext) -> dict:
    """What the turn about to run will overwrite, as JSON."""
    return {
        "title": ctx.thread.title,
        "understanding": ctx.thread.understanding,
        "safety": ctx.thread.safety,
        "technique": ctx.technique.model_dump(mode="json") if ctx.technique else None,
    }


async def save(conn: asyncpg.Connection, ctx: TurnContext, user_id: uuid.UUID | str) -> None:
    await conn.execute(
        "update public.threads set rewind_snapshot = $1::jsonb where id = $2 and user_id = $3",
        snapshot_of(ctx), ctx.thread.id, user_id,
    )


def _refuse(category: ErrorCategory, user_message: str) -> ServiceError:
    return ServiceError(user_message, category, user_message=user_message)


async def undo_last_turn(
    conn: asyncpg.Connection, user_id: uuid.UUID | str, thread_id: uuid.UUID | str, message_id: uuid.UUID | str
) -> None:
    """Delete the person's last message and Mani's reply, and restore the state from before that turn.
    Raises a ServiceError, changing nothing, when the turn cannot be undone safely."""
    await threads.lock(conn, thread_id)
    ctx = await load_turn_context(conn, thread_id, user_id)
    if ctx is None:
        raise _refuse(ErrorCategory.NOT_FOUND, "That conversation is not available.")
    thread = ctx.thread
    if thread.message_count <= OPENING_MESSAGES:
        raise _refuse(ErrorCategory.CONFLICT, "The style you chose cannot be edited.")
    if ctx.summary and ctx.summary.summarized_message_count >= thread.message_count - 1:
        raise _refuse(ErrorCategory.CONFLICT, "That message is already part of this conversation's summary.")
    snapshot = await conn.fetchval(
        "select rewind_snapshot from public.threads where id = $1 and user_id = $2", thread_id, user_id
    )
    if snapshot is None:
        raise _refuse(ErrorCategory.CONFLICT, "That message cannot be edited.")

    outcome = await conn.fetchval("select public.delete_last_message_pair($1, $2)", thread_id, message_id)
    if outcome != "deleted":
        category, message = _REFUSALS[outcome]
        raise _refuse(category, message)

    await _restore(conn, user_id, thread_id, snapshot)


async def _restore(conn: asyncpg.Connection, user_id, thread_id, snapshot: dict) -> None:
    await conn.execute(
        "update public.threads set title = $1 where id = $2 and user_id = $3",
        snapshot["title"], thread_id, user_id,
    )
    await conn.execute(
        "update public.threads set understanding = $1::jsonb, rewind_snapshot = null where id = $2 and user_id = $3",
        snapshot["understanding"], thread_id, user_id,
    )
    await threads.set_safety(conn, thread_id, user_id, snapshot.get("safety") or "clear")
    if snapshot["technique"] is None:
        await conn.execute("delete from public.thread_technique_state where thread_id = $1", thread_id)
    else:
        t = TechniqueState.model_validate(snapshot["technique"])
        await conn.execute(
            """
            insert into public.thread_technique_state
                (thread_id, user_id, framework_id, outcome, phase, at_message_count)
            values ($1, $2, $3, $4, $5, $6)
            on conflict (thread_id) do update set
                framework_id     = excluded.framework_id,
                outcome          = excluded.outcome,
                phase            = excluded.phase,
                at_message_count = excluded.at_message_count
            """,
            thread_id, user_id, t.framework_id, t.outcome.value, t.phase, t.at_message_count,
        )
