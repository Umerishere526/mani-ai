# ABOUTME: Fixtures for whole-turn tests: the test person against a live database, and a scripted model installed in
# ABOUTME: place of the provider call. Skips when no database is reachable.

import pytest

from mani.llm import client
from tests.integration.cleanup import remove_test_users
from tests.integration.fixtures import ALICE, ScriptedModel, claims_for, reachable


@pytest.fixture
async def alice():
    if not await reachable():
        pytest.skip("no database reachable; run `supabase start`")
    from mani.db import pool

    await pool.open_pool()
    async with pool.as_admin() as conn:
        await remove_test_users(conn, ALICE)
        await conn.execute("insert into auth.users (id, email) values ($1, 'd1@t.test')", ALICE)
    try:
        yield claims_for(ALICE)
    finally:
        async with pool.as_admin() as conn:
            await remove_test_users(conn, ALICE)
        await pool.close_pool()


@pytest.fixture
def model(monkeypatch):
    def install(*replies) -> ScriptedModel:
        scripted = ScriptedModel(*replies)
        monkeypatch.setattr(client, "complete", scripted)
        return scripted

    return install
