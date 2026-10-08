# ABOUTME: Checks a portal edit cannot leave a model call without a thinking level, or a required row broken.
# ABOUTME: Runs the real admin writes against the live database; every write is rolled back.

import pytest

from mani.db import config_tables
from mani.errors import ErrorCategory, ServiceError
from tests.integration.test_turn import reachable


class RolledBack(Exception):
    """Raised at the end of a write that passed, so the seeded rows are left as they were."""


@pytest.fixture
async def pool():
    if not await reachable():
        pytest.skip("no database reachable; run `supabase start`")
    from mani.db import pool

    await pool.open_pool()
    try:
        yield pool
    finally:
        await pool.close_pool()


async def row_id(pool, name: str):
    async with pool.as_admin() as conn:
        return await conn.fetchval("select id from admin.prompts where name = $1", name)


async def versions_of(pool, prompt_id) -> int:
    async with pool.as_admin() as conn:
        return await conn.fetchval(
            "select count(*) from admin.prompt_versions where prompt_id = $1", prompt_id
        )


async def refused(pool, write) -> ServiceError:
    """Run a write the way the admin routes do, in one transaction, expecting a 422."""
    with pytest.raises(ServiceError) as raised:
        async with pool.as_admin() as conn:
            await write(conn)
    assert raised.value.category is ErrorCategory.INVALID_REQUEST
    return raised.value


async def passes(pool, write):
    with pytest.raises(RolledBack):
        async with pool.as_admin() as conn:
            await write(conn)
            raise RolledBack


@pytest.mark.parametrize("changes", [
    {"model_parameters": {"maxTokens": 800}},
    {"model_parameters": {"reasoning_effort": ["high"]}},
    {"model_parameters": {"reasoning_effort": "extreme"}},
    {"name": "fold_paused"},
    {"is_active": False},
])
async def test_an_edit_that_would_break_a_call_row_is_refused_with_nothing_saved(pool, changes):
    """The portal replaces model_parameters whole, so one careless save drops the level; and a
    renamed or inactive call row is a call with no row. The version snapshot goes back too."""
    memory_fold = await row_id(pool, "memory_fold")
    before = await versions_of(pool, memory_fold)

    await refused(pool, lambda conn: config_tables.update_prompt(conn, memory_fold, changes))

    assert await versions_of(pool, memory_fold) == before


async def test_a_layer_renamed_to_a_call_name_is_checked_as_a_call(pool):
    """The check runs on the row after the edit, so the name it ends up with is what counts."""
    layer = await row_id(pool, "title_generation")

    async def rename(conn):
        await conn.execute(
            "update admin.prompts set name = 'memory_fold_parked' where name = 'memory_fold'"
        )
        await config_tables.update_prompt(conn, layer, {"name": "memory_fold"})

    await refused(pool, rename)


async def test_a_new_call_row_without_parameters_is_refused(pool):
    async def create(conn):
        await conn.execute("delete from admin.prompts where name = 'voice_translation'")
        await config_tables.create_prompt(
            conn, name="voice_translation", content="Translate.", model_parameters=None
        )

    await refused(pool, create)


async def test_edits_that_keep_a_call_usable_pass(pool):
    """A content edit to a call row, and any edit to a layer row, are the portal's everyday work."""
    memory_fold = await row_id(pool, "memory_fold")
    layer = await row_id(pool, "response_format")

    async def edit(conn):
        kept = await config_tables.update_prompt(conn, memory_fold, {"content": "Fold it."})
        assert kept.model_parameters["reasoning_effort"] == "high"
        await config_tables.update_prompt(conn, layer, {"model_parameters": {}})

    await passes(pool, edit)


@pytest.mark.parametrize(("name", "changes"), [
    ("tuning", {"content": "windows: {context_window: 3}"}),
    ("replies", {"content": "greeting: {new: 'Hi {nickname}'}"}),
    ("mani_base", {"content": "identity: [no shapes here]"}),
    ("response_format", {"is_active": False}),
    ("replies", {"is_active": False}),
    ("replies", {"name": "replies_parked"}),
    ("tuning", {"name": "tuning_parked"}),
])
async def test_an_edit_that_would_break_a_required_row_is_refused_with_nothing_saved(
    pool, name, changes
):
    """A turn cannot run without these rows, so a typo or a toggle in the portal is refused when
    written, and the version snapshot goes back with it."""
    row = await row_id(pool, name)
    before = await versions_of(pool, row)

    await refused(pool, lambda conn: config_tables.update_prompt(conn, row, changes))

    assert await versions_of(pool, row) == before
    async with pool.as_admin() as conn:
        stored = await config_tables.get_prompt_by_id(conn, row)
    assert (stored.name, stored.is_active) == (name, True)


async def test_a_refusal_for_a_bad_number_names_the_key_and_not_the_value(pool):
    row = await row_id(pool, "tuning")

    problem = await refused(
        pool,
        lambda conn: config_tables.update_prompt(conn, row, {"content": "windows: {context_window: 987654}"}),
    )

    assert "windows" in problem.user_message
    assert "987654" not in problem.user_message


async def test_an_edit_that_keeps_a_required_row_usable_passes(pool):
    row = await row_id(pool, "tuning")

    async def edit(conn):
        current = await config_tables.get_prompt_by_id(conn, row)
        changed = current.content.replace("context_window: 20", "context_window: 30")
        kept = await config_tables.update_prompt(conn, row, {"content": changed})
        assert "context_window: 30" in kept.content

    await passes(pool, edit)
