# ABOUTME: The migration that folds a worry's two kind keys into one, run inside a transaction that is rolled back: a
# ABOUTME: conversation with its worry open keeps its kind, and one settled carries none into its next worry.

import pathlib

import pytest

from tests.integration.fixtures import start

MIGRATION = pathlib.Path(__file__).resolve().parents[2] / "supabase/migrations/042_worry_about.sql"


class _RolledBack(Exception):
    pass


@pytest.mark.parametrize(("safety", "record", "kept"), [
    ("danger", {"danger_about": "body", "danger_reached": True}, "body"),
    ("unsure", {"danger_about": "themselves", "asked_about": "from_someone"}, "from_someone"),
    ("clear", {"danger_about": "themselves", "danger_reached": True}, None),
    ("danger", {"danger_reached": True}, None),
])
async def test_the_kind_of_an_open_worry_is_kept_and_a_settled_worrys_is_dropped(alice, safety, record, kept):
    from mani.db import pool

    thread = await start(alice)
    async with pool.as_admin() as conn:
        await conn.execute("update public.threads set understanding = $2::jsonb, safety = $3, "
                           "rewind_snapshot = '{}'::jsonb where id = $1", thread.id, record, safety)
    seen = {}
    with pytest.raises(_RolledBack):
        async with pool.as_admin() as conn, conn.transaction():
            await conn.execute(MIGRATION.read_text())
            seen["record"], seen["snapshot"] = await conn.fetchrow(
                "select understanding, rewind_snapshot from public.threads where id = $1", thread.id)
            raise _RolledBack
    assert seen["record"].get("worry_about") == kept
    assert "danger_about" not in seen["record"] and "asked_about" not in seen["record"]
    assert seen["record"].get("danger_reached") == record.get("danger_reached") and seen["snapshot"] is None
