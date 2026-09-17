# ABOUTME: Records what every model call cost and which prompt version produced it.
# ABOUTME: Nothing here existed before - usage went to a debug log and was lost.

import uuid
from dataclasses import dataclass
from enum import StrEnum

import asyncpg


class Outcome(StrEnum):
    OK = "ok"
    SCHEMA_INVALID = "schema_invalid"
    PROVIDER_ERROR = "provider_error"
    TIMEOUT = "timeout"


class Purpose(StrEnum):
    CHAT = "chat"
    SUMMARIZE = "summarize"
    EXERCISE_SELECT = "exercise_select"


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0


async def record(
    conn: asyncpg.Connection,
    *,
    purpose: Purpose,
    model: str,
    outcome: Outcome,
    usage: Usage,
    latency_ms: int,
    user_id: uuid.UUID | str | None = None,
    thread_id: uuid.UUID | str | None = None,
    message_id: uuid.UUID | str | None = None,
    prompt_version_id: uuid.UUID | str | None = None,
    error_message: str | None = None,
) -> uuid.UUID:
    """Write one row per provider call, successful or not.

    Failures are recorded too - a turn that cost money and produced nothing is exactly
    what you want to see when a bill or a latency graph moves. `error_message` carries
    the provider's reason, never the conversation.
    """
    return await conn.fetchval(
        """
        insert into admin.llm_calls
            (thread_id, user_id, message_id, prompt_version_id, purpose, model,
             input_tokens, output_tokens, cached_input_tokens, latency_ms,
             outcome, error_message)
        values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        returning id
        """,
        thread_id, user_id, message_id, prompt_version_id, purpose.value, model,
        usage.input_tokens, usage.output_tokens, usage.cached_input_tokens,
        latency_ms, outcome.value, error_message,
    )


async def attach_message(
    conn: asyncpg.Connection,
    call_id: uuid.UUID | str,
    message_id: uuid.UUID | str,
) -> None:
    """Link a recorded call to the message it produced.

    The call is logged before the message exists, so the link is made afterwards. It is
    what lets an incident ask which prompt version wrote a particular reply - a question
    the previous system could not answer at all.
    """
    await conn.execute(
        "update admin.llm_calls set message_id = $2 where id = $1", call_id, message_id
    )


async def spend_since(
    conn: asyncpg.Connection, user_id: uuid.UUID | str, hours: int = 24
) -> dict:
    """Token totals for one user over a window, for a per-user ceiling.

    The ceiling itself is still an open question - a number is needed to size the
    retry budget - but the measurement it depends on exists now.
    """
    row = await conn.fetchrow(
        """
        select coalesce(sum(input_tokens), 0)        as input_tokens,
               coalesce(sum(output_tokens), 0)       as output_tokens,
               coalesce(sum(cached_input_tokens), 0) as cached_input_tokens,
               count(*)                              as calls
          from admin.llm_calls
         where user_id = $1
           and created_at >= now() - make_interval(hours => $2)
        """,
        user_id, hours,
    )
    return dict(row)
