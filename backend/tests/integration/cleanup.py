# ABOUTME: Helpers every integration fixture shares: reaching the database, claims, removing users.
# ABOUTME: Removal takes the cost rows a test's calls left behind, so nothing outlives its test.

import uuid

import asyncpg

from mani.auth.jwt import Claims
from mani.config import get_settings


async def reachable() -> bool:
    try:
        conn = await asyncpg.connect(get_settings().database_url, timeout=3)
    except (OSError, asyncpg.PostgresError):
        return False
    await conn.close()
    return True


def claims_for(user_id: uuid.UUID | str) -> Claims:
    return Claims(sub=str(user_id), raw={"sub": str(user_id), "role": "authenticated"})


async def remove_test_users(conn: asyncpg.Connection, *user_ids: uuid.UUID | str) -> None:
    """Delete test users, and first the `admin.llm_calls` rows recorded against them.

    Deleting a user sets `llm_calls.user_id` to null rather than removing the row - right for
    a real account, whose spend must still add up, and wrong for a test user: the rows a test
    fabricates would outlive it looking exactly like real calls, and every cost or cache
    figure read from the table would count them.
    """
    ids = [str(user_id) for user_id in user_ids]
    await conn.execute("delete from admin.llm_calls where user_id = any($1::uuid[])", ids)
    await conn.execute("delete from auth.users where id = any($1::uuid[])", ids)
