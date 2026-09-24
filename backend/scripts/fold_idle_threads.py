# ABOUTME: Folds conversations that have gone quiet into each person's memory.
# ABOUTME: Run on a schedule by the host (hourly is plenty); safe to run twice at once.

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import logging
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from mani import memory  # noqa: E402
from mani.auth.jwt import Claims  # noqa: E402
from mani.db import memory as memory_db, pool  # noqa: E402


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=200, help="most people to fold per run")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    await pool.open_pool()
    idle_before = dt.datetime.now(dt.UTC) - memory.IDLE_AFTER
    try:
        # Finding who has a quiet thread is cross-user, so it is the one admin read. The
        # folds themselves run as each person, so RLS scopes every write exactly as it does
        # when their own New chat triggers one. Two runners at once is safe: a thread being
        # folded is claimed with `skip locked`, and the other runner passes over it.
        async with pool.as_admin() as conn:
            people = await memory_db.users_with_idle_threads(conn, idle_before, args.limit)
        folded = 0
        for user_id in people:
            claims = Claims(sub=str(user_id), raw={"sub": str(user_id), "role": "authenticated"})
            folded += await memory.fold_finished(claims, idle_before=idle_before)
    finally:
        await pool.close_pool()

    print(f"people: {len(people)}  threads folded: {folded}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
