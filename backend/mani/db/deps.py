# ABOUTME: FastAPI dependencies that hand a route a database connection.
# ABOUTME: UserConn applies RLS from the caller's claims; AdminConn is the exception.

from collections.abc import AsyncIterator
from typing import Annotated

import asyncpg
from fastapi import Depends

from mani.auth.deps import AdminUser, CurrentUser
from mani.db import pool


async def user_conn(user: CurrentUser) -> AsyncIterator[asyncpg.Connection]:
    """The default. One transaction per request, acting as the caller."""
    async with pool.as_user(user) as conn:
        yield conn


async def admin_conn(_: AdminUser) -> AsyncIterator[asyncpg.Connection]:
    """Cross-user work only, and only for a caller whose token says admin.

    Named so its use is obvious in review - reaching for it where user_conn would do is
    how RLS stops applying to real traffic.
    """
    async with pool.as_admin() as conn:
        yield conn


UserConn = Annotated[asyncpg.Connection, Depends(user_conn)]
AdminConn = Annotated[asyncpg.Connection, Depends(admin_conn)]
