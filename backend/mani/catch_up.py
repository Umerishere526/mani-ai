# ABOUTME: Finishes on a schedule what a reply or a chat left behind and the app never asked for.
# ABOUTME: Each piece runs as the person it belongs to, so RLS scopes every write as it does their own requests.

from __future__ import annotations

import asyncio
import datetime as dt
import logging

from mani import memory, summarize
from mani.auth.jwt import Claims
from mani.chat import orchestrator
from mani.db import pool, threads

logger = logging.getLogger(__name__)

# How long the app has to ask for a reply's follow-up itself before the schedule runs it.
QUIET_AFTER = dt.timedelta(minutes=5)
# Work still waiting this long after its reply is left alone, so one that always fails is not paid for every run.
GIVE_UP_AFTER = dt.timedelta(hours=1)
# Most items each job starts in one run; raise it if the logged counts show a backlog.
LIMIT = 10
# Every job stops here, inside a function's 300 s, so the run reports and its claims expire rather than being cut
# off by the platform; what it did not reach waits for the next run.
RUN_SECONDS = 240


async def follow_ups(limit: int = LIMIT) -> int:
    """Run the readings and summaries still waiting on replies gone quiet; how many finished. One the app or another
    run has claimed meanwhile is passed over, and one whose part failed stays waiting for the next run."""
    now = dt.datetime.now(dt.UTC)
    async with pool.as_admin() as conn:
        waiting = await threads.waiting_follow_ups(conn, now - QUIET_AFTER, now - GIVE_UP_AFTER, limit)
    ran = 0
    for row in waiting:
        done = await orchestrator.follow_up(Claims.acting_as(row["user_id"]), row["thread_id"], row["message_id"])
        if done is not None and not done.pending:
            ran += 1
    return ran


async def run() -> dict[str, int | None]:
    """Every catch-up, side by side: summaries fallen behind, follow-ups never asked for, and quiet chats to fold.
    Each count is None for a job stopped at the run's budget."""
    summaries, ran, folded = await asyncio.gather(
        _within_budget("summaries", summarize.reconcile_due(limit=LIMIT)),
        _within_budget("follow-ups", follow_ups()),
        _within_budget("memory folds", memory.fold_idle(limit=LIMIT)),
    )
    return {"summaries": summaries, "follow_ups": ran, "folded": folded}


async def _within_budget(job: str, work) -> int | None:
    try:
        return await asyncio.wait_for(work, RUN_SECONDS)
    except TimeoutError:
        logger.warning("catch-up %s stopped at the run's budget of %d s", job, RUN_SECONDS)
        return None
