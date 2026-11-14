# ABOUTME: Thread reads and writes, including the composed state a turn needs.
# ABOUTME: Writes are collected into ThreadUpdates and applied once, not scattered.

from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass, field

import asyncpg

from mani.llm.schema import Memory
from mani.models.rows import (
    Pause,
    Profile,
    SupportStyle,
    TechniqueState,
    Thread,
    ThreadSummary,
)

COLUMNS = (
    "id, user_id, title, message_count, crisis_detected, "
    "created_at, last_message_at, deleted_at, conversation_style"
)

DEFAULT_PAGE = 20

# A thread is listed once the person has written in it. Mani's greeting and a style button they tapped (stored with
# `selected_prompt`) do not count. Refers to the thread as `t`.
WRITTEN_IN = """exists (
    select 1 from public.messages m
     where m.thread_id = t.id and m.role = 'user' and m.selected_prompt is null)"""


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
        select {COLUMNS} from public.threads t
         where user_id = $1
           and deleted_at is null
           and {WRITTEN_IN}
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


async def understanding_of(
    conn: asyncpg.Connection, thread_id: uuid.UUID | str, user_id: uuid.UUID | str
) -> dict | None:
    """What Mani understands of them as stored now, or None when the thread is gone."""
    row = await conn.fetchrow(
        "select understanding from public.threads where id = $1 and user_id = $2 and deleted_at is null",
        thread_id, user_id,
    )
    return None if row is None else dict(row["understanding"] or {})


async def set_pending_follow_up(
    conn: asyncpg.Connection, thread_id: uuid.UUID | str, user_id: uuid.UUID | str, follow_up: dict | None
) -> dict | None:
    """Store what is left to do after this turn's reply, for the app to ask for, or clear the last with None. Returns
    what was waiting before, which this replaces."""
    return await conn.fetchval(
        """
        with before as (
            select pending_follow_up from public.threads where id = $2 and user_id = $3 for update
        )
        update public.threads t set pending_follow_up = $1::jsonb
          from before where t.id = $2 and t.user_id = $3
        returning before.pending_follow_up
        """,
        follow_up, thread_id, user_id,
    )


# How long a claimed follow-up is left alone: past the model's own deadline, so a request still working is never
# run a second time, and one that died frees its work for the next request.
FOLLOW_UP_CLAIM_SECONDS = 120


async def claim_pending_follow_up(
    conn: asyncpg.Connection, thread_id: uuid.UUID | str, user_id: uuid.UUID | str, message_id: uuid.UUID | str
) -> dict | None:
    """What is left to do after Mani's reply `message_id`, marked as claimed so no second request runs it meanwhile;
    None when nothing waits, what waits is for another reply, or another request holds the claim. It stays on the
    thread until `settle_pending_follow_up`, so a request that fails or dies loses nothing."""
    row = await conn.fetchrow(
        """
        with waiting as (
            select id, pending_follow_up from public.threads
            where id = $1 and user_id = $2 and deleted_at is null
              and pending_follow_up ->> 'message_id' = $3::text
              and coalesce((pending_follow_up ->> 'claimed_at')::timestamptz, '-infinity')
                  < now() - make_interval(secs => $4::float8)
            for update
        )
        update public.threads t
           set pending_follow_up = waiting.pending_follow_up || jsonb_build_object('claimed_at', now())
          from waiting where t.id = waiting.id
        returning waiting.pending_follow_up
        """,
        thread_id, user_id, str(message_id), float(FOLLOW_UP_CLAIM_SECONDS),
    )
    return None if row is None else row["pending_follow_up"]


async def waiting_follow_ups(
    conn: asyncpg.Connection, quiet_since: dt.datetime, given_up_before: dt.datetime, limit: int
) -> list[asyncpg.Record]:
    """Threads whose follow-up still waits on a reply that has been quiet since `quiet_since`, oldest first, and not
    so long that it was given up on, nor claimed by a request still running it: thread_id, user_id and the reply's
    message_id. Cross-user, so admin-only."""
    return await conn.fetch(
        """
        select id as thread_id, user_id, pending_follow_up ->> 'message_id' as message_id
          from public.threads
         where pending_follow_up is not null and deleted_at is null
           and last_message_at < $1 and last_message_at >= $2
           and coalesce((pending_follow_up ->> 'claimed_at')::timestamptz, '-infinity')
               < now() - make_interval(secs => $4::float8)
         order by last_message_at
         limit $3
        """,
        quiet_since, given_up_before, limit, float(FOLLOW_UP_CLAIM_SECONDS),
    )


async def settle_pending_follow_up(
    conn: asyncpg.Connection,
    thread_id: uuid.UUID | str,
    user_id: uuid.UUID | str,
    message_id: uuid.UUID | str,
    remaining: dict | None,
) -> None:
    """Leave only what is still to do after reply `message_id`, unclaimed so the next request may run it, or clear it
    with None. A newer turn's follow-up is never touched."""
    await conn.execute(
        "update public.threads set pending_follow_up = $1::jsonb "
        "where id = $2 and user_id = $3 and pending_follow_up ->> 'message_id' = $4::text",
        remaining, thread_id, user_id, str(message_id),
    )


async def most_recent(
    conn: asyncpg.Connection, user_id: uuid.UUID | str
) -> Thread | None:
    row = await conn.fetchrow(
        f"select {COLUMNS} from public.threads t "
        f"where user_id = $1 and deleted_at is null and {WRITTEN_IN} "
        "order by last_message_at desc limit 1",
        user_id,
    )
    return Thread.from_record(row)


async def create(
    conn: asyncpg.Connection, user_id: uuid.UUID | str, title: str | None = None
) -> Thread:
    """A new conversation with nothing in it yet."""
    row = await conn.fetchrow(
        f"insert into public.threads (user_id, title) values ($1, $2) returning {COLUMNS}",
        user_id, title,
    )
    return Thread.from_record(row)


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
    summary: ThreadSummary | None = None
    # Another of this person's conversations was flagged for crisis recently. Only the fact
    # crosses threads, never what was said in it.
    recent_crisis: bool = False
    # Patterns from this person's earlier conversations, folded in as each one finished.
    memory: Memory | None = None
    # The pauses this turn may owe the question whether they are all right for (chat/pause.return_check), each the
    # latest that has run out by the database's clock as the pause gate reads it, within RECENT_CRISIS_DAYS of its
    # end (an older one owes nothing): this person's, and this conversation's own. A reason is loaded only for a pause that began in this conversation.
    pause: Pause | None = None
    own_pause: Pause | None = None


# How long a crisis in one conversation keeps the next ones gentle, and how long a pause that has run out owes the
# question whether they are all right.
RECENT_CRISIS_DAYS = 30

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
  (select to_jsonb(sm) from public.thread_summaries sm
    where sm.thread_id = t.id)                     as summary,
  exists (select 1 from public.threads c
           where c.user_id = t.user_id and c.id <> t.id
             and c.crisis_at > now() - interval '{RECENT_CRISIS_DAYS} days')
                                                   as recent_crisis,
  (select um.memory from admin.user_memory um
    where um.user_id = t.user_id)                  as memory,
  (select jsonb_build_object(
            'id', cp.id, 'user_id', cp.user_id, 'thread_id', cp.thread_id, 'started_at', cp.started_at,
            'ends_at', cp.ends_at, 'checked_at', cp.checked_at,
            'reason', case when cp.thread_id = t.id then cp.reason end)
     from public.chat_pauses cp
    where cp.user_id = t.user_id and cp.ends_at <= now()
      and cp.ends_at > now() - interval '{RECENT_CRISIS_DAYS} days'
    order by cp.started_at desc limit 1)          as pause,
  (select to_jsonb(cp) from public.chat_pauses cp
    where cp.thread_id = t.id and cp.user_id = t.user_id and cp.ends_at <= now()
      and cp.ends_at > now() - interval '{RECENT_CRISIS_DAYS} days'
    order by cp.started_at desc limit 1)          as own_pause
from (select {COLUMNS}, understanding, check_at_message_count, safety from public.threads
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
        summary=ThreadSummary.model_validate(row["summary"]) if row["summary"] else None,
        recent_crisis=row["recent_crisis"],
        memory=Memory.model_validate(row["memory"]) if row["memory"] else None,
        pause=Pause.model_validate(row["pause"]) if row["pause"] else None,
        own_pause=Pause.model_validate(row["own_pause"]) if row["own_pause"] else None,
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
    retire_technique: bool = False
    offer_frameworks: list[str] = field(default_factory=list)
    # What the body check-in found, set only on the turn that answers its step, never overwritten within a run.
    physical_response: str | None = None
    conversation_effect: str | None = None
    # A new offer starts a new run, so the last run's two outcomes are cleared.
    reset_outcomes: bool = False
    conversation_style: SupportStyle | None = None
    # The whole stage store, set only when this turn's merge changed it.
    stages_known: dict | None = None
    # What Mani understands of them, set only when this turn's merge changed it.
    understanding: dict | None = None
    # Where the conversation stands on safety, set only when this turn moved it (chat/safety.after).
    safety: str | None = None
    # When Mani's check of its understanding was made, set only on the turn whose reply is one.
    check_at_message_count: int | None = None

    def __bool__(self) -> bool:
        # Each optional field is tested for presence, not for truth. A field whose
        # meaningful value is falsy - a zeroed counter, an empty title - would otherwise
        # make this report "nothing to do" and silently drop every other write with it.
        return (
            self.title is not None
            or self.technique is not None
            or self.retire_technique
            or bool(self.offer_frameworks)
            or self.physical_response is not None
            or self.conversation_effect is not None
            or self.reset_outcomes
            or self.conversation_style is not None
            or self.stages_known is not None
            or self.understanding is not None
            or self.safety is not None
            or self.check_at_message_count is not None
        )


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

    if updates.conversation_style is not None:
        # Its own column grant, added by migration 002 - the grant in 001 is
        # column-scoped and covers title, last_message_at and deleted_at only, so a
        # missing grant here would fail at runtime with 42501 and roll back the turn.
        await conn.execute(
            "update public.threads set conversation_style = $1 "
            "where id = $2 and user_id = $3",
            updates.conversation_style.value, thread_id, user_id,
        )

    if updates.retire_technique:
        # Retired, not removed. at_message_count is what the cooldown is measured from,
        # so deleting the row tells the next turn no technique has ever run and lets a
        # second framework start immediately. A finished technique is one whose outcome
        # is accepted and whose phase is null.
        await conn.execute(
            "update public.thread_technique_state set phase = null "
            "where thread_id = $1 and user_id = $2",
            thread_id, user_id,
        )
    elif updates.technique is not None:
        t = updates.technique
        await conn.execute(
            """
            insert into public.thread_technique_state
                (thread_id, user_id, framework_id, outcome, phase,
                 at_message_count)
            values ($1, $2, $3, $4, $5, $6)
            on conflict (thread_id) do update set
                framework_id         = excluded.framework_id,
                outcome              = excluded.outcome,
                phase                = excluded.phase,
                at_message_count     = excluded.at_message_count
            """,
            thread_id, user_id, t.framework_id, t.outcome.value, t.phase,
            t.at_message_count,
        )

    if updates.reset_outcomes:
        await conn.execute(
            "update public.thread_technique_state set physical_response = null, conversation_effect = null "
            "where thread_id = $1 and user_id = $2",
            thread_id, user_id,
        )
    for column, value in (
        ("physical_response", updates.physical_response), ("conversation_effect", updates.conversation_effect),
    ):
        if value is not None:
            # Its own statement per outcome, never part of the upsert above, so a later turn's upsert cannot
            # erase it; written once per run by mani_service (migration 025).
            await conn.execute(
                f"update public.thread_technique_state set {column} = $1 where thread_id = $2 and user_id = $3 "
                f"and {column} is null",
                value, thread_id, user_id,
            )

    if updates.stages_known is not None:
        # Its own statement after the upsert above, never part of it: a new offer row upserts over
        # a retired one, and the store has to survive that.
        await conn.execute(
            "update public.thread_technique_state set stages_known = $1::jsonb "
            "where thread_id = $2 and user_id = $3",
            updates.stages_known, thread_id, user_id,
        )

    if updates.safety is not None:
        await set_safety(conn, thread_id, user_id, updates.safety)
    if updates.understanding is not None:
        # Its own column grant, to mani_service only (migration 022).
        await conn.execute(
            "update public.threads set understanding = $1::jsonb where id = $2 and user_id = $3",
            updates.understanding, thread_id, user_id,
        )

    if updates.check_at_message_count is not None:
        # Its own column grant, to mani_service only (migration 023).
        await conn.execute(
            "update public.threads set check_at_message_count = $1 where id = $2 and user_id = $3",
            updates.check_at_message_count, thread_id, user_id,
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



async def set_safety(
    conn: asyncpg.Connection, thread_id: uuid.UUID | str, user_id: uuid.UUID | str, state: str
) -> None:
    """Where the conversation stands on safety: clear, unsure or danger (chat/safety.State)."""
    await conn.execute(
        "update public.threads set safety = $1 where id = $2 and user_id = $3", state, thread_id, user_id,
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
