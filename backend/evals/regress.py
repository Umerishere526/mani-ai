# ABOUTME: The conversation regression suite: plays evals/regression/scenarios.json through the real stack, checks each
# ABOUTME: conversation, judges it, and writes a report. Costs real model calls; see --help and .claude/BACKEND.md.

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys
from urllib.parse import urlparse

# A scripted person answers faster than anyone types, so the per-minute limit is off here, as in check_suite.
os.environ["MINUTE_MESSAGE_LIMIT"] = "0"

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402

from evals.regression import checks, report  # noqa: E402
from evals.regression.play import error_record, gap_record, play  # noqa: E402
from mani.config import get_settings  # noqa: E402
from mani.db import config_tables, pool  # noqa: E402
from mani.chat.techniques import stages_of  # noqa: E402

SCENARIOS = pathlib.Path(__file__).resolve().parent / "regression" / "scenarios.json"
LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")
# OpenRouter holds each running request's cost against the balance; a few at a time keeps the holds small.
CONCURRENCY = 3


def _args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Mani conversation regression suite (real model calls).")
    p.add_argument("--scenario", action="append", help="Run only this scenario id (repeatable), e.g. TC-01.")
    p.add_argument("--only", choices=["framework", "pacing", "safety", "isolation"], help="Run one group.")
    p.add_argument("--list", action="store_true", help="List the scenarios and gaps, then exit. No calls.")
    p.add_argument("--no-judge", action="store_true", help="Skip the judged quality layer.")
    p.add_argument("--cost", action="store_true", help="Read each chat call's billed cost from OpenRouter.")
    p.add_argument("--bench", type=int, metavar="N", help="Play the selection N times for latency only (no judge).")
    p.add_argument("--strict-latency", action="store_true", help="Fail the run when a turn exceeds its limit.")
    p.add_argument("--allow-remote-db", action="store_true",
                   help="Allow a DATABASE_URL that is not local. Never point this at production.")
    return p.parse_args(argv)


def _selected(args: argparse.Namespace) -> list[dict]:
    scenarios = json.loads(SCENARIOS.read_text())["scenarios"]
    if args.scenario:
        wanted = set(args.scenario)
        scenarios = [s for s in scenarios if s["id"] in wanted]
        if missing := wanted - {s["id"] for s in scenarios}:
            sys.exit(f"Unknown scenario(s): {', '.join(sorted(missing))}")
    if args.only:
        scenarios = [s for s in scenarios if s["group"] == args.only]
    return scenarios


def _git_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


async def _registry() -> dict[str, list[str]]:
    """Each active framework's stages, from the same table the chat reads."""
    async with pool.as_admin() as conn:
        return {f.id: stages_of(f) for f in await config_tables.list_active_frameworks(conn)}


def _runnable(scenario: dict, stages: dict[str, list[str]]) -> bool:
    """A gap scenario runs once a framework it expects is active again."""
    if scenario["status"] != "gap":
        return True
    return any(f in stages for f in scenario.get("expect", {}).get("framework", []))


async def _run(args: argparse.Namespace, scenarios: list[dict]) -> dict:
    stages, allowed = await _registry(), checks.allowed_labels()
    rounds = args.bench or 1
    gate = asyncio.Semaphore(CONCURRENCY)
    async with httpx.AsyncClient() as http:
        async def one(scenario: dict, n: int) -> dict:
            if not _runnable(scenario, stages):
                return gap_record(scenario)
            async with gate:
                print(f"… {scenario['id']}{f' #{n}' if args.bench else ''}", flush=True)
                try:
                    record = await play(scenario, stages, allowed, judged=not (args.no_judge or args.bench),
                                        read_cost=args.cost, http=http)
                except Exception as error:  # noqa: BLE001 - one scenario's failure never loses the others
                    record = error_record(scenario, error)
            return {**record, "id": f"{record['id']}#{n}" if args.bench else record["id"]}
        records = await asyncio.gather(*(one(s, n) for n in range(1, rounds + 1) for s in scenarios))
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%d-%H%M%S")
    models = sorted({m for r in records for m in (r.get("usage") or {}).get("models", [])})
    return {"run_id": f"bench-{stamp}" if args.bench else stamp, "git_sha": _git_sha(), "chat_models": models,
            "scenarios": records}


def _exit_code(run: dict, strict_latency: bool) -> int:
    failing = {checks.DETERMINISTIC} | ({checks.PERFORMANCE} if strict_latency else set())
    return int(any(not c["passed"] and c["kind"] in failing for s in run["scenarios"] for c in s["checks"]))


async def main(argv: list[str]) -> int:
    args = _args(argv)
    scenarios = _selected(args)
    if args.list:
        for s in scenarios:
            print(f"{s['id']}  {s['group']:<9} {s['status']:<4} {s['style']:<10} {s['title']}")
        return 0
    host = urlparse(get_settings().database_url).hostname
    if host not in LOCAL_HOSTS and not args.allow_remote_db:
        print(f"Refusing to run against database host {host!r}: the suite creates test people and conversations. "
              "Use a local or dedicated test database, or pass --allow-remote-db for a test project.")
        return 2
    await pool.open_pool()
    try:
        run = await _run(args, scenarios)
    finally:
        await pool.close_pool()
    out = report.write(run)
    for s in run["scenarios"]:
        failed = [c["check"] for c in s["checks"] if not c["passed"] and c["kind"] == checks.DETERMINISTIC]
        status = "GAP " if s["status"] == "gap" else ("FAIL" if failed else "PASS")
        print(f"{status}  {s['id']:<8} {', '.join(failed)}")
    print(f"\nReport: {out}")
    return _exit_code(run, args.strict_latency)


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
