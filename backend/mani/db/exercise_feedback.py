# ABOUTME: Reads and writes the person's 👍/👎 on library exercises (public.exercise_feedback), one per exercise.
# ABOUTME: Only an active exercise can be rated; admins read every person's ratings, filtered by email.

from __future__ import annotations

import datetime as dt
import uuid

import asyncpg
from pydantic import BaseModel

from mani.models.api import FeedbackOut, FeedbackRating

DEFAULT_PAGE = 100
MAX_PAGE = 500


class AdminExerciseFeedback(BaseModel):
    """One person's rating of one exercise, as an admin reviews it."""

    user_id: uuid.UUID
    user_email: str | None = None
    exercise_id: uuid.UUID
    exercise_title: str
    exercise_type: str | None = None
    category: str
    rating: FeedbackRating
    reason: str | None = None
    updated_at: dt.datetime


async def rate(
    conn: asyncpg.Connection,
    user_id: uuid.UUID | str,
    exercise_id: uuid.UUID,
    rating: FeedbackRating,
    reason: str | None,
) -> FeedbackOut | None:
    """Sets or replaces the rating. None when the exercise does not exist or is not active."""
    row = await conn.fetchrow(
        """
        insert into public.exercise_feedback (user_id, exercise_id, rating, reason)
        select $1, e.id, $3, $4
          from admin.exercises e
         where e.id = $2 and e.is_active
        on conflict (user_id, exercise_id) do update
           set rating = excluded.rating, reason = excluded.reason, updated_at = now()
        returning rating, reason, updated_at
        """,
        user_id, exercise_id, rating, reason,
    )
    return FeedbackOut.model_validate(dict(row)) if row else None


async def clear(conn: asyncpg.Connection, user_id: uuid.UUID | str, exercise_id: uuid.UUID) -> None:
    """Removes the rating, if there is one. Clearing an unrated exercise is not an error: it stays unrated."""
    await conn.execute(
        "delete from public.exercise_feedback where user_id = $1 and exercise_id = $2", user_id, exercise_id
    )


async def for_user(conn: asyncpg.Connection, user_id: uuid.UUID | str) -> dict[uuid.UUID, FeedbackOut]:
    """The person's ratings by exercise id."""
    rows = await conn.fetch(
        "select exercise_id, rating, reason, updated_at from public.exercise_feedback where user_id = $1", user_id
    )
    return {row["exercise_id"]: FeedbackOut.model_validate(dict(row)) for row in rows}


async def list_all(
    conn: asyncpg.Connection, search: str | None = None, limit: int = DEFAULT_PAGE
) -> list[AdminExerciseFeedback]:
    """Every person's ratings, the most recently changed first. `search` matches part of the person's email, or
    their user id exactly. Admin connection only."""
    term = (search or "").strip() or None
    rows = await conn.fetch(
        """
        select f.user_id, u.email as user_email, f.exercise_id, e.title as exercise_title,
               e.type as exercise_type, e.category, f.rating, f.reason, f.updated_at
          from public.exercise_feedback f
          join auth.users u on u.id = f.user_id
          join admin.exercises e on e.id = f.exercise_id
         where $1::text is null or u.email ilike '%' || $1 || '%' or f.user_id::text = lower($1)
         order by f.updated_at desc
         limit $2
        """,
        term, limit,
    )
    return [AdminExerciseFeedback.model_validate(dict(r)) for r in rows]
