# ABOUTME: Where a chat turn's time goes, from admin.llm_calls: latency against input, cached, output and thinking
# ABOUTME: tokens, by conversation style, with retries apart. Reads only; never calls the model.

"""Report how long Mani's chat calls take and what they spend their time on.

    .venv/bin/python scripts/latency_report.py                     # the last 24 hours
    .venv/bin/python scripts/latency_report.py --since 2026-11-03  # from a date (UTC)
    .venv/bin/python scripts/latency_report.py --thread <uuid>     # one conversation, call by call

The client saw a turn take about 9 seconds (2026-11-03). Every chat turn is one model call, plus one retry when the
reply does not fit its shape, and both are logged. The report answers which of these the time follows: the reply's
length (output tokens), the model's thinking (reasoning tokens, part of output), the prompt (input tokens, and how much
of it was cached), or retries.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import pathlib
import statistics
import sys
import uuid

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from mani.db import pool  # noqa: E402

def pool_database() -> str:
    """The host and database name the report reads, never the password."""
    from urllib.parse import urlparse

    from mani.config import get_settings

    url = urlparse(get_settings().database_url)
    return f"{url.hostname}:{url.port or 5432}{url.path}"


QUERY = """
select c.created_at, c.thread_id, c.message_id, c.model, c.outcome::text as outcome, c.latency_ms,
       c.input_tokens, c.cached_input_tokens, c.output_tokens, c.reasoning_tokens,
       coalesce(t.conversation_style, '-') as style
from admin.llm_calls c
left join public.threads t on t.id = c.thread_id
where c.purpose = 'chat' and c.created_at >= $1 and ($2::uuid is null or c.thread_id = $2)
order by c.created_at
"""
# Output size buckets, in tokens, for latency by how much the reply wrote (thinking included).
BUCKETS = ((0, 500), (500, 1000), (1000, 2000), (2000, 4000), (4000, 10**9))


def _median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def _p90(values: list[float]) -> float:
    return statistics.quantiles(values, n=10)[-1] if len(values) >= 10 else (max(values) if values else 0.0)


def _seconds(rows: list[dict]) -> list[float]:
    return [r["latency_ms"] / 1000 for r in rows]


def _summary(title: str, rows: list[dict]) -> list[str]:
    if not rows:
        return [f"  {title}: no calls"]
    seconds = _seconds(rows)
    visible = [r["output_tokens"] - r["reasoning_tokens"] for r in rows]
    cached_share = sum(r["cached_input_tokens"] for r in rows) / max(sum(r["input_tokens"] for r in rows), 1)
    per_token = [r["latency_ms"] / r["output_tokens"] for r in rows if r["output_tokens"]]
    return [
        f"  {title}: {len(rows)} call(s)",
        f"    time      median {_median(seconds):.1f} s, p90 {_p90(seconds):.1f} s, slowest {max(seconds):.1f} s",
        f"    input     median {_median([r['input_tokens'] for r in rows]):.0f} tokens, {cached_share:.0%} cached",
        f"    output    median {_median([r['output_tokens'] for r in rows]):.0f} tokens: "
        f"{_median([r['reasoning_tokens'] for r in rows]):.0f} thinking, {_median(visible):.0f} written",
        f"    speed     median {_median(per_token):.1f} ms per output token",
    ]


def report(rows: list[dict], *, slowest: int) -> list[str]:
    ok = [r for r in rows if r["outcome"] == "ok"]
    failed = [r for r in rows if r["outcome"] != "ok"]
    lines = [f"{len(rows)} chat call(s): {len(ok)} ok, {len(failed)} failed and retried or given up", ""]
    lines += _summary("all ok calls", ok)
    for style in sorted({r["style"] for r in ok}):
        lines += _summary(style, [r for r in ok if r["style"] == style])
    lines += ["", "  time by how much the reply wrote (thinking included):"]
    for low, high in BUCKETS:
        bucket = [r for r in ok if low <= r["output_tokens"] < high]
        if bucket:
            label = f"{low}+" if high >= 10**9 else f"{low}-{high}"
            lines.append(f"    {label:>10} tokens: {len(bucket):>3} call(s), median {_median(_seconds(bucket)):.1f} s")
    if failed:
        by = {}
        for r in failed:
            by.setdefault(r["outcome"], []).append(r)
        lines += ["", "  retries (each adds its own time to the turn):"]
        for outcome, group in sorted(by.items()):
            lines.append(f"    {outcome}: {len(group)} call(s), {sum(_seconds(group)):.1f} s in all, "
                         f"median {_median(_seconds(group)):.1f} s each")
    lines += ["", f"  the {slowest} slowest ok calls:"]
    for r in sorted(ok, key=lambda r: r["latency_ms"], reverse=True)[:slowest]:
        lines.append(
            f"    {r['latency_ms'] / 1000:5.1f} s  {r['style']:<10} in {r['input_tokens']:>6} "
            f"({r['cached_input_tokens']:>6} cached)  out {r['output_tokens']:>5} ({r['reasoning_tokens']:>5} thinking)  "
            f"{r['created_at']:%Y-%m-%d %H:%M} thread {str(r['thread_id'])[:8]}"
        )
    return lines


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--since", help="ISO date or date-time, UTC (default: 24 hours ago)")
    parser.add_argument("--thread", type=uuid.UUID, help="only this conversation")
    parser.add_argument("--slowest", type=int, default=10, help="how many of the slowest calls to list")
    args = parser.parse_args()
    since = (
        dt.datetime.fromisoformat(args.since).replace(tzinfo=dt.timezone.utc) if args.since
        else dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=24)
    )
    await pool.open_pool()
    try:
        async with pool.as_admin() as conn:
            rows = [dict(r) for r in await conn.fetch(QUERY, since, args.thread)]
            # With nothing in range, say where the calls are: a wrong date, or another database (the deployed app's
            # calls are stored in its own database, not a local one).
            latest = None if rows else await conn.fetchrow(
                "select max(created_at) as at, count(*) as n from admin.llm_calls where purpose = 'chat'"
            )
    finally:
        await pool.close_pool()
    print(f"chat calls since {since:%Y-%m-%d %H:%M} UTC" + (f", thread {args.thread}" if args.thread else ""))
    if not rows:
        where = pool_database()
        if latest and latest["n"]:
            print(f"no chat calls in range; this database ({where}) has {latest['n']} in all, the newest at "
                  f"{latest['at']:%Y-%m-%d %H:%M} UTC: try --since with an earlier date")
        else:
            print(f"no chat calls at all in this database ({where}): the conversation you want is in another one, such "
                  "as the deployed app's; point DATABASE_URL at it")
        return 0
    print("\n".join(report(rows, slowest=args.slowest)))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
