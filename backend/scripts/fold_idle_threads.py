# ABOUTME: Folds conversations that have gone quiet into each person's memory.
# ABOUTME: Run on a schedule by the host (hourly is plenty); safe to run twice at once.

from __future__ import annotations

import argparse
import asyncio
import logging
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from mani import memory  # noqa: E402
from mani.db import pool  # noqa: E402


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=200, help="most people to fold per run")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    await pool.open_pool()
    try:
        folded = await memory.fold_idle(limit=args.limit)
    finally:
        await pool.close_pool()

    print(f"threads folded: {folded}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
