# ABOUTME: Checks that a model call's link to its message, written after the turn commits, never fails the reply.
# ABOUTME: No database - pool.as_admin and attach_message are both faked.

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import asyncpg
import pytest

from mani.chat import turn
from mani.db import llm_calls


@pytest.fixture(autouse=True)
def admin_pool(monkeypatch):
    """Fakes pool.as_admin() so link_call never needs a real connection.

    link_call does `from mani.db import pool` inside the function body, so patching the
    module attribute is what a local import will actually see at call time.
    """
    import mani.db.pool as pool_module

    @asynccontextmanager
    async def fake_as_admin():
        yield object()

    monkeypatch.setattr(pool_module, "as_admin", fake_as_admin)


async def test_a_link_that_cannot_be_stored_is_logged_and_never_raised(monkeypatch, caplog):
    calls = {"n": 0}

    async def refused(conn, call_id, message_id):
        calls["n"] += 1
        raise asyncpg.ForeignKeyViolationError("message_id is not present")

    monkeypatch.setattr(llm_calls, "attach_message", refused)

    with caplog.at_level(logging.WARNING, logger=turn.logger.name):
        await turn.link_call(call_id="c", message_id="m")

    assert calls["n"] == 1
    assert [r.getMessage() for r in caplog.records] == ["could not store the link from llm call c to message m"]
