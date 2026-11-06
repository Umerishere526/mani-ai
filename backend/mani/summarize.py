# ABOUTME: Refreshes a thread's rolling summary of what has left the model's view of a long thread.
# ABOUTME: Runs after a turn has been answered, never in the path of one.

from __future__ import annotations

import logging
import uuid

import asyncpg

from mani.config import get_settings
from mani.db import llm_calls, messages as messages_db, summaries, threads
from mani.llm import client
from mani.llm.schema import Extraction
from mani.one_at_a_time import one_at_a_time
from mani.models.rows import Message, MessageRole, TechniqueTried, ThreadSummary
from mani.prompts import cache

logger = logging.getLogger(__name__)

# How much raw conversation one summarization run reads.
BATCH = 200


def transcript(messages: list[Message]) -> str:
    return "\n\n".join(
        f"{'User' if m.role is MessageRole.USER else 'Assistant'}: {m.content}"
        for m in messages
    )


def existing_context(summary: ThreadSummary | None) -> str:
    if summary is None:
        return "No existing summary."
    parts = []
    if summary.summary:
        parts.append(f"Previous summary: {summary.summary}")
    if summary.techniques_tried:
        tried = ", ".join(
            f"{t.name} ({'helpful' if t.helpful else 'not helpful'})"
            for t in summary.techniques_tried
        )
        parts.append(f"Techniques tried: {tried}")
    return "\n".join(parts) if parts else "No existing summary."


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


async def update(claims, thread_id: uuid.UUID | str) -> ThreadSummary | None:
    """Fold new messages into the thread's summary. Returns None when the thread is gone.

    Read, then the model with no connection held, then write. Transcript content is never
    logged - the reference logged whole conversations at error level, in production.
    """
    from mani.db import pool

    settings = get_settings()
    user_id = claims.user_id
    # One summary per thread at a time. Every turn past the threshold schedules one, so a
    # message sent before the last has landed would otherwise fold the same messages again
    # and pay for it. The second waits here, then finds them already summarized.
    async with one_at_a_time(("summary", str(thread_id))):
        config = await cache.load()
        async with pool.as_user(claims) as conn:
            thread = await threads.get(conn, thread_id, user_id)
            if thread is None:
                return None
            existing = await summaries.get(conn, thread_id)
            checkpoint = existing.summarized_through_message_id if existing else None
            new_messages = await _since_checkpoint(conn, thread_id, user_id, checkpoint)
        if not new_messages:
            return existing

        prompt = config.prompt("summarization")
        if prompt is None:
            logger.warning("no summarization prompt configured; skipping")
            return existing

        call = await client.complete(
            [
                {"role": "system", "content": prompt.content},
                {
                    "role": "user",
                    "content": (
                        f"## Existing Summary\n{existing_context(existing)}\n\n"
                        f"## New Messages\n{transcript(new_messages)}\n\n"
                        "Extract updated information from these messages and merge with the "
                        "existing summary."
                    ),
                },
            ],
            Extraction,
            model=prompt.model_id or settings.default_summary_model,
            purpose=llm_calls.Purpose.SUMMARIZE,
            temperature=prompt.model_parameters.get("temperature", 0),
            max_tokens=prompt.model_parameters.get("maxTokens", 500),
            reasoning_effort=prompt.model_parameters.get("reasoning_effort"),
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

        async with pool.as_user(claims) as conn:
            # Written only onto the summary it read. One written meanwhile, by another instance, covers
            # these messages already, so it stands and this one is dropped.
            await conn.execute(
                "select pg_advisory_xact_lock(hashtextextended($1, 0))", f"summary:{thread_id}"
            )
            now = await summaries.get(conn, thread_id)
            if (now.summarized_through_message_id if now else None) != checkpoint:
                return now
            return await summaries.upsert(
                conn,
                thread.id,
                user_id,
                summary=call.value.summary,
                techniques_tried=merged,
                # A real message id, so the next run knows where it got to. The reference wrote
                # the summary row's own id into this column when the batch was empty, which is a
                # different id space - the foreign key now refuses it outright.
                summarized_through_message_id=new_messages[-1].id,
                # The thread's own message count, the same unit the trigger compares against.
                summarized_message_count=thread.message_count,
            )


async def update_quietly(claims, thread_id: uuid.UUID | str) -> None:
    """Run a summary, swallowing failure.

    Scheduled after the response has been sent, so it never delays a reply and never
    fails one.
    """
    try:
        await update(claims, thread_id)
    except Exception:
        logger.exception("summarization failed for thread %s", thread_id)


async def reconcile_due(*, limit: int = 200) -> int:
    """Catch up every thread whose summary has fallen behind, across every user.

    The per-turn trigger (`update_quietly`) is the fast path and covers almost every
    thread almost immediately; this is the guaranteed path for whatever it missed - the
    process restarted before its background task finished, or never got a next turn to
    trigger it. Safe to run concurrently with itself or with a per-turn trigger: in one
    process a second attempt on a thread waits for the first and finds nothing left, and
    across processes the second to write finds the first's summary and drops its own.
    """
    from mani.auth.jwt import Claims
    from mani.db import pool, summaries

    async with pool.as_admin() as conn:
        due = await summaries.due_for_summary(
            conn, budget_chars=get_settings().context_budget_chars,
            block=messages_db.CONTEXT_DROP_BLOCK, limit=limit,
        )

    done = 0
    for row in due:
        claims = Claims(
            sub=str(row["user_id"]), raw={"sub": str(row["user_id"]), "role": "authenticated"}
        )
        await update_quietly(claims, row["thread_id"])
        done += 1
    return done
