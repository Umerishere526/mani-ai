# ABOUTME: Builds the FastAPI application - Sentry, the pool, error handling, routers.
# ABOUTME: Run with `fastapi dev main.py` from the backend directory.

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from mani import auth_admin, storage, stt
from mani.config import get_settings
from mani.db import pool
from mani.errors import ErrorCategory, ServiceError
from mani.routers import (
    account,
    admin,
    cron,
    crisis,
    exercises,
    health,
    messages,
    profile,
    threads,
    transcribe,
)

logger = logging.getLogger(__name__)


def error_body(category: ErrorCategory, message: str, retryable: bool) -> dict:
    """The single error shape every client branches on."""
    return {"error": {"category": category, "message": message, "retryable": retryable}}


def operation_id(route: APIRoute) -> str:
    """Name the generated TypeScript client function after the handler.

    FastAPI's default appends the path and method - `start_v1_threads_post` - which
    becomes the function name in the generated client. Route names are unique across
    the routers, and asserted so in the tests.
    """
    return route.name


def scrub_event(event: dict, _hint: dict) -> dict:
    """Remove from a Sentry event every field that can carry what somebody typed or what the
    model replied: the request body, frame locals, and breadcrumbs, which are log lines.

    The init options already stop the SDK collecting the first two; this removes them again
    should an integration attach them anyway.
    """
    (event.get("request") or {}).pop("data", None)
    for exception in (event.get("exception") or {}).get("values") or []:
        for frame in (exception.get("stacktrace") or {}).get("frames") or []:
            frame.pop("vars", None)
    event.pop("breadcrumbs", None)
    return event


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await pool.open_pool()
    try:
        yield
    finally:
        await storage.close()
        await stt.close()
        await auth_admin.close()
        await pool.close_pool()


def create_app() -> FastAPI:
    settings = get_settings()

    # Without this the root logger sits at WARNING and every logger.info in the service
    # is discarded - including the repair notes and the one-call-per-turn trail.
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            # Conversation content is special-category health data and must not leave
            # the process attached to an error report. What an event still carries is each
            # exception's type, message and stack, including any chained cause, and a
            # third-party exception's message can quote the input it failed on.
            send_default_pii=False,
            max_request_body_size="never",
            include_local_variables=False,
            before_send=scrub_event,
        )

    app = FastAPI(
        title="Mani",
        version="0.1.0",
        description="Chat orchestration, prompts, exercises and crisis handling.",
        lifespan=lifespan,
        generate_unique_id_function=operation_id,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.exception_handler(ServiceError)
    async def service_error_handler(_: Request, exc: ServiceError) -> JSONResponse:
        # The internal message goes to the log; only user_message reaches the client.
        if exc.status_code >= 500:
            logger.error("%s: %s", exc.category, exc, exc_info=exc)
        else:
            # An expired token or a missing thread is the client's problem, not an
            # incident. Logging a stack trace for each would bury real faults under
            # routine noise and spend the Sentry quota on it.
            logger.warning("%s: %s", exc.category, exc)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(exc.category, exc.user_message, exc.retryable),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Give a malformed request the same error shape as everything else.

        FastAPI's default returns `{"detail": [...]}`, so a client branching on
        `error.category` silently falls through to its unknown-error path.
        """
        # Only which field failed and how. The rest of a pydantic error carries the
        # rejected value, which for a too-long message is the whole thing the person
        # typed, and a log line is no place for that.
        logger.warning(
            "invalid request: %s",
            [(e.get("type"), e.get("loc")) for e in exc.errors()],
        )
        return JSONResponse(
            status_code=422,
            content=error_body(
                ErrorCategory.INVALID_REQUEST,
                "That request was not valid. Please try again.",
                False,
            ),
        )

    for router in (
        health.router,
        profile.router,
        account.router,
        threads.router,
        messages.router,
        transcribe.router,
        exercises.router,
        crisis.router,
        admin.router,
        cron.router,
    ):
        app.include_router(router)
    return app


app = create_app()
