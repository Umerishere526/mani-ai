# ABOUTME: Checks the summary call's user message carries only headings and keyed lines, and when the backstop runs.
# ABOUTME: Builds the message from fake rows, so no model call or database is needed.

import datetime as dt
import time
import uuid
from contextlib import asynccontextmanager

from mani import summarize
from mani.chat.techniques import Registry
from mani.db import pool, summaries
from mani.models.rows import Message, MessageRole, TechniqueTried, ThreadSummary
from mani.prompts.cache import Config
from mani.summarize import request
from tests.seeded import seeded_replies, seeded_tuning

USER = uuid.UUID("a0000000-0000-4000-8000-00000000000a")
THREAD = uuid.UUID("b0000000-0000-4000-8000-00000000000b")
NOW = dt.datetime(2026, 10, 7, tzinfo=dt.UTC)


def message(role: MessageRole, content: str) -> Message:
    return Message(
        id=uuid.uuid4(), thread_id=THREAD, user_id=USER, role=role, content=content, created_at=NOW
    )


NEW = [message(MessageRole.USER, "my manager took credit again"), message(MessageRole.MANI, "What happened?")]


def test_a_thread_with_no_summary_yet_sends_only_the_new_messages():
    for nothing in (None, ThreadSummary(thread_id=THREAD, user_id=USER)):
        assert request(nothing, NEW) == (
            "## New Messages\nUser: my manager took credit again\n\nAssistant: What happened?"
        )


def test_an_existing_summary_is_sent_as_keyed_lines_above_the_new_messages():
    existing = ThreadSummary(
        thread_id=THREAD, user_id=USER, summary="Talked about work.",
        current_issue="Missed credit at work.",
        techniques_tried=[TechniqueTried(name="abcde", helpful=False)],
    )
    assert request(existing, NEW) == (
        "## Existing Summary\ncurrent_issue: Missed credit at work.\nsummary: Talked about work.\n"
        "techniques_tried: abcde (not_helpful)\n\n"
        "## New Messages\nUser: my manager took credit again\n\nAssistant: What happened?"
    )


async def test_the_backstop_catches_up_threads_at_the_tuned_context_window(monkeypatch):
    """The turn refreshes a summary every `context_window` messages; the cron backstop must use the
    same number, or a message could be outside both the history and the summary."""
    config = Config(
        prompts={}, registry=Registry([]), loaded_at=time.monotonic(),
        replies=seeded_replies(), tuning=seeded_tuning(windows={"context_window": 4}),
    )
    asked = {}

    async def load():
        return config

    @asynccontextmanager
    async def admin():
        yield None

    async def due_for_summary(_conn, *, threshold, limit):
        asked["threshold"] = threshold
        return []

    monkeypatch.setattr(summarize.cache, "load", load)
    monkeypatch.setattr(pool, "as_admin", admin)
    monkeypatch.setattr(summaries, "due_for_summary", due_for_summary)

    assert await summarize.reconcile_due() == 0
    assert asked == {"threshold": 4}
