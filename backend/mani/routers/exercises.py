# ABOUTME: The exercise catalog, a user's completions, and their 👍/👎 on each exercise.
# ABOUTME: Audio paths never leave the backend; clients get a short-lived signed link.

import asyncio
import uuid

import asyncpg
from fastapi import APIRouter

from mani.auth.deps import CurrentUser
from mani.db import exercise_feedback as feedback_db
from mani.db import exercises as exercises_db
from mani.db.deps import UserConn
from mani.errors import ErrorCategory, ServiceError
from mani.models.api import (
    CompletionIn,
    CompletionOut,
    ExerciseOut,
    FeedbackIn,
    FeedbackOut,
)
from mani.routers.serializers import to_completion, to_exercise
from mani.storage import signed_audio_url

router = APIRouter(prefix="/v1/exercises", tags=["exercises"])


async def _with_urls(conn: asyncpg.Connection, user_id: str, rows: list) -> list[ExerciseOut]:
    """Each exercise with its signed link and the caller's own rating of it."""
    urls = await asyncio.gather(*(signed_audio_url(e.audio_path) for e in rows))
    rated = await feedback_db.for_user(conn, user_id)
    return [to_exercise(e, url, rated.get(e.id)) for e, url in zip(rows, urls, strict=True)]


@router.get("", response_model=list[ExerciseOut])
async def list_exercises(
    user: CurrentUser, conn: UserConn, category: str | None = None
) -> list[ExerciseOut]:
    return await _with_urls(conn, user.user_id, await exercises_db.list_active(conn, category))


@router.get("/home", response_model=list[ExerciseOut])
async def home_screen(user: CurrentUser, conn: UserConn) -> list[ExerciseOut]:
    return await _with_urls(conn, user.user_id, await exercises_db.list_active(conn, home_screen=True))


@router.get("/completions", response_model=list[CompletionOut])
async def list_completions(user: CurrentUser, conn: UserConn) -> list[CompletionOut]:
    return [to_completion(c) for c in await exercises_db.list_completions(conn, user.user_id)]


@router.post("/completions", response_model=CompletionOut, status_code=201)
async def complete(
    user: CurrentUser, conn: UserConn, body: CompletionIn
) -> CompletionOut:
    completion = await exercises_db.record_completion(
        conn, user.user_id, body.exercise_id, body.helpful
    )
    return to_completion(completion)


@router.get("/{exercise_id}", response_model=ExerciseOut)
async def get_exercise(
    user: CurrentUser, conn: UserConn, exercise_id: uuid.UUID
) -> ExerciseOut:
    exercise = await exercises_db.get(conn, exercise_id)
    if exercise is None:
        raise ServiceError(
            f"exercise {exercise_id} not found or inactive",
            ErrorCategory.NOT_FOUND,
            user_message="That exercise is not available.",
        )
    rated = await feedback_db.for_user(conn, user.user_id)
    return to_exercise(exercise, await signed_audio_url(exercise.audio_path), rated.get(exercise.id))


@router.put("/{exercise_id}/feedback", response_model=FeedbackOut)
async def rate(
    user: CurrentUser, conn: UserConn, exercise_id: uuid.UUID, body: FeedbackIn
) -> FeedbackOut:
    """The person's 👍 or 👎 on an exercise, replacing any earlier one, with an optional reason."""
    stored = await feedback_db.rate(conn, user.user_id, exercise_id, body.rating, body.reason)
    if stored is None:
        raise ServiceError(
            f"exercise {exercise_id} not found or inactive",
            ErrorCategory.NOT_FOUND,
            user_message="That exercise is not available.",
        )
    return stored


@router.delete("/{exercise_id}/feedback", status_code=204)
async def clear_rating(user: CurrentUser, conn: UserConn, exercise_id: uuid.UUID) -> None:
    await feedback_db.clear(conn, user.user_id, exercise_id)
