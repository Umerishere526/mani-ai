# ABOUTME: The rolling thread summary that gives Mani memory beyond the recent window.
# ABOUTME: The checkpoint is a message id, enforced by a foreign key.

import uuid

import asyncpg

from mani.models.rows import TechniqueTried, ThreadSummary

COLUMNS = (
    "thread_id, user_id, summary, current_issue, techniques_tried, "
    "summarized_through_message_id, summarized_message_count"
)


async def get(
    conn: asyncpg.Connection, thread_id: uuid.UUID | str
) -> ThreadSummary | None:
    row = await conn.fetchrow(
        f"select {COLUMNS} from public.thread_summaries where thread_id = $1", thread_id
    )
    return ThreadSummary.from_record(row)


async def upsert(
    conn: asyncpg.Connection,
    thread_id: uuid.UUID | str,
    user_id: uuid.UUID | str,
    *,
    summary: str | None,
    techniques_tried: list[TechniqueTried],
    summarized_through_message_id: uuid.UUID | str | None,
    summarized_message_count: int,
    current_issue: str | None = None,
) -> ThreadSummary:
    """Replace the summary for a thread.

    `summarized_through_message_id` references public.messages. The previous
    implementation fell back to writing the summary row's own id into the equivalent
    column, so the next run found no checkpoint and re-summarized from the beginning.
    The foreign key now refuses that outright.
    """
    row = await conn.fetchrow(
        f"""
        insert into public.thread_summaries
            (thread_id, user_id, summary, current_issue, techniques_tried,
             summarized_through_message_id, summarized_message_count)
        values ($1, $2, $3, $4, $5::jsonb, $6, $7)
        on conflict (thread_id) do update set
            summary                       = excluded.summary,
            current_issue                 = excluded.current_issue,
            techniques_tried              = excluded.techniques_tried,
            summarized_through_message_id = excluded.summarized_through_message_id,
            summarized_message_count      = excluded.summarized_message_count
        returning {COLUMNS}
        """,
        thread_id, user_id, summary, current_issue,
        [t.model_dump() for t in techniques_tried],
        summarized_through_message_id, summarized_message_count,
    )
    return ThreadSummary.model_validate(dict(row))


def merge_techniques(
    existing: list[TechniqueTried], incoming: list[TechniqueTried]
) -> list[TechniqueTried]:
    """Combine technique records, newest winning, matched case-insensitively by name."""
    merged = {t.name.lower(): t for t in existing}
    for technique in incoming:
        merged[technique.name.lower()] = technique
    return list(merged.values())
