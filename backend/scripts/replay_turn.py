# ABOUTME: Replays one turn against the real model from a seeded thread, several times, and prints each reply.
# ABOUTME: Counts the replies each scenario's patterns match, so a prompt change is measured before and after.

from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import pathlib
import re
import sys
import uuid

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from mani.auth.jwt import Claims  # noqa: E402
from mani.chat import orchestrator  # noqa: E402
from mani.db import pool  # noqa: E402

SCENARIOS = pathlib.Path(__file__).with_name("replay_scenarios.json")


def _override(assignment: str) -> None:
    """Set a module constant for this run, as `mani.chat.context._WHEN_UNSURE=text`, so a wording can be
    compared with and without itself."""
    target, value = assignment.split("=", 1)
    module, name = target.rsplit(".", 1)
    setattr(importlib.import_module(module), name, value)


async def _seed(user: uuid.UUID, scenario: dict) -> uuid.UUID:
    """A thread holding the scenario's history and the framework state it was in."""
    claims = Claims(sub=str(user), raw={"sub": str(user), "role": "authenticated"})
    async with pool.as_user(claims) as conn:
        thread, _ = await orchestrator.start_thread(conn, claims)
    async with pool.as_admin() as conn:
        await conn.execute("delete from public.messages where thread_id = $1", thread.id)
        for entry in scenario["history"]:
            await conn.execute(
                "insert into public.messages (thread_id, user_id, role, content, prompt_options) "
                "values ($1, $2, $3, $4, $5::jsonb)",
                thread.id, user, entry["role"], entry["content"], entry.get("buttons"),
            )
        await conn.execute(
            "update public.threads set conversation_style = $2 where id = $1", thread.id, scenario["style"]
        )
        if scenario.get("framework"):
            await conn.execute(
                "insert into public.thread_technique_state "
                "(thread_id, user_id, framework_id, outcome, phase, at_message_count, library_offered_since) "
                "values ($1, $2, $3, 'accepted', $4, 5, false)",
                thread.id, user, scenario["framework"], scenario["phase"],
            )
            await conn.execute(
                "insert into public.thread_techniques_offered (thread_id, user_id, framework_id) values ($1, $2, $3)",
                thread.id, user, scenario["framework"],
            )
    return thread.id


async def _run_once(name: str, scenario: dict, number: int) -> str:
    user = uuid.uuid4()
    claims = Claims(sub=str(user), raw={"sub": str(user), "role": "authenticated"})
    async with pool.as_admin() as conn:
        await conn.execute(
            "insert into auth.users (id, email) values ($1, $2)", user, f"replay.{name}.{number}.{user}@scenario.check"
        )
    try:
        thread_id = await _seed(user, scenario)
        async with pool.as_user(claims) as conn:
            turn = await orchestrator.send(conn, claims, thread_id, scenario["message"])
        return turn.content
    finally:
        async with pool.as_admin() as conn:
            await conn.execute("delete from admin.llm_calls where user_id = $1", user)
            await conn.execute("delete from auth.users where id = $1", user)


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", help="run only this scenario from replay_scenarios.json")
    parser.add_argument("--runs", type=int, default=3, help="replays per scenario; one run is noise")
    parser.add_argument("--override", action="append", default=[], help="module.NAME=value for this run")
    args = parser.parse_args()
    for assignment in args.override:
        _override(assignment)
    scenarios = json.loads(SCENARIOS.read_text())
    chosen = {k: v for k, v in scenarios.items() if not args.scenario or k == args.scenario}
    await pool.open_pool()
    try:
        for name, scenario in chosen.items():
            print(f"\n=== {name}: {scenario['message']!r}  ({scenario['about']})")
            replies = [await _run_once(name, scenario, n) for n in range(1, args.runs + 1)]
            for number, reply in enumerate(replies, 1):
                print(f"  {number}. {reply!r}")
            for label, pattern in scenario.get("flags", {}).items():
                matched = sum(bool(re.search(pattern, reply, re.IGNORECASE)) for reply in replies)
                print(f"  -> {label}: {matched} of {len(replies)}")
    finally:
        await pool.close_pool()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
