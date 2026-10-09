# ABOUTME: Records each model call's cost and outcome, one row per provider call.
# ABOUTME: Links each recorded call to the reply it produced once that reply is stored.

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
    MEMORY_FOLD = "memory_fold"


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    # The share of output_tokens the model spent thinking before it answered, never on top.
    reasoning_tokens: int = 0


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
            (thread_id, user_id, purpose, model,
             input_tokens, output_tokens, cached_input_tokens, reasoning_tokens,
             latency_ms, outcome, error_message)
        values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        returning id
        """,
        thread_id, user_id, purpose.value, model,
        usage.input_tokens, usage.output_tokens, usage.cached_input_tokens,
        usage.reasoning_tokens, latency_ms, outcome.value, error_message,
    )


async def attach_message(
    conn: asyncpg.Connection,
    call_id: uuid.UUID | str,
    message_id: uuid.UUID | str,
    *,
    reported_stages: dict[str, str] | None = None,
    stage: str | None = None,
) -> None:
    """Link a recorded call to the message it produced, with what the turn recorded of the stages.

    The call is logged before the message exists, so the link is made afterwards. It is
    what lets an incident ask which call, model and cost produced a particular reply.
    `reported_stages` is what the reply reported of each stage, as the guard kept it, and `stage`
    the phase the turn stored: ids and statuses only, so a run can be read turn by turn after it ends.
    """
    await conn.execute(
        "update admin.llm_calls set message_id = $2, reported_stages = $3, stage = $4 where id = $1",
        call_id, message_id, reported_stages, stage,
    )

