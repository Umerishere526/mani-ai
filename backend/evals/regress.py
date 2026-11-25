# ABOUTME: The conversation regression suite: plays evals/regression/scenarios.json through the real stack, checks each
# ABOUTME: conversation, judges it, and writes a report. Costs real model calls; see --help and .claude/BACKEND.md.

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys
from collections import defaultdict

# A scripted person answers faster than anyone types, so the per-minute limit is off here, as in check_suite.
os.environ["MINUTE_MESSAGE_LIMIT"] = "0"

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402

from evals.drive import remote_database_refusal  # noqa: E402
from evals.regression import checks, report  # noqa: E402
from evals.regression.judge import conversation_of, judge, judge_modes  # noqa: E402
from evals.regression.play import error_record, gap_record, play  # noqa: E402
from mani.db import config_tables, pool  # noqa: E402
from mani.chat.techniques import stages_of  # noqa: E402
from mani.prompts import cache, composer  # noqa: E402
from scripts.seed import parse_prompt  # noqa: E402

SCENARIOS = pathlib.Path(__file__).resolve().parent / "regression" / "scenarios.json"
# Scenarios nobody tunes against: played only to see whether a gain on the benchmark holds on conversations it never
# saw (muhammad's brief of 2026-11-25). Their transcripts are for scoring, never for writing prompt examples.
HOLDOUT = pathlib.Path(__file__).resolve().parent / "regression" / "holdout.json"
# OpenRouter holds each running request's cost against the balance; a few at a time keeps the holds small.
CONCURRENCY = 3
# A judge call holds no chat request, so more of them run at once when a saved run is judged again.
REJUDGE_CONCURRENCY = 6
STYLES = 3


def _args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Mani conversation regression suite (real model calls).")
    p.add_argument("--scenario", action="append", help="Run only this scenario id (repeatable), e.g. TC-01.")
    p.add_argument("--only", choices=["framework", "pacing", "safety", "isolation"], help="Run one group.")
    p.add_argument("--holdout", action="store_true",
                   help="Play the held-out scenarios instead of the benchmark: for measuring, never for tuning.")
    p.add_argument("--list", action="store_true", help="List the scenarios and gaps, then exit. No calls.")
    p.add_argument("--no-judge", action="store_true", help="Skip the judged quality layer.")
    p.add_argument("--bench", type=int, metavar="N", help="Play the selection N times for latency only (no judge).")
    p.add_argument("--jobs", type=int, default=CONCURRENCY, metavar="N", help="How many scenarios play at once.")
    p.add_argument("--rejudge", metavar="FULL_JSON",
                   help="Judge a saved run's conversations again on the current dimensions. No chat calls.")
    p.add_argument("--model", help="Experiment: the chat model for this run only; the prompt row is not touched.")
    p.add_argument("--effort", help="Experiment: the chat model's reasoning effort for this run only.")
    p.add_argument("--prompt-file", help="Experiment: a prompt file whose body is the mani prompt for this run only.")
    p.add_argument("--strict-latency", action="store_true", help="Fail the run when a turn exceeds its limit.")
    p.add_argument("--allow-remote-db", action="store_true",
                   help="Allow a DATABASE_URL that is not local. Never point this at production.")
    return p.parse_args(argv)


def _definitions(path: pathlib.Path) -> list[dict]:
    return json.loads(path.read_text())["scenarios"] if path.exists() else []


def _selected(args: argparse.Namespace) -> list[dict]:
    scenarios = _definitions(HOLDOUT if args.holdout else SCENARIOS)
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


def _stamp() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y%m%d-%H%M%S")


def experiment(args: argparse.Namespace) -> dict | None:
    """Swaps the chat model, its effort or the prompt's text for this process only, and says what was swapped; None
    when the run plays what is seeded. The prompt row and any running app are untouched."""
    if not (args.model or args.effort or args.prompt_file):
        return None
    row_settings = composer.model_settings

    def model_settings(config: cache.Config, name: str) -> tuple[str, dict, dict]:
        model, parameters, routing = row_settings(config, name)
        if name != "mani":
            return model, parameters, routing
        effort = {"reasoning_effort": args.effort} if args.effort else {}
        return args.model or model, {**parameters, **effort}, routing

    composer.model_settings = model_settings
    if args.prompt_file:
        body = parse_prompt(pathlib.Path(args.prompt_file))["content"]
        seeded = cache.load

        async def with_prompt() -> cache.Config:
            config = await seeded()
            mani = config.prompts["mani"].model_copy(update={"content": body})
            return dataclasses.replace(config, prompts={**config.prompts, "mani": mani})

        cache.load = with_prompt
    return {"model": args.model, "effort": args.effort, "prompt_file": args.prompt_file}


async def _registry() -> tuple[dict[str, list[str]], dict[str, str]]:
    """Each active framework's stages and its name, by id, from the same table the chat reads."""
    async with pool.as_admin() as conn:
        frameworks = await config_tables.list_active_frameworks(conn)
    return {f.id: stages_of(f) for f in frameworks}, {f.id: f.name for f in frameworks}


def _runnable(scenario: dict, stages: dict[str, list[str]]) -> bool:
    """A gap scenario runs once a framework it expects is active again."""
    if scenario["status"] != "gap":
        return True
    return any(f in stages for f in scenario.get("expect", {}).get("framework", []))


async def modes(http: httpx.AsyncClient, records: list[dict], scenarios: list[dict]) -> list[dict]:
    """One verdict on how differently the styles handled an opening, for each `triplet` whose three styles played."""
    by_id = {s["id"]: s for s in scenarios}
    groups: dict[str, dict] = defaultdict(dict)
    for record in records:
        scenario = by_id.get(record["id"])
        if scenario and scenario.get("triplet") and record.get("exchanges"):
            groups[scenario["triplet"]][scenario["style"]] = conversation_of(record, scenario["style"])
    verdicts = []
    for name, conversations in sorted(groups.items()):
        if len(conversations) < STYLES:
            continue
        try:
            verdicts.append(await judge_modes(http, name, conversations))
        except Exception as error:  # noqa: BLE001 - a failed judge call is reported, never allowed to end the run
            verdicts.append({"triplet": name, "styles": sorted(conversations), "error": f"{type(error).__name__}: {error}"})
    return verdicts


async def _run(args: argparse.Namespace, scenarios: list[dict], swapped: dict | None) -> dict:
    stages, names = await _registry()
    allowed = checks.allowed_labels(tuple(names.values()))
    rounds = args.bench or 1
    judged = not (args.no_judge or args.bench)
    gate = asyncio.Semaphore(args.jobs)
    async with httpx.AsyncClient() as http:
        async def one(scenario: dict, n: int) -> dict:
            if not _runnable(scenario, stages):
                return gap_record(scenario)
            async with gate:
                print(f"… {scenario['id']}{f' #{n}' if args.bench else ''}", flush=True)
                try:
                    record = await play(scenario, stages, names, allowed, judged=judged, http=http)
                except Exception as error:  # noqa: BLE001 - one scenario's failure never loses the others
                    record = error_record(scenario, error)
            return {**record, "id": f"{record['id']}#{n}" if args.bench else record["id"]}
        records = await asyncio.gather(*(one(s, n) for n in range(1, rounds + 1) for s in scenarios))
        compared = await modes(http, records, scenarios) if judged else []
    # Only a run of the seeded benchmark is a baseline for the next one: the others carry their kind in their id.
    kind = "bench-" if args.bench else "".join(f"{k}-" for k, on in (("exp", swapped), ("holdout", args.holdout)) if on)
    models = sorted({m for r in records for m in (r.get("usage") or {}).get("models", [])})
    return {"run_id": f"{kind}{_stamp()}", "git_sha": _git_sha(), "chat_models": models, "experiment": swapped,
            "scenarios": records, "modes": compared}


async def rejudge(path: pathlib.Path) -> dict:
    """A saved run with every conversation judged again on the current dimensions: the same words the person saw,
    scored by today's instrument, so runs from before and after a change of dimensions compare like for like."""
    saved = json.loads(path.read_text())
    definitions = {s["id"]: s for s in _definitions(SCENARIOS) + _definitions(HOLDOUT)}
    gate = asyncio.Semaphore(REJUDGE_CONCURRENCY)
    async with httpx.AsyncClient() as http:
        async def one(record: dict) -> dict:
            scenario = definitions.get(record["id"])
            if scenario is None or not record.get("exchanges"):
                return record
            async with gate:
                try:
                    verdict = await judge(http, conversation_of(record, scenario["style"]), scenario)
                except Exception as error:  # noqa: BLE001 - a failed judge call is reported, never allowed to end the run
                    verdict = {"error": f"{type(error).__name__}: {error}"}
            return {**record, "style": scenario["style"], "judge": verdict}
        records = await asyncio.gather(*(one(r) for r in saved["scenarios"]))
        compared = await modes(http, records, list(definitions.values()))
    return {**saved, "run_id": f"rejudge-{saved['run_id']}-{_stamp()}", "rejudged_from": saved["run_id"],
            "scenarios": records, "modes": compared}


def _exit_code(run: dict, strict_latency: bool) -> int:
    failing = {checks.DETERMINISTIC} | ({checks.PERFORMANCE} if strict_latency else set())
    return int(any(not c["passed"] and c["kind"] in failing for s in run["scenarios"] for c in s["checks"]))


async def main(argv: list[str]) -> int:
    args = _args(argv)
    if args.rejudge:
        out = report.write(await rejudge(pathlib.Path(args.rejudge)))
        print(f"Report: {out}")
        return 0
    scenarios = _selected(args)
    if args.list:
        for s in scenarios:
            print(f"{s['id']}  {s['group']:<9} {s['status']:<4} {s['style']:<10} {s['title']}")
        return 0
    if refusal := remote_database_refusal(args.allow_remote_db):
        print(refusal)
        return 2
    swapped = experiment(args)
    await pool.open_pool()
    try:
        run = await _run(args, scenarios, swapped)
    finally:
        await pool.close_pool()
    out = report.write(run)
    for s in run["scenarios"]:
        failed = [c["check"] for c in s["checks"] if not c["passed"] and c["kind"] == checks.DETERMINISTIC]
        status = "GAP " if s["status"] == "gap" else ("FAIL" if failed else "PASS")
        print(f"{status}  {s['id']:<8} {', '.join(failed)}")
    print(f"Report: {out}")
    return _exit_code(run, args.strict_latency)


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
