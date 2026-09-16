# ABOUTME: Liveness and readiness endpoints for the container platform.
# ABOUTME: Neither calls a model provider; readiness checks the database only.

from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from mani.db import pool

router = APIRouter(tags=["health"])


class Health(BaseModel):
    status: str


class Readiness(BaseModel):
    status: str
    database: bool


@router.get("/health")
def health() -> Health:
    """Is the process alive. Answers from process state only."""
    return Health(status="ok")


@router.get("/health/ready")
async def ready(response: Response) -> Readiness:
    """Is the process able to serve. A container platform should route on this."""
    database = await pool.ping()
    if not database:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return Readiness(status="ok" if database else "degraded", database=database)
