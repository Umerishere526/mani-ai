# ABOUTME: The rolling thread summary that covers what has left the model's view of a long thread.
# ABOUTME: The checkpoint is a message id, enforced by a foreign key.

import uuid

import asyncpg

from mani.models.rows import TechniqueTried, ThreadSummary

COLUMNS = (
    "thread_id, user_id, summary, techniques_tried, "
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
            (thread_id, user_id, summary, techniques_tried,
             summarized_through_message_id, summarized_message_count)
        values ($1, $2, $3, $4::jsonb, $5, $6)
        on conflict (thread_id) do update set
            summary                       = excluded.summary,
            techniques_tried              = excluded.techniques_tried,
            summarized_through_message_id = excluded.summarized_through_message_id,
            summarized_message_count      = excluded.summarized_message_count
        returning {COLUMNS}
        """,
        thread_id, user_id, summary,
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


async def due_for_summary(
    conn: asyncpg.Connection, *, budget_chars: int, block: int, limit: int
) -> list[dict]:
    """Threads too long for the model's budget whose summary is a block or more behind, so some of
    what has left the model's view may be in no summary yet.

    Cross-user, so admin-only - the same reconciliation a per-turn trigger does for one
    thread, run here as a batch for whichever ones the per-turn trigger missed (the
    process restarted, or never ran at all, before its next turn came in).
    """
    rows = await conn.fetch(
        """
        select t.id as thread_id, t.user_id
          from public.threads t
          left join public.thread_summaries s on s.thread_id = t.id
         where t.message_count - coalesce(s.summarized_message_count, 0) >= $2
           and (select coalesce(sum(length(m.content)), 0) from public.messages m
                 where m.thread_id = t.id) > $1
         order by t.last_message_at
         limit $3
        """,
        budget_chars, block, limit,
    )
    return [dict(r) for r in rows]
