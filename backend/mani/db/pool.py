# ABOUTME: The asyncpg pool and the two ways to take a connection from it.
# ABOUTME: as_user() applies RLS from the caller's claims; as_admin() bypasses it.

import asyncio
import json
import logging
import weakref
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

# The pool runs behind Supabase's transaction pooler (port 6543), which hands each transaction
# whichever backend is free. So every statement runs inside a transaction, state is only ever
# `set local` or transaction-scoped, and no statement is prepared under a name that a later
# transaction would expect to find. Sizes are settings (db_pool_min_size, db_pool_max_size).
# Each statement may take this long; no transaction spans a model call any more.
COMMAND_TIMEOUT_SECONDS = 10.0


async def _configure(conn: asyncpg.Connection) -> None:
    """Run on every new connection in the pool.

    asyncpg hands jsonb back as raw text unless told otherwise. Decoding it here means
    every query module gets dicts, rather than each one remembering to json.loads its
    own columns - which is the kind of thing that works until the one place that forgot.
    The codecs live in this client; the type lookup they need runs in a transaction, so the
    transaction pooler keeps it on one backend.
    """
    async with conn.transaction():
        await conn.set_type_codec(
            "jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
        )
        await conn.set_type_codec(
            "json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
        )


async def _reset(conn: asyncpg.Connection) -> None:
    """Run when a connection goes back to the pool, in place of asyncpg's session reset.

    asyncpg's own reset unlocks session advisory locks, unlistens and resets every setting. Behind the
    transaction pooler those statements reach whichever backend is free, not one this client set anything
    on, and nothing here sets session state. A transaction left open by a cancelled request is still
    rolled back."""
    if conn.is_in_transaction():
        await conn.execute("rollback")


async def open_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=settings.db_pool_min_size,
            max_size=settings.db_pool_max_size,
            command_timeout=COMMAND_TIMEOUT_SECONDS,
            # Named server-side statements do not survive the transaction pooler.
            statement_cache_size=0,
            init=_configure,
            reset=_reset,
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


# The tasks holding a connection right now. A task that holds one and waits for a second, or for a model,
# holds the first for as long as that wait: enough of them empty the pool and every request stalls behind
# them (the turn before 2026-11-05, then the prompt cache, summaries and memory folds). So it is refused.
# Tracked per task rather than in a context variable, which a background task started meanwhile would copy.
_holding: weakref.WeakSet[asyncio.Task] = weakref.WeakSet()


def holding() -> bool:
    """Whether the running task holds a connection from this pool."""
    task = asyncio.current_task()
    return task is not None and task in _holding


def refuse_while_holding(what: str) -> None:
    """Raise when the running task holds a connection: `what` must happen before it is taken or after."""
    if holding():
        raise RuntimeError(f"{what} while this task holds a database connection")


@asynccontextmanager
async def _acquire() -> AsyncIterator[asyncpg.Connection]:
    """A connection from the pool, or a quick retryable refusal when none frees up in time."""
    refuse_while_holding("a second connection was asked for")
    pool = get_pool()
    try:
        conn = await pool.acquire(timeout=get_settings().db_acquire_timeout_seconds)
    except TimeoutError as exc:
        raise ServiceError(
            "no database connection free within the acquire timeout",
            ErrorCategory.BUSY,
            retryable=True,
            user_message="Mani is busy right now. Please try again in a moment.",
        ) from exc
    task = asyncio.current_task()
    _holding.add(task)
    try:
        yield conn
    finally:
        _holding.discard(task)
        await pool.release(conn)


@asynccontextmanager
async def as_user(claims: Claims) -> AsyncIterator[asyncpg.Connection]:
    """A connection acting as the caller, inside a transaction, with RLS applying.

    This is the default for anything serving a request. Every statement run on it is
    subject to the policies on the table, so a query that forgets its own ownership
    filter still cannot read another person's rows - which is the failure the previous
    implementation shipped.

    The whole block is one transaction: either the turn's writes all land or none do.
    """
    async with _acquire() as conn:
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
    async with _acquire() as conn:
        async with conn.transaction():
            yield conn


async def ping() -> bool:
    """Whether the database answers. Used by the readiness probe."""
    try:
        async with as_admin() as conn:
            return await conn.fetchval("select 1") == 1
    except (ServiceError, asyncpg.PostgresError, OSError):
        return False
