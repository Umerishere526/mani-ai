# ABOUTME: Makes an existing account an admin, who can read every person's conversations and chat in none.
# ABOUTME: Usage: python scripts/grant_admin.py someone@example.com [--revoke]

from __future__ import annotations

import argparse
import asyncio
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from mani import auth_admin  # noqa: E402
from mani.db import pool  # noqa: E402


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("email", help="the account's email; it must already exist")
    parser.add_argument("--revoke", action="store_true", help="remove admin instead of granting it")
    args = parser.parse_args()

    await pool.open_pool()
    try:
        async with pool.as_admin() as conn:
            user_id = await conn.fetchval(
                "select id from auth.users where lower(email) = lower($1)", args.email.strip()
            )
    finally:
        await pool.close_pool()
    if user_id is None:
        print(f"No account with the email {args.email}. Sign up first, then run this again.")
        return 1

    try:
        await auth_admin.set_admin(str(user_id), granted=not args.revoke)
    finally:
        await auth_admin.close()
    state = "is no longer an admin" if args.revoke else "is now an admin"
    print(f"{args.email} {state}. It takes effect the next time they sign in.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
