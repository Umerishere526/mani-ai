# ABOUTME: One scheduled catch-up run ends inside a function's time limit whatever its jobs do.
# ABOUTME: The three jobs are faked; what is under test is the run's own budget and what it reports.

import asyncio
import time

from mani import catch_up, memory, summarize


def test_a_job_that_runs_past_the_budget_is_stopped_and_the_others_still_report(monkeypatch):
    """Vercel ends the function at its limit and loses whatever the run had not reported; the run ends first."""

    async def stuck(**_):
        await asyncio.sleep(5)
        return 1

    async def quick(**_):
        return 2

    monkeypatch.setattr(catch_up, "RUN_SECONDS", 0.05)
    monkeypatch.setattr(summarize, "reconcile_due", stuck)
    monkeypatch.setattr(catch_up, "follow_ups", quick)
    monkeypatch.setattr(memory, "fold_idle", quick)

    started = time.monotonic()
    done = asyncio.run(catch_up.run())

    assert time.monotonic() - started < 1
    assert done == {"summaries": None, "follow_ups": 2, "folded": 2}
