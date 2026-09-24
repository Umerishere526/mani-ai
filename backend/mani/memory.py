# ABOUTME: Folds a finished conversation into what Mani knows about the person across chats.
# ABOUTME: Runs when a new chat starts and from the idle job, never in the path of a reply.

from __future__ import annotations

import datetime as dt
import logging
import uuid

import asyncpg

from mani.auth.jwt import Claims
from mani.chat import context
from mani.config import get_settings
from mani.db import llm_calls, memory as memory_db
from mani.llm import client
from mani.llm.schema import Memory
from mani.models.rows import Message, MessageRole
from mani.prompts import cache

logger = logging.getLogger(__name__)

# The memory is pasted into the system prompt of every later chat, so it is bounded here
# whatever the model returns: a runaway list is a cost multiplier and an injection channel.
MAX_ENTRIES = 6
MAX_ENTRY_CHARS = 160

# How long a conversation has to be quiet before the idle job treats it as finished.
IDLE_AFTER = dt.timedelta(hours=24)

# Each fold advances the thread to the last message it read, so the loop below ends on its
# own. This bounds it anyway: a fault in that condition would otherwise pay for a model
# call per iteration, forever, in a background task nobody is watching.
MAX_FOLDS_PER_RUN = 20


def bounded(memory: Memory) -> Memory:
    return Memory.model_validate(
        {
            field: [entry.strip()[:MAX_ENTRY_CHARS] for entry in entries if entry.strip()][
                :MAX_ENTRIES
            ]
            for field, entries in memory.model_dump().items()
        }
    )


def _transcript(messages: list[Message]) -> str:
    return "\n\n".join(
        f"{'Person' if m.role is MessageRole.USER else 'Mani'}: "
        f"{context.disarm(m.content) if m.role is MessageRole.USER else m.content}"
        for m in messages
    )


async def fold_one(
    conn: asyncpg.Connection,
    user_id: uuid.UUID | str,
    *,
    keep: uuid.UUID | str | None = None,
    idle_before: dt.datetime | None = None,
) -> bool:
    """Fold one finished thread into the person's memory. False when none was waiting.

    Claim, read, merge and write share the caller's transaction: if the model call fails,
    the claim is released and the thread is picked up again next time.
    """
    claimed = await memory_db.claim_thread(conn, user_id, keep=keep, idle_before=idle_before)
    if claimed is None:
        return False
    thread_id, since = claimed

    new_messages = await memory_db.messages_since(conn, thread_id, user_id, since)
    existing = await memory_db.lock(conn, user_id)

    config = await cache.load()
    prompt = config.prompt("memory_fold")
    if prompt is None:
        raise RuntimeError("no memory_fold prompt configured")

    call = await client.complete(
        [
            {"role": "system", "content": prompt.content},
            {
                "role": "user",
                "content": (
                    f"## Known so far\n{existing.model_dump_json(indent=1)}\n\n"
                    f"## The conversation that just finished\n{_transcript(new_messages)}"
                ),
            },
        ],
        Memory,
        model=prompt.model_id or get_settings().default_summary_model,
        purpose=llm_calls.Purpose.MEMORY_FOLD,
        temperature=prompt.model_parameters.get("temperature", 0),
        max_tokens=prompt.model_parameters.get("maxTokens", 800),
        routing=prompt.routing,
        user_id=user_id,
        thread_id=thread_id,
    )
    await memory_db.save(conn, user_id, bounded(call.value))
    await memory_db.mark_folded_through(conn, thread_id, new_messages[-1].created_at)
    return True


async def fold_finished(
    claims: Claims, *, keep: uuid.UUID | str | None = None, idle_before: dt.datetime | None = None
) -> int:
    """Fold every finished thread this person has waiting, each in its own transaction.

    One per transaction so a failure costs only that thread, which stays unclaimed. Stops at
    the first failure rather than retrying the same thread in a loop. Failures are logged,
    never raised: a missing memory costs Mani some context, and must never fail the chat
    that triggered it. Transcript content is never logged.
    """
    from mani.db import pool

    folded = 0
    try:
        while folded < MAX_FOLDS_PER_RUN:
            async with pool.as_user(claims) as conn:
                if not await fold_one(conn, claims.user_id, keep=keep, idle_before=idle_before):
                    return folded
            folded += 1
        logger.warning("memory fold stopped at %d threads for user %s", folded, claims.user_id)
        return folded
    except Exception:
        logger.exception("memory fold failed for user %s", claims.user_id)
        return folded
