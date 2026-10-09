# ABOUTME: Refreshes a thread's rolling summary so Mani remembers past the recent window.
# ABOUTME: Runs after a turn has been answered, never in the path of one.

from __future__ import annotations

import logging
import uuid

import asyncpg

from mani.config import get_settings
from mani.db import llm_calls, messages as messages_db, summaries, threads
from mani.llm import client
from mani.llm.schema import Extraction
from mani.models.rows import Message, MessageRole, TechniqueTried, ThreadSummary
from mani.prompts import cache, calls
from mani.prompts.composer import tried_line

logger = logging.getLogger(__name__)

# How much raw conversation one summarization run reads.
BATCH = 200

# How many threads one catch-up run summarizes.
RECONCILE_BATCH = 200


def transcript(messages: list[Message]) -> str:
    return "\n\n".join(
        f"{'User' if m.role is MessageRole.USER else 'Assistant'}: {m.content}"
        for m in messages
    )


def request(existing: ThreadSummary | None, new_messages: list[Message]) -> str:
    """The summary call's user message: headings and keyed lines, which summarization.md names.

    `## Existing Summary` is left out when there is none yet, or when all its fields are empty.
    """
    lines = []
    if existing is not None:
        if existing.current_issue:
            lines.append(f"current_issue: {existing.current_issue}")
        if existing.summary:
            lines.append(f"summary: {existing.summary}")
        if existing.techniques_tried:
            lines.append(f"techniques_tried: {tried_line(existing.techniques_tried)}")
    sections = ["## Existing Summary\n" + "\n".join(lines)] if lines else []
    return "\n\n".join(sections + [f"## New Messages\n{transcript(new_messages)}"])


async def _since_checkpoint(
    conn: asyncpg.Connection,
    thread_id: uuid.UUID | str,
    user_id: str,
    checkpoint: uuid.UUID | None,
) -> list[Message]:
    """Messages written after the last summarized one, oldest first."""
    rows = await conn.fetch(
        f"""
        select {messages_db.COLUMNS} from public.messages
         where thread_id = $1
           and user_id = $2
           and ($3::uuid is null
                or created_at > (select created_at from public.messages where id = $3))
         order by created_at
         limit $4
        """,
        thread_id, user_id, checkpoint, BATCH,
    )
    return Message.from_records(rows)


async def update(
    conn: asyncpg.Connection, thread_id: uuid.UUID | str, user_id: str
) -> ThreadSummary | None:
    """Fold new messages into the thread's summary.

    Returns None when there is nothing new. A failure here is logged and swallowed: a
    missing summary costs Mani some memory, and is not worth failing a delivered reply
    over. Transcript content is never logged - the reference logged whole conversations
    at error level, in production.
    """
    settings = get_settings()
    # One summary per thread at a time. Every turn past the threshold schedules one, so a
    # message sent before the last has committed would otherwise fold the same messages again
    # and pay for it. A run already in progress will cover them; this one steps aside.
    if not await conn.fetchval(
        "select pg_try_advisory_xact_lock(hashtextextended($1, 0))", f"summary:{thread_id}"
    ):
        return None
    thread = await threads.get(conn, thread_id, user_id)
    if thread is None:
        return None

    existing = await summaries.get(conn, thread_id)
    checkpoint = existing.summarized_through_message_id if existing else None
    new_messages = await _since_checkpoint(conn, thread_id, user_id, checkpoint)
    if not new_messages:
        return existing

    config = await cache.load()
    prompt = config.require("summarization")
    effort = calls.effort_for(prompt, "summarization")

    call = await client.complete(
        [
            {"role": "system", "content": prompt.content},
            {"role": "user", "content": request(existing, new_messages)},
        ],
        Extraction,
        model=prompt.model_id or settings.default_summary_model,
        purpose=llm_calls.Purpose.SUMMARIZE,
        temperature=prompt.model_parameters.get("temperature", 0),
        max_tokens=prompt.model_parameters.get("maxTokens", 500),
        reasoning_effort=effort,
        routing=prompt.routing,
        user_id=user_id,
        thread_id=thread.id,
    )

    merged = summaries.merge_techniques(
        existing.techniques_tried if existing else [],
        [
            TechniqueTried(name=t.name, helpful=t.helpful, context=t.context)
            for t in call.value.techniques_tried
        ],
    )

    return await summaries.upsert(
        conn,
        thread.id,
        user_id,
        summary=call.value.summary,
        current_issue=call.value.current_issue,
        techniques_tried=merged,
        # A real message id, so the next run knows where it got to. The reference wrote
        # the summary row's own id into this column when the batch was empty, which is a
        # different id space - the foreign key now refuses it outright.
        summarized_through_message_id=new_messages[-1].id,
        # The thread's own message count, the same unit the trigger compares against.
        summarized_message_count=thread.message_count,
    )


async def update_quietly(claims, thread_id: uuid.UUID | str) -> None:
    """Run a summary on its own connection, swallowing failure.

    Scheduled after the response has been sent, so it never delays a reply and never
    fails one. It takes a fresh user-scoped connection because the turn's transaction has
    already committed by the time this runs.
    """
    from mani.db import pool

    try:
        async with pool.as_user(claims) as conn:
            await update(conn, thread_id, claims.user_id)
    except Exception:
        logger.exception("summarization failed for thread %s", thread_id)


async def reconcile_due() -> int:
    """Catch up every thread whose summary has fallen behind, across every user.

    The per-turn trigger (`update_quietly`) is the fast path and covers almost every
    thread almost immediately; this is the guaranteed path for whatever it missed - the
    process restarted before its background task finished, or never got a next turn to
    trigger it. Safe to run concurrently with itself or with a per-turn trigger: `update`
    takes a transaction-scoped advisory lock per thread, so two attempts on the same
    thread just have one step aside.
    """
    from mani.auth.jwt import Claims
    from mani.db import pool, summaries

    # The turn refreshes a summary every `context_window` messages, so this catches up the same.
    threshold = (await cache.load()).tuning.windows.context_window
    async with pool.as_admin() as conn:
        due = await summaries.due_for_summary(conn, threshold=threshold, limit=RECONCILE_BATCH)

    done = 0
    for row in due:
        claims = Claims(
            sub=str(row["user_id"]), raw={"sub": str(row["user_id"]), "role": "authenticated"}
        )
        await update_quietly(claims, row["thread_id"])
        done += 1
    return done
