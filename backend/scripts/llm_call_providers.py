# ABOUTME: Shows which provider endpoint served each recent model call, and how long it took there.
# ABOUTME: Read only: it resolves the generation ids in admin.llm_calls through OpenRouter's /generation.

from __future__ import annotations

import argparse
import asyncio
import pathlib
import sys

import httpx

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from mani.config import get_settings  # noqa: E402
from mani.db import pool  # noqa: E402


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=30, help="most recent calls to show")
    parser.add_argument("--purpose", default="chat", help="chat, summarize, exercise_select or memory_fold")
    parser.add_argument("--slower-than", type=int, default=0, help="only calls over this many ms")
    args = parser.parse_args()
    settings = get_settings()

    await pool.open_pool()
    try:
        async with pool.as_admin() as conn:
            rows = await conn.fetch(
                """
                select created_at, outcome, latency_ms, output_tokens, generation_id
                from admin.llm_calls
                where purpose = $1 and latency_ms > $2
                order by created_at desc
                limit $3
                """,
                args.purpose, args.slower_than, args.limit,
            )
    finally:
        await pool.close_pool()

    headers = {"Authorization": f"Bearer {settings.openrouter_api_key}"}
    async with httpx.AsyncClient(base_url=settings.openrouter_base_url, headers=headers, timeout=15) as http:
        print(f"{'when (UTC)':19}  {'outcome':14}  {'ours ms':>7}  {'out':>4}  {'provider':12}  {'theirs ms':>9}  {'gen ms':>7}")
        for row in rows:
            provider, latency, generation = "-", "-", "-"
            # A timeout was cut off before a reply, so it has no id; match it by time on the
            # Activity page instead.
            if row["generation_id"]:
                response = await http.get("/generation", params={"id": row["generation_id"]})
                if response.is_success:
                    data = response.json().get("data") or {}
                    provider = data.get("provider_name") or "-"
                    latency = data.get("latency") or "-"
                    generation = data.get("generation_time") or "-"
                else:
                    provider = f"http {response.status_code}"
            when = row["created_at"].strftime("%Y-%m-%d %H:%M:%S")
            print(
                f"{when:19}  {row['outcome']:14}  {row['latency_ms']:>7}  {row['output_tokens']:>4}  "
                f"{provider:12}  {latency!s:>9}  {generation!s:>7}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
