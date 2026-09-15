# ABOUTME: Thread reads and writes, including the composed state a turn needs.
# ABOUTME: Writes are collected into ThreadUpdates and applied once, not scattered.

from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass, field
from typing import Any

import asyncpg

from mani.models.rows import (
    Profile,
    ResponseStyle,
    TechniqueOutcome,
    TechniqueState,
    Thread,
    ThreadSummary,
)

COLUMNS = (
    "id, user_id, title, message_count, crisis_detected, "
    "created_at, last_message_at, deleted_at"
)

DEFAULT_PAGE = 20
# How many recent reply shapes the model is shown, to keep it from repeating itself.
STYLE_WINDOW = 7


@dataclass(frozen=True)
class Page:
    threads: list[Thread]
    next_cursor: str | None


async def list_for_user(
    conn: asyncpg.Connection,
    user_id: uuid.UUID | str,
    limit: int = DEFAULT_PAGE,
    cursor: dt.datetime | None = None,
) -> Page:
    rows = await conn.fetch(
        f"""
        select {COLUMNS} from public.threads
         where user_id = $1
           and deleted_at is null
           and ($2::timestamptz is null or last_message_at < $2)
         order by last_message_at desc
         limit $3
        """,
        user_id, cursor, limit + 1,
    )
    has_more = len(rows) > limit
    page = Thread.from_records(rows[:limit])
    next_cursor = page[-1].last_message_at.isoformat() if has_more and page else None
    return Page(threads=page, next_cursor=next_cursor)


async def get(
    conn: asyncpg.Connection, thread_id: uuid.UUID | str, user_id: uuid.UUID | str
) -> Thread | None:
    row = await conn.fetchrow(
        f"select {COLUMNS} from public.threads "
        "where id = $1 and user_id = $2 and deleted_at is null",
        thread_id, user_id,
    )
    return Thread.from_record(row)


async def most_recent(
    conn: asyncpg.Connection, user_id: uuid.UUID | str
) -> Thread | None:
    row = await conn.fetchrow(
        f"select {COLUMNS} from public.threads "
        "where user_id = $1 and deleted_at is null "
        "order by last_message_at desc limit 1",
        user_id,
    )
    return Thread.from_record(row)


async def create_or_reuse(
    conn: asyncpg.Connection, user_id: uuid.UUID | str, title: str | None = None
) -> tuple[Thread, bool]:
    """The caller's newest unused thread, or a fresh one. Returns (thread, created).

    "New chat" is idempotent while nothing has been said: tapping it repeatedly returns
    the same empty thread instead of leaving a trail of them. One statement, so the two
    halves cannot disagree - the implementation this replaces counted, then decided, then
    inserted, across three round trips.

    A thread is unused when it holds no message from the person. Mani's greeting does not
    count, or a thread would stop being reusable the moment it was opened.
    """
    row = await conn.fetchrow(
        f"""
        with reusable as (
            select {COLUMNS} from public.threads t
             where t.user_id = $1
               and t.deleted_at is null
               and not exists (
                 select 1 from public.messages m
                  where m.thread_id = t.id and m.role = 'user'
               )
             order by t.last_message_at desc
             limit 1
        ), created as (
            insert into public.threads (user_id, title)
            select $1, $2
             where not exists (select 1 from reusable)
            returning {COLUMNS}
        )
        select {COLUMNS}, false as created from reusable
        union all
        select {COLUMNS}, true as created from created
        """,
        user_id, title,
    )
    values = dict(row)
    return Thread.model_validate(values), values.pop("created")


async def soft_delete(
    conn: asyncpg.Connection, thread_id: uuid.UUID | str, user_id: uuid.UUID | str
) -> bool:
    """Mark a thread deleted rather than removing it.

    Retention and real erasure are a separate mechanism; this is what a person sees
    when they delete a conversation.
    """
    result = await conn.execute(
        "update public.threads set deleted_at = now() "
        "where id = $1 and user_id = $2 and deleted_at is null",
        thread_id, user_id,
    )
    return result.endswith(" 1")


# ---------------------------------------------------------------------------
# The composed read
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TurnContext:
    """Everything about a thread a turn needs, fetched together.

    The previous implementation read these as separate round trips and then kept a
    mutable in-memory mirror that drifted from the database within a single request.
    One read, one immutable snapshot.
    """

    thread: Thread
    profile: Profile | None
    technique: TechniqueState | None
    techniques_offered: list[str] = field(default_factory=list)
    recent_styles: list[ResponseStyle] = field(default_factory=list)
    summary: ThreadSummary | None = None


_TURN_CONTEXT_SQL = f"""
select
  to_jsonb(t) - 'x'                                as thread,
  (select to_jsonb(p) from public.profiles p
    where p.user_id = t.user_id)                   as profile,
  (select to_jsonb(s) from public.thread_technique_state s
    where s.thread_id = t.id)                      as technique,
  coalesce((select jsonb_agg(o.framework_id order by o.offered_at)
    from public.thread_techniques_offered o
    where o.thread_id = t.id), '[]'::jsonb)        as techniques_offered,
  coalesce((select jsonb_agg(to_jsonb(style) order by style.created_at)
    from (select shape, voice, created_at
            from public.thread_response_styles rs
           where rs.thread_id = t.id
           order by rs.created_at desc
           limit {STYLE_WINDOW}) style), '[]'::jsonb) as recent_styles,
  (select to_jsonb(sm) from public.thread_summaries sm
    where sm.thread_id = t.id)                     as summary
from (select {COLUMNS} from public.threads
       where id = $1 and user_id = $2 and deleted_at is null) t
"""


async def load_turn_context(
    conn: asyncpg.Connection, thread_id: uuid.UUID | str, user_id: uuid.UUID | str
) -> TurnContext | None:
    row = await conn.fetchrow(_TURN_CONTEXT_SQL, thread_id, user_id)
    if row is None or row["thread"] is None:
        return None

    return TurnContext(
        thread=Thread.model_validate(row["thread"]),
        profile=Profile.model_validate(row["profile"]) if row["profile"] else None,
        technique=TechniqueState.model_validate(row["technique"])
        if row["technique"] else None,
        techniques_offered=list(row["techniques_offered"] or []),
        recent_styles=[
            ResponseStyle.model_validate(s) for s in row["recent_styles"] or []
        ],
        summary=ThreadSummary.model_validate(row["summary"]) if row["summary"] else None,
    )


# ---------------------------------------------------------------------------
# The composed write
# ---------------------------------------------------------------------------


@dataclass
class ThreadUpdates:
    """What a turn changed, applied in one go at the end of the transaction.

    The previous implementation issued up to fourteen writes per turn, thirteen of
    them unprotected, several of them before the model had even been called - so a
    failure left the thread describing a turn that never happened. Collecting them
    means they land together or not at all.
    """

    title: str | None = None
    technique: TechniqueState | None = None
    clear_technique: bool = False
    offer_frameworks: list[str] = field(default_factory=list)
    style: ResponseStyle | None = None
    library_offered: bool = False

    def __bool__(self) -> bool:
        return any([
            self.title, self.technique, self.clear_technique,
            self.offer_frameworks, self.style, self.library_offered,
        ])


async def apply(
    conn: asyncpg.Connection,
    thread_id: uuid.UUID | str,
    user_id: uuid.UUID | str,
    updates: ThreadUpdates,
) -> None:
    if not updates:
        return

    if updates.title is not None:
        await conn.execute(
            "update public.threads set title = $1 where id = $2 and user_id = $3",
            updates.title, thread_id, user_id,
        )

    if updates.clear_technique:
        await conn.execute(
            "delete from public.thread_technique_state where thread_id = $1", thread_id
        )
    elif updates.technique is not None:
        t = updates.technique
        await conn.execute(
            """
            insert into public.thread_technique_state
                (thread_id, user_id, framework_id, outcome, phase,
                 at_message_count, library_offered_since)
            values ($1, $2, $3, $4, $5, $6, $7)
            on conflict (thread_id) do update set
                framework_id         = excluded.framework_id,
                outcome              = excluded.outcome,
                phase                = excluded.phase,
                at_message_count     = excluded.at_message_count,
                library_offered_since = excluded.library_offered_since
            """,
            thread_id, user_id, t.framework_id, t.outcome.value, t.phase,
            t.at_message_count, t.library_offered_since,
        )

    if updates.offer_frameworks:
        # One statement. The previous version read the whole row, merged in
        # JavaScript and wrote it back, losing an entry whenever two turns overlapped.
        await conn.executemany(
            """
            insert into public.thread_techniques_offered (thread_id, framework_id, user_id)
            values ($1, $2, $3)
            on conflict (thread_id, framework_id) do nothing
            """,
            [(thread_id, fid, user_id) for fid in updates.offer_frameworks],
        )

    if updates.style is not None:
        await conn.execute(
            "insert into public.thread_response_styles (thread_id, user_id, shape, voice) "
            "values ($1, $2, $3, $4)",
            thread_id, user_id, updates.style.shape, updates.style.voice,
        )

    if updates.library_offered:
        await conn.execute(
            "update public.thread_technique_state set library_offered_since = true "
            "where thread_id = $1",
            thread_id,
        )


async def mark_crisis(
    conn: asyncpg.Connection,
    thread_id: uuid.UUID | str,
    reason: str,
    message_id: uuid.UUID | str | None = None,
) -> uuid.UUID:
    """Flag the thread and record the event. There is no matching unflag."""
    return await conn.fetchval(
        "select public.mark_thread_crisis($1, $2, $3)", thread_id, reason, message_id
    )


async def set_technique_outcome(
    conn: asyncpg.Connection,
    thread_id: uuid.UUID | str,
    user_id: uuid.UUID | str,
    framework_id: str,
    outcome: TechniqueOutcome,
    at_message_count: int,
    phase: str | None = None,
) -> None:
    """Convenience for the common single-field change."""
    await apply(
        conn, thread_id, user_id,
        ThreadUpdates(technique=TechniqueState(
            thread_id=thread_id if isinstance(thread_id, uuid.UUID) else uuid.UUID(str(thread_id)),
            framework_id=framework_id,
            outcome=outcome,
            phase=phase,
            at_message_count=at_message_count,
        )),
    )
