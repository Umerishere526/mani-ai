# ABOUTME: Checks the summary call's user message carries only headings and keyed lines.
# ABOUTME: Builds the message from fake rows, so no model call or database is needed.

import datetime as dt
import uuid

from mani.models.rows import Message, MessageRole, TechniqueTried, ThreadSummary
from mani.summarize import request

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
