# ABOUTME: Runs work after a response, independent of the request that triggered it.
# ABOUTME: Not FastAPI's BackgroundTasks - see fire_and_forget for why.

from __future__ import annotations

import logging
from collections.abc import Coroutine
from typing import Any

logger = logging.getLogger(__name__)

# A task not referenced anywhere may be garbage-collected mid-run - this set is that
# reference, for the whole lifetime of the process. Tasks remove themselves on completion.
_pending: set[Any] = set()


def fire_and_forget(coro: Coroutine[Any, Any, Any], *, name: str | None = None) -> None:
    """Schedule background work that does not wait on this request's own cleanup.

    FastAPI's `BackgroundTasks` are awaited to completion *before* a route's `Depends`
    dependencies with `yield` run their exit code - which is where `UserConn`'s transaction
    actually commits. A task that reads or references what this request just wrote (a
    message, in this codebase) is not merely racing that commit, it is sequenced strictly
    ahead of it: the commit cannot happen until the background task returns. Confirmed
    live - `orchestrator.link_call`, scheduled as a `BackgroundTasks` entry, hit a foreign
    key violation on the message it wanted to reference on every single turn, and retrying
    within it for up to 250ms never once succeeded, because the row it was waiting for was
    never going to become visible during that window no matter how long it waited.

    `asyncio.create_task` has no such relationship to the response: it is scheduled on the
    loop independently, so the transaction's commit and this task's first attempt are free
    to interleave normally. A short retry inside the task is a reasonable safety margin
    against ordinary scheduling variance; it is not compensating for a structural block.
    """
    import asyncio

    task = asyncio.create_task(coro, name=name)
    _pending.add(task)

    def _done(finished: "asyncio.Task[Any]") -> None:
        _pending.discard(finished)
        exc = finished.exception() if not finished.cancelled() else None
        if exc is not None:
            logger.exception("background task %s failed", name or finished.get_name(), exc_info=exc)

    task.add_done_callback(_done)
