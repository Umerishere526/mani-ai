# ABOUTME: The asyncpg pool and the two ways to take a connection from it.
# ABOUTME: as_user() applies RLS from the caller's claims; as_admin() bypasses it.

import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg

from mani.auth.jwt import Claims
from mani.config import get_settings
from mani.errors import ErrorCategory, ServiceError

logger = logging.getLogger(__name__)

# Postgres is reached directly rather than through PostgREST, because a chat turn makes
# many writes that have to succeed or fail together and PostgREST cannot hold a
# transaction across statements.
_pool: asyncpg.Pool | None = None

MIN_POOL_SIZE = 2
MAX_POOL_SIZE = 10
# A turn holds its connection across a model call, so this has to exceed that.
COMMAND_TIMEOUT_SECONDS = 90.0


async def _configure(conn: asyncpg.Connection) -> None:
    """Run on every new connection in the pool.

    asyncpg hands jsonb back as raw text unless told otherwise. Decoding it here means
    every query module gets dicts, rather than each one remembering to json.loads its
    own columns - which is the kind of thing that works until the one place that forgot.
    """
    await conn.set_type_codec(
        "jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )
    await conn.set_type_codec(
        "json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )


async def open_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=MIN_POOL_SIZE,
            max_size=MAX_POOL_SIZE,
            command_timeout=COMMAND_TIMEOUT_SECONDS,
            init=_configure,
        )
        logger.info("database pool opened")
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("database pool closed")


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise ServiceError(
            "database pool is not open",
            ErrorCategory.CONFIG_ERROR,
            user_message="Mani is starting up. Please try again in a moment.",
        )
    return _pool


@asynccontextmanager
async def as_user(claims: Claims) -> AsyncIterator[asyncpg.Connection]:
    """A connection acting as the caller, inside a transaction, with RLS applying.

    This is the default for anything serving a request. Every statement run on it is
    subject to the policies on the table, so a query that forgets its own ownership
    filter still cannot read another person's rows - which is the failure the previous
    implementation shipped.

    The whole block is one transaction: either the turn's writes all land or none do.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            # `set local` reverts when the transaction ends, so a pooled connection
            # cannot leak one caller's identity into the next request.
            # mani_service, not authenticated: it holds the privileges only the backend
            # should have - writing Mani's half of a turn, recording a crisis - which a
            # user must not hold through PostgREST with their own JWT. RLS applies to it
            # the same way, so this is a wider privilege set, not a wider view of rows.
            await conn.execute("set local role mani_service")
            # set_config rather than SET LOCAL, which takes no parameters. auth.uid()
            # reads `sub` out of this, so it must be the verified claims, never input.
            await conn.execute(
                "select set_config('request.jwt.claims', $1, true)",
                claims.as_pg_setting(),
            )
            yield conn


@asynccontextmanager
async def as_admin() -> AsyncIterator[asyncpg.Connection]:
    """A connection with no user scoping, for work that is genuinely cross-user.

    Named distinctly so its use is visible in review. Reaching for this where as_user()
    would do is how RLS stops applying to real traffic. Legitimate uses: reading the
    prompt and framework registry, writing the call log, admin endpoints.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            yield conn


async def ping() -> bool:
    """Whether the database answers. Used by the readiness probe."""
    try:
        pool = get_pool()
        async with pool.acquire() as conn:
            return await conn.fetchval("select 1") == 1
    except (ServiceError, asyncpg.PostgresError, OSError):
        return False
