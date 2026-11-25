# ABOUTME: The exercise catalog, its topics, and a user's completions.
# ABOUTME: The catalog and topics are shared config; completions are the user's own rows under RLS.

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

import asyncpg
from pydantic import BaseModel, ConfigDict

from mani.models.rows import Exercise, Row

_EXERCISE_COLUMNS = (
    "id", "title", "subtitle", "description", "type", "category", "audio_path",
    "duration_minutes", "display_order", "show_on_home_screen", "framework_id",
)
COLUMNS = ", ".join(_EXERCISE_COLUMNS)
ADMIN_COLUMNS = COLUMNS + ", is_active, created_at, updated_at"


class Completion(Row):
    id: uuid.UUID
    exercise_id: uuid.UUID
    helpful: bool | None = None
    completed_at: dt.datetime


class ListedExercise(Exercise):
    """An exercise in a topic's listing: `subcategory` is set when the topic lists it from another topic."""

    subcategory: str | None = None


class LibraryTopic(Row):
    """A library topic: its id is the category its exercises carry."""

    id: str
    title: str
    blurb: str = ""
    display_order: int = 0


class AdminExercise(Exercise):
    is_active: bool = True
    created_at: dt.datetime
    updated_at: dt.datetime


class ExerciseInput(BaseModel):
    """The editable fields. Only what is supplied is written."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    subtitle: str | None = None
    description: str | None = None
    type: str | None = None
    category: str | None = None
    audio_path: str | None = None
    duration_minutes: float | None = None
    display_order: int | None = None
    show_on_home_screen: bool | None = None
    is_active: bool | None = None
    # Which framework this exercise follows when it finishes. Null is the ordinary
    # library exercise, which is most of them.
    framework_id: str | None = None


async def list_active(
    conn: asyncpg.Connection,
    category: str | None = None,
    *,
    home_screen: bool | None = None,
) -> list[ListedExercise]:
    """The catalog a signed-in user may browse, ordered as the portal arranged it.

    `category` narrows it to one topic: the exercises it owns, then those it lists from other topics, each under
    its subcategory. `home_screen` None is the whole catalog; True or False narrows it to one side.
    """
    columns = ", ".join(f"e.{name}" for name in _EXERCISE_COLUMNS)
    rows = await conn.fetch(
        f"""
        select {columns}, l.subcategory
          from admin.exercises e
          left join admin.exercise_topic_links l on l.exercise_id = e.id and l.topic_id = $2
         where e.is_active
           and ($1::boolean is null or e.show_on_home_screen = $1)
           and ($2::text is null or e.category = $2 or l.topic_id is not null)
         order by l.display_order nulls first, e.category, e.display_order, e.title
        """,
        home_screen, category,
    )
    return ListedExercise.from_records(rows)


async def list_topics(conn: asyncpg.Connection) -> list[LibraryTopic]:
    rows = await conn.fetch(
        "select id, title, blurb, display_order from admin.library_topics order by display_order, title"
    )
    return LibraryTopic.from_records(rows)


async def get(conn: asyncpg.Connection, exercise_id: uuid.UUID | str) -> Exercise | None:
    row = await conn.fetchrow(
        f"select {COLUMNS} from admin.exercises where id = $1 and is_active", exercise_id
    )
    return Exercise.from_record(row)


async def list_completions(
    conn: asyncpg.Connection, user_id: uuid.UUID | str
) -> list[Completion]:
    rows = await conn.fetch(
        "select id, exercise_id, helpful, completed_at from public.exercise_completions "
        "where user_id = $1 order by completed_at desc",
        user_id,
    )
    return Completion.from_records(rows)


async def record_completion(
    conn: asyncpg.Connection,
    user_id: uuid.UUID | str,
    exercise_id: uuid.UUID | str,
    helpful: bool | None = None,
) -> Completion:
    row = await conn.fetchrow(
        "insert into public.exercise_completions (user_id, exercise_id, helpful) "
        "values ($1, $2, $3) returning id, exercise_id, helpful, completed_at",
        user_id, exercise_id, helpful,
    )
    return Completion.model_validate(dict(row))


# ---------------------------------------------------------------------------
# Portal operations - inactive rows included
# ---------------------------------------------------------------------------


async def list_all(conn: asyncpg.Connection) -> list[AdminExercise]:
    rows = await conn.fetch(
        f"select {ADMIN_COLUMNS} from admin.exercises order by category, display_order"
    )
    return AdminExercise.from_records(rows)


async def create(conn: asyncpg.Connection, values: ExerciseInput) -> AdminExercise:
    row = await conn.fetchrow(
        f"""
        insert into admin.exercises
            (title, subtitle, description, type, category, audio_path,
             duration_minutes, display_order, show_on_home_screen, is_active, framework_id)
        values ($1, $2, coalesce($3, ''), $4, $5, $6,
                $7, coalesce($8, 0), coalesce($9, false), coalesce($10, true), $11)
        returning {ADMIN_COLUMNS}
        """,
        values.title, values.subtitle, values.description, values.type,
        values.category, values.audio_path, values.duration_minutes,
        values.display_order, values.show_on_home_screen, values.is_active,
        values.framework_id,
    )
    return AdminExercise.model_validate(dict(row))


async def update(
    conn: asyncpg.Connection, exercise_id: uuid.UUID | str, values: ExerciseInput
) -> AdminExercise | None:
    """Write only the fields that were supplied.

    Built from a fixed column list rather than from caller-supplied keys, so nothing a
    request body says can name a column that was not meant to be editable.
    """
    supplied: dict[str, Any] = values.model_dump(exclude_none=True)
    if not supplied:
        row = await conn.fetchrow(
            f"select {ADMIN_COLUMNS} from admin.exercises where id = $1", exercise_id
        )
        return AdminExercise.from_record(row)

    columns = list(supplied)
    assignments = ", ".join(f"{name} = ${i + 2}" for i, name in enumerate(columns))
    row = await conn.fetchrow(
        f"update admin.exercises set {assignments} where id = $1 returning {ADMIN_COLUMNS}",
        exercise_id, *(supplied[name] for name in columns),
    )
    return AdminExercise.from_record(row)


async def delete(conn: asyncpg.Connection, exercise_id: uuid.UUID | str) -> bool:
    result = await conn.execute("delete from admin.exercises where id = $1", exercise_id)
    return result.endswith(" 1")
