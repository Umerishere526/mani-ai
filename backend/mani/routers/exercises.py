# ABOUTME: The exercise catalog and a user's completions.
# ABOUTME: Audio paths never leave the backend; clients get a short-lived signed link.

import asyncio
import uuid

from fastapi import APIRouter

from mani.auth.deps import CurrentUser
from mani.db import exercises as exercises_db
from mani.db.deps import UserConn
from mani.errors import ErrorCategory, ServiceError
from mani.models.api import CompletionIn, CompletionOut, ExerciseOut
from mani.routers.serializers import to_completion, to_exercise
from mani.storage import signed_audio_url

router = APIRouter(prefix="/v1/exercises", tags=["exercises"])


async def _with_urls(rows: list) -> list[ExerciseOut]:
    urls = await asyncio.gather(*(signed_audio_url(e.audio_path) for e in rows))
    return [to_exercise(e, url) for e, url in zip(rows, urls, strict=True)]


@router.get("", response_model=list[ExerciseOut])
async def list_exercises(
    _: CurrentUser, conn: UserConn, category: str | None = None
) -> list[ExerciseOut]:
    return await _with_urls(await exercises_db.list_active(conn, category))


@router.get("/home", response_model=list[ExerciseOut])
async def home_screen(_: CurrentUser, conn: UserConn) -> list[ExerciseOut]:
    return await _with_urls(await exercises_db.list_active(conn, home_screen=True))


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
    _: CurrentUser, conn: UserConn, exercise_id: uuid.UUID
) -> ExerciseOut:
    exercise = await exercises_db.get(conn, exercise_id)
    if exercise is None:
        raise ServiceError(
            f"exercise {exercise_id} not found or inactive",
            ErrorCategory.NOT_FOUND,
            user_message="That exercise is not available.",
        )
    return to_exercise(exercise, await signed_audio_url(exercise.audio_path))
