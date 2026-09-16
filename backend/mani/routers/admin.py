# ABOUTME: Portal endpoints - prompt content and versions, the exercise catalog, crises.
# ABOUTME: Every route here requires an admin claim on the token and a service-role connection.

import datetime as dt
import uuid

from fastapi import APIRouter
from pydantic import BaseModel

from mani.auth.deps import AdminUser
from mani.db import config_tables, exercises as exercises_db
from mani.db.deps import AdminConn
from mani.db.exercises import AdminExercise, ExerciseInput
from mani.errors import ErrorCategory, ServiceError
from mani.models.api import PromptIn, PromptOut, PromptVersionOut
from mani.prompts import cache
from mani.routers.serializers import to_prompt, to_prompt_version

router = APIRouter(prefix="/v1/admin", tags=["admin"])


class PromptCreateIn(BaseModel):
    name: str
    content: str
    description: str = ""
    model_id: str | None = None
    model_parameters: dict | None = None
    routing: dict | None = None


class CrisisEventOut(BaseModel):
    id: uuid.UUID
    thread_id: uuid.UUID
    user_id: uuid.UUID
    reason: str
    detected_at: dt.datetime
    resolution: str | None = None
    resolved_at: dt.datetime | None = None


@router.post("/prompts/cache/invalidate", status_code=204)
def invalidate_cache(_: AdminUser) -> None:
    """Make an edit take effect now instead of when the TTL expires."""
    cache.invalidate()


@router.get("/prompts", response_model=list[PromptOut])
async def list_prompts(conn: AdminConn) -> list[PromptOut]:
    return [to_prompt(p) for p in await config_tables.list_all_prompts(conn)]


@router.post("/prompts", response_model=PromptOut, status_code=201)
async def create_prompt(
    user: AdminUser, conn: AdminConn, body: PromptCreateIn
) -> PromptOut:
    prompt = await config_tables.create_prompt(
        conn,
        name=body.name,
        content=body.content,
        description=body.description,
        model_id=body.model_id,
        model_parameters=body.model_parameters,
        routing=body.routing,
        created_by=user.user_id,
    )
    cache.invalidate()
    return to_prompt(prompt)


@router.get("/prompts/{prompt_id}", response_model=PromptOut)
async def get_prompt(conn: AdminConn, prompt_id: uuid.UUID) -> PromptOut:
    prompt = await config_tables.get_prompt_by_id(conn, prompt_id)
    if prompt is None:
        raise ServiceError(
            f"prompt {prompt_id} not found",
            ErrorCategory.NOT_FOUND,
            user_message="That prompt does not exist.",
        )
    return to_prompt(prompt)


@router.patch("/prompts/{prompt_id}", response_model=PromptOut)
async def update_prompt(
    user: AdminUser, conn: AdminConn, prompt_id: uuid.UUID, body: PromptIn
) -> PromptOut:
    """Snapshot then publish, in one transaction.

    If the snapshot cannot be written the edit does not happen. The previous version
    logged a failed snapshot and published regardless, losing the history it existed for.
    """
    changes = body.model_dump(exclude_none=True, exclude={"change_summary"})
    prompt = await config_tables.update_prompt(
        conn,
        prompt_id,
        changes,
        change_summary=body.change_summary,
        updated_by=user.user_id,
    )
    if prompt is None:
        raise ServiceError(
            f"prompt {prompt_id} not found",
            ErrorCategory.NOT_FOUND,
            user_message="That prompt does not exist.",
        )
    cache.invalidate()
    return to_prompt(prompt)


@router.get("/prompts/{prompt_id}/versions", response_model=list[PromptVersionOut])
async def list_versions(conn: AdminConn, prompt_id: uuid.UUID) -> list[PromptVersionOut]:
    return [to_prompt_version(r) for r in await config_tables.list_prompt_versions(conn, prompt_id)]


@router.get("/exercises", response_model=list[AdminExercise])
async def list_all_exercises(conn: AdminConn) -> list[AdminExercise]:
    return await exercises_db.list_all(conn)


@router.post("/exercises", response_model=AdminExercise, status_code=201)
async def create_exercise(conn: AdminConn, body: ExerciseInput) -> AdminExercise:
    if not body.title or not body.category or not body.audio_path:
        raise ServiceError(
            "an exercise needs a title, a category and an audio path",
            ErrorCategory.CONFIG_ERROR,
            user_message="Title, category and audio path are required.",
        )
    return await exercises_db.create(conn, body)


@router.patch("/exercises/{exercise_id}", response_model=AdminExercise)
async def update_exercise(
    conn: AdminConn, exercise_id: uuid.UUID, body: ExerciseInput
) -> AdminExercise:
    exercise = await exercises_db.update(conn, exercise_id, body)
    if exercise is None:
        raise ServiceError(
            f"exercise {exercise_id} not found",
            ErrorCategory.NOT_FOUND,
            user_message="That exercise does not exist.",
        )
    return exercise


@router.delete("/exercises/{exercise_id}", status_code=204)
async def delete_exercise(conn: AdminConn, exercise_id: uuid.UUID) -> None:
    if not await exercises_db.delete(conn, exercise_id):
        raise ServiceError(
            f"exercise {exercise_id} not found",
            ErrorCategory.NOT_FOUND,
            user_message="That exercise does not exist.",
        )


@router.get("/crisis-events", response_model=list[CrisisEventOut])
async def list_crisis_events(conn: AdminConn, unresolved: bool = True) -> list[CrisisEventOut]:
    """Flagged conversations, newest first.

    The table this reads replaced a boolean on the thread that overwrote itself, so a
    second crisis erased the first and there was nothing to review.
    """
    rows = await conn.fetch(
        """
        select id, thread_id, user_id, reason, detected_at, resolution, resolved_at
          from admin.crisis_events
         where (not $1 or resolved_at is null)
         order by detected_at desc
         limit 200
        """,
        unresolved,
    )
    return [CrisisEventOut(**dict(r)) for r in rows]
