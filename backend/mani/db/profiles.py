# ABOUTME: Reads and writes the onboarding profile - nickname, topics, support style.
# ABOUTME: Every function takes a connection; the caller owns the transaction.

import uuid

import asyncpg

from mani.models.rows import Profile

COLUMNS = "user_id, nickname, topics, support_style, age_bracket, remember_progress"


async def get(conn: asyncpg.Connection, user_id: uuid.UUID | str) -> Profile | None:
    row = await conn.fetchrow(
        f"select {COLUMNS} from public.profiles where user_id = $1", user_id
    )
    return Profile.from_record(row)


async def upsert(
    conn: asyncpg.Connection,
    user_id: uuid.UUID | str,
    *,
    nickname: str | None = None,
    topics: list[str] | None = None,
    support_style: str | None = None,
    age_bracket: str | None = None,
    remember_progress: bool | None = None,
) -> Profile:
    """Create or update a profile, leaving unspecified fields untouched.

    `coalesce` on the update side so a partial edit - changing only the nickname -
    does not silently blank the topics collected at onboarding.
    """
    row = await conn.fetchrow(
        f"""
        insert into public.profiles (user_id, nickname, topics, support_style, age_bracket, remember_progress)
        values ($1, $2, coalesce($3::text[], '{{}}'), $4, $5, coalesce($6, true))
        on conflict (user_id) do update set
            nickname          = coalesce(excluded.nickname, public.profiles.nickname),
            topics            = coalesce($3::text[], public.profiles.topics),
            support_style     = coalesce(excluded.support_style, public.profiles.support_style),
            age_bracket       = coalesce(excluded.age_bracket, public.profiles.age_bracket),
            remember_progress = coalesce($6, public.profiles.remember_progress)
        returning {COLUMNS}
        """,
        user_id, nickname, topics, support_style, age_bracket, remember_progress,
    )
    return Profile.model_validate(dict(row))
