# ABOUTME: A conversation as a timeline of what code decided on each turn, from admin.turn_traces: the moment, the
# ABOUTME: stage before and after, what the model reported, what code applied, its notes and checks. Reads only.

"""Why each turn of a conversation went the way it did.

    .venv/bin/python scripts/trace.py --thread <uuid>           # decisions only
    .venv/bin/python scripts/trace.py --latest --text           # the newest conversation, with the messages
    .venv/bin/python scripts/trace.py --thread <uuid> --raw     # also the model's raw reply, while it is kept

Decisions hold no words. --text prints the conversation itself and --raw the model's reply, which carries their
words: use them for review on your own machine. Turns from before migration 027 have no trace.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import sys
import uuid

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from mani.db import pool  # noqa: E402

MESSAGES = """
select m.id, m.role::text as role, m.content, m.selected_prompt, m.created_at,
       t.trace, t.raw_reply
from public.messages m
left join admin.turn_traces t on t.message_id = m.id
where m.thread_id = $1
order by m.created_at
"""
LATEST = "select id from public.threads where deleted_at is null order by last_message_at desc nulls last limit 1"


def _value(value) -> str:
    if isinstance(value, dict):
        return ", ".join(f"{k} {_value(v)}" for k, v in value.items())
    if isinstance(value, list):
        return " | ".join(_value(v) for v in value)
    return str(value)


def turn_lines(number: int, trace: dict) -> list[str]:
    """One turn's decisions, a heading and a line for each part present."""
    moment = trace.get("moment", "?")
    stage = ""
    if trace.get("phase_before") or trace.get("phase_after"):
        stage = f" · {trace.get('phase_before') or '-'} -> {trace.get('phase_after') or '-'}"
    took = f" ({trace['latency_ms'] / 1000:.1f} s)" if trace.get("latency_ms") else ""
    their = f"their message {trace['their_message']} · " if trace.get("their_message") else ""
    lines = [f"#{number}  {their}{moment}{stage}{took}"]
    for key, label in (
        ("model", "model reported"), ("applied", "code applied"), ("walk", "walk"), ("stages", "stages"),
        ("may_move", "may move"), ("moved", "moved to the set"), ("offered", "offered"),
        ("offer_dropped", "offer unusable"), ("funnel", "funnel"), ("core_fixed", "core held fixed"),
        ("buttons", "buttons"), ("notes", "notes"), ("checks", "checks"), ("guarded", "guarded"),
        ("safety", "safety"), ("reason", "reason"),
    ):
        if key in trace:
            value = trace[key]
            if key == "stages":
                value = " ".join(f"{r['stage']}={r['status']}{'*' if r.get('asking') else ''}" for r in value)
            lines.append(f"    {label}: {_value(value)}")
    return lines


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    which = parser.add_mutually_exclusive_group(required=True)
    which.add_argument("--thread", type=uuid.UUID, help="the conversation")
    which.add_argument("--latest", action="store_true", help="the most recently active conversation")
    parser.add_argument("--text", action="store_true", help="also print the messages (their words)")
    parser.add_argument("--raw", action="store_true", help="also print the model's raw reply, while it is kept")
    args = parser.parse_args()
    await pool.open_pool()
    try:
        async with pool.as_admin() as conn:
            thread_id = args.thread or await conn.fetchval(LATEST)
            if thread_id is None:
                print("No conversations.")
                return 1
            rows = [dict(r) for r in await conn.fetch(MESSAGES, thread_id)]
    finally:
        await pool.close_pool()
    print(f"thread {thread_id}: {len(rows)} message(s)")
    number = 0
    for row in rows:
        trace = row["trace"]
        if isinstance(trace, str):
            trace = json.loads(trace)
        if args.text:
            mark = ">" if row["role"] == "user" else "<"
            said = row["selected_prompt"] and f"[tapped] {row['selected_prompt']}" or " ".join(row["content"].split())
            print(f"  {mark} {said}")
        if row["role"] != "mani" or not trace:
            continue
        number += 1
        print("\n".join(turn_lines(number, trace)))
        if args.raw and row["raw_reply"]:
            raw = row["raw_reply"] if isinstance(row["raw_reply"], dict) else json.loads(row["raw_reply"])
            print("    raw reply: " + json.dumps(raw, ensure_ascii=False))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
