# ABOUTME: Checks that seeding a prompt keeps the history of which prompt was live when: a changed prompt file puts
# ABOUTME: the row it replaces into admin.prompt_versions, and an unchanged one writes nothing. Rolled back after.

import asyncpg
import pytest

from mani.config import get_settings
from scripts.seed import seed_prompt
from tests.integration.fixtures import reachable

NAME = "seed_history_test_prompt"


def prompt_file(content: str, effort: str = "high") -> dict:
    return {"id": None, "name": NAME, "description": "", "content": content, "model_id": "some/model",
            "model_parameters": {"reasoning_effort": effort}, "routing": {"zdr": True}}


@pytest.fixture
async def conn():
    """A plain connection, as the seed opens one, inside a transaction that is never committed."""
    if not await reachable():
        pytest.skip("no database reachable; run `supabase start`")
    connection = await asyncpg.connect(get_settings().database_url)
    transaction = connection.transaction()
    await transaction.start()
    try:
        yield connection
    finally:
        await transaction.rollback()
        await connection.close()


async def history(conn: asyncpg.Connection) -> list[tuple[int, str, str]]:
    rows = await conn.fetch(
        "select v.version, v.content, v.model_parameters->>'reasoning_effort' as effort "
        "from admin.prompt_versions v join admin.prompts p on p.id = v.prompt_id where p.name = $1 order by v.version",
        NAME)
    return [(r["version"], r["content"], r["effort"]) for r in rows]


async def test_a_reseeded_prompt_keeps_what_it_replaced_and_an_unchanged_one_writes_nothing(conn):
    assert await seed_prompt(conn, prompt_file("first"), "content/prompts/test.md") == 1
    assert await seed_prompt(conn, prompt_file("first"), "content/prompts/test.md") == 1
    assert await history(conn) == []

    assert await seed_prompt(conn, prompt_file("second"), "content/prompts/test.md") == 2
    assert await seed_prompt(conn, prompt_file("second", effort="low"), "content/prompts/test.md") == 3

    assert await history(conn) == [(1, "first", "high"), (2, "second", "high")]
    assert await conn.fetchval(
        "select change_summary from admin.prompt_versions v join admin.prompts p on p.id = v.prompt_id "
        "where p.name = $1 and v.version = 1", NAME) == "replaced by the seed of content/prompts/test.md"
