# ABOUTME: Reads the configuration tables - prompts and the framework registry.
# ABOUTME: Both live in the admin schema, so these run on an admin connection.

import uuid
from typing import Any

import asyncpg

from mani.models.rows import Framework, Prompt

# A closed set, so nothing a request body names can reach a column that is not editable -
# `version`, `created_by` and the timestamps among them.
EDITABLE_PROMPT_COLUMNS = frozenset(
    {"name", "description", "content", "model_id", "model_parameters", "routing",
     "is_active"}
)

PROMPT_COLUMNS = (
    "id, name, description, content, version, model_id, "
    "model_parameters, routing, is_active"
)
FRAMEWORK_COLUMNS = (
    "id, name, summary, body, activation_conditions, phases, display_order"
)


async def list_active_prompts(conn: asyncpg.Connection) -> list[Prompt]:
    """Every live prompt, for the composer's cache.

    Filtered in SQL rather than in Python. The reference fetched every row including
    inactive ones - full content each time - and filtered afterwards.
    """
    rows = await conn.fetch(
        f"select {PROMPT_COLUMNS} from admin.prompts where is_active order by name"
    )
    return Prompt.from_records(rows)


async def get_prompt(conn: asyncpg.Connection, name: str) -> Prompt | None:
    row = await conn.fetchrow(
        f"select {PROMPT_COLUMNS} from admin.prompts where name = $1 and is_active", name
    )
    return Prompt.from_record(row)


async def list_all_prompts(conn: asyncpg.Connection) -> list[Prompt]:
    """Every prompt, active or not, for the portal."""
    rows = await conn.fetch(f"select {PROMPT_COLUMNS} from admin.prompts order by name")
    return Prompt.from_records(rows)


async def get_prompt_by_id(
    conn: asyncpg.Connection, prompt_id: uuid.UUID | str
) -> Prompt | None:
    row = await conn.fetchrow(
        f"select {PROMPT_COLUMNS} from admin.prompts where id = $1", prompt_id
    )
    return Prompt.from_record(row)


async def create_prompt(
    conn: asyncpg.Connection,
    *,
    name: str,
    content: str,
    description: str = "",
    model_id: str | None = None,
    model_parameters: dict[str, Any] | None = None,
    routing: dict[str, Any] | None = None,
    created_by: uuid.UUID | str | None = None,
) -> Prompt:
    row = await conn.fetchrow(
        f"""
        insert into admin.prompts
            (name, content, description, model_id, model_parameters, routing,
             created_by, updated_by)
        values ($1, $2, $3, $4, coalesce($5::jsonb, '{{}}'::jsonb),
                coalesce($6::jsonb, '{{}}'::jsonb), $7, $7)
        returning {PROMPT_COLUMNS}
        """,
        name, content, description, model_id, model_parameters, routing, created_by,
    )
    return Prompt.model_validate(dict(row))


async def update_prompt(
    conn: asyncpg.Connection,
    prompt_id: uuid.UUID | str,
    changes: dict[str, Any],
    *,
    change_summary: str | None = None,
    updated_by: uuid.UUID | str | None = None,
) -> Prompt | None:
    """Snapshot the current prompt, then write the new one.

    Both statements are in the caller's transaction, which is the whole point: the
    previous implementation logged a failed snapshot and published anyway, so the history
    it was meant to preserve had holes in it exactly where an incident would look.
    """
    current = await get_prompt_by_id(conn, prompt_id)
    if current is None:
        return None

    await conn.execute(
        """
        insert into admin.prompt_versions
            (prompt_id, version, content, model_id, model_parameters, routing,
             change_summary, created_by)
        values ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7, $8)
        on conflict (prompt_id, version) do nothing
        """,
        current.id, current.version, current.content, current.model_id,
        current.model_parameters, current.routing, change_summary, updated_by,
    )

    columns = [name for name in changes if name in EDITABLE_PROMPT_COLUMNS]
    if not columns:
        return current

    assignments = ", ".join(f"{name} = ${i + 3}" for i, name in enumerate(columns))
    row = await conn.fetchrow(
        f"""
        update admin.prompts
           set {assignments}, version = version + 1, updated_by = $2
         where id = $1
        returning {PROMPT_COLUMNS}
        """,
        prompt_id, updated_by, *(changes[name] for name in columns),
    )
    return Prompt.from_record(row)


async def list_prompt_versions(
    conn: asyncpg.Connection, prompt_id: uuid.UUID | str
) -> list[asyncpg.Record]:
    return await conn.fetch(
        """
        select id, prompt_id, version, content, model_id, model_parameters, routing,
               change_summary, created_at
          from admin.prompt_versions
         where prompt_id = $1
         order by version desc
        """,
        prompt_id,
    )


async def list_active_frameworks(conn: asyncpg.Connection) -> list[Framework]:
    """The closed set of techniques a model-supplied id is checked against."""
    rows = await conn.fetch(
        f"select {FRAMEWORK_COLUMNS} from admin.frameworks "
        "where is_active order by display_order, id"
    )
    return Framework.from_records(rows)
