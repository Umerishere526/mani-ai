# ABOUTME: Checks link_call's retry against the race it exists to survive.
# ABOUTME: No database - pool.as_admin and attach_message are both faked.

from __future__ import annotations

from contextlib import asynccontextmanager

import asyncpg
import pytest

from mani.chat import orchestrator
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


def not_found() -> asyncpg.PostgresError:
    # attach_message's real failure mode: the message row is not yet visible to this
    # connection, because the transaction that wrote it has not committed.
    return asyncpg.ForeignKeyViolationError("message_id not yet visible")


async def test_a_race_that_clears_on_the_second_attempt_still_links(monkeypatch):
    calls = {"n": 0}

    async def flaky(conn, call_id, message_id):
        calls["n"] += 1
        if calls["n"] < 2:
            raise not_found()

    monkeypatch.setattr(llm_calls, "attach_message", flaky)
    monkeypatch.setattr(orchestrator, "LINK_RETRY_DELAY_SECONDS", 0)

    await orchestrator.link_call(call_id="c", message_id="m")

    assert calls["n"] == 2


async def test_a_race_that_never_clears_gives_up_without_raising(monkeypatch):
    async def always_fails(conn, call_id, message_id):
        raise not_found()

    monkeypatch.setattr(llm_calls, "attach_message", always_fails)
    monkeypatch.setattr(orchestrator, "LINK_RETRY_DELAY_SECONDS", 0)

    # Never raises - a failed link costs a forensic record, not a delivered reply.
    await orchestrator.link_call(call_id="c", message_id="m")


async def test_a_clean_first_attempt_does_not_retry(monkeypatch):
    calls = {"n": 0}

    async def clean(conn, call_id, message_id):
        calls["n"] += 1

    monkeypatch.setattr(llm_calls, "attach_message", clean)

    await orchestrator.link_call(call_id="c", message_id="m")

    assert calls["n"] == 1
