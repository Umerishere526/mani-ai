# ABOUTME: What Mani carries into later conversations of what a person worked through, for them to read, correct, delete.
# ABOUTME: Only the progress layer; the patterns stay the fold's, and the whole memory goes with the account.

from fastapi import APIRouter

from mani.auth.deps import CurrentUser
from mani.db import memory as memory_db
from mani.db.deps import UserConn
from mani.llm.schema import ProgressMemory
from mani.models.api import ProgressMemoryIn, ProgressMemoryOut

# muhammad, 2026-11-06: progress memory is transparent and theirs: they can see it, correct it and delete it, and
# turning remember_progress off in their profile keeps none.
router = APIRouter(prefix="/v1/memory/progress", tags=["memory"])


def _out(progress: ProgressMemory) -> ProgressMemoryOut:
    return ProgressMemoryOut(**progress.model_dump())


@router.get("", response_model=ProgressMemoryOut)
async def get_progress(user: CurrentUser, conn: UserConn) -> ProgressMemoryOut:
    memory = await memory_db.get(conn, user.user_id)
    return _out(memory.progress if memory else ProgressMemory())


@router.put("", response_model=ProgressMemoryOut)
async def correct_progress(user: CurrentUser, conn: UserConn, body: ProgressMemoryIn) -> ProgressMemoryOut:
    """Replace what is carried forward with their own correction."""
    memory = await memory_db.save_progress(conn, user.user_id, ProgressMemory(**body.model_dump()))
    return _out(memory.progress)


@router.delete("", status_code=204)
async def delete_progress(user: CurrentUser, conn: UserConn) -> None:
    await memory_db.forget_progress(conn, user.user_id)
