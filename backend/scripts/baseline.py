# ABOUTME: Totals, medians and ranges for a cost baseline, and the offline compare of two runs.
# ABOUTME: eval_replies.py --baseline measures; this summarizes and compares without a model or database.

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import statistics
import subprocess
import sys
from typing import Any
from urllib.parse import urlparse

# Every number a turn row carries, summed into a scenario's total for one run.
NUMBERS = (
    "calls", "input_tokens", "cached_input_tokens", "output_tokens", "reasoning_tokens",
    "model_latency_ms", "turn_latency_ms",
)
# What compare reads per scenario: the cost numbers plus the quality findings beside them.
COMPARED = NUMBERS + ("findings",)

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
LABEL = re.compile(r"[A-Za-z0-9_-]+")
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
BASELINES_DIR = pathlib.Path(__file__).with_name("baselines")

# The code a turn runs, for the diff hash. Saved baselines are left out, so writing or
# staging one never makes the next run look like different code.
CODE_PATHS = (
    "backend/mani", "backend/content", "backend/scripts", ":(exclude)backend/scripts/baselines",
)

# Header fields that say whether two files measured the same thing.
HEADER_FIELDS = ("model", "reasoning_effort", "content", "scripts", "git", "runs", "style")


def database_host(database_url: str) -> str | None:
    """The host alone: the URL also carries the database password."""
    return urlparse(database_url).hostname


def is_local(database_url: str) -> bool:
    """Only a local database is measured: hosted holds real people and another schema."""
    return database_host(database_url) in LOCAL_HOSTS


def digest(value: Any) -> str:
    """The first 12 hex characters of sha256: text as it is, anything else as sorted key JSON."""
    text = value if isinstance(value, str) else json.dumps(value, sort_keys=True, default=str)
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def git_state() -> dict[str, str | None]:
    """The commit, and a hash of the uncommitted code changes a turn would run."""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        diff = subprocess.run(
            ["git", "diff", "HEAD", "--", *CODE_PATHS], cwd=REPO_ROOT,
            capture_output=True, text=True, check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "diff": None}
    return {"commit": commit, "diff": digest(diff)}


def content_hashes(config: Any) -> dict[str, Any]:
    """What the turns read from the seeded content, as the prompt cache holds it.

    The model reads seeded rows, not the files, so this, not the commit, says which
    content was measured. Each framework is hashed whole, as the cache returns it.
    """
    return {
        "mani_base": digest(config.require("mani_base").content),
        "response_format": digest(config.require("response_format").content),
        "frameworks": {
            fid: digest(config.registry.get(fid).model_dump(mode="json"))
            for fid in sorted(config.registry.ids)
        },
    }


def turn_row(
    *, line: int, token: str, kind: str, rows: list[dict], turn_latency_ms: int
) -> dict[str, Any]:
    """One script line's cost: every provider call it made, in the order they were written.

    `token` is the authored script line, never what the model wrote; `rows` are the
    admin.llm_calls rows the turn produced.
    """
    return {
        "line": line, "token": token, "kind": kind, "calls": len(rows),
        "input_tokens": sum(r["input_tokens"] for r in rows),
        "cached_input_tokens": sum(r["cached_input_tokens"] for r in rows),
        "output_tokens": sum(r["output_tokens"] for r in rows),
        "reasoning_tokens": sum(r["reasoning_tokens"] for r in rows),
        "model_latency_ms": sum(r["latency_ms"] for r in rows),
        "turn_latency_ms": turn_latency_ms,
        "purposes": [r["purpose"] for r in rows],
        "outcomes": [r["outcome"] for r in rows],
    }


def scenario_result(
    *, run: int, scenario: str, findings: int, turns: list[dict]
) -> dict[str, Any]:
    return {
        "run": run, "scenario": scenario, "findings": findings,
        "totals": {key: sum(t[key] for t in turns) for key in NUMBERS},
        "turns": turns,
    }


def _spread(values: list[int]) -> dict[str, float | int]:
    """Median to one decimal place, since with an even run count it can fall between two."""
    return {
        "median": round(float(statistics.median(values)), 1), "min": min(values), "max": max(values)
    }


def _scenario_totals(result: dict) -> dict[str, int]:
    return {**result["totals"], "findings": result["findings"]}


def summarize(results: list[dict]) -> dict[str, Any]:
    """Per scenario totals across runs (what compare reads), per line numbers for diagnosis,
    and the median, minimum and maximum of the whole set's totals."""
    scenarios = list(dict.fromkeys(r["scenario"] for r in results))
    summary: dict[str, Any] = {}
    for name in scenarios:
        runs = [r for r in results if r["scenario"] == name]
        totals = [_scenario_totals(r) for r in runs]
        lines: dict[int, list[dict]] = {}
        for run in runs:
            for turn in run["turns"]:
                lines.setdefault(turn["line"], []).append(turn)
        summary[name] = {
            "totals": {key: _spread([t[key] for t in totals]) for key in COMPARED},
            "lines": [
                {
                    "line": line, "present_in": len(turns),
                    **{key: _spread([t[key] for t in turns]) for key in NUMBERS},
                }
                for line, turns in sorted(lines.items())
            ],
        }

    per_run: dict[int, dict[str, int]] = {}
    for result in results:
        run = per_run.setdefault(result["run"], dict.fromkeys(COMPARED, 0))
        for key, value in _scenario_totals(result).items():
            run[key] += value
    spreads = {key: _spread([run[key] for run in per_run.values()]) for key in COMPARED}
    return {
        "summary": summary,
        "totals": {
            stat: {key: spreads[key][stat] for key in COMPARED}
            for stat in ("median", "min", "max")
        },
    }


def reasoning_reported(efforts: dict[str, str | None], results: list[dict]) -> bool:
    """False when some call was asked to think and no call reported any thinking at all,
    which means the count is being lost, not that the model thought for free."""
    asked_to_think = any(effort not in (None, "none") for effort in efforts.values())
    if not asked_to_think:
        return True
    return any(r["totals"]["reasoning_tokens"] > 0 for r in results)


class NotABaseline(Exception):
    pass


def load(path: pathlib.Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise NotABaseline(f"{path}: no such file") from exc
    except json.JSONDecodeError as exc:
        raise NotABaseline(f"{path}: not JSON") from exc
    if not isinstance(data, dict) or not {"label", "summary", "totals"} <= data.keys():
        raise NotABaseline(f"{path}: not a baseline file")
    return data


def _change(before: float | None, after: float | None) -> str:
    if before is None or after is None:
        return f"{_value(before):>12} {_value(after):>12} {'':>12} {'':>8}"
    difference = round(after - before, 1)
    percent = f"{100 * difference / before:+.1f}%" if before else "n/a"
    return f"{_value(before):>12} {_value(after):>12} {difference:>+12} {percent:>8}"


def _value(value: float | None) -> str:
    return "missing" if value is None else str(value)


def _table(title: str, before: dict | None, after: dict | None) -> list[str]:
    lines = [f"\n{title}", f"{'':<20} {'before':>12} {'after':>12} {'change':>12} {'%':>8}"]
    for key in COMPARED:
        lines.append(f"{key:<20} {_change((before or {}).get(key), (after or {}).get(key))}")
    return lines


def compare(before: dict[str, Any], after: dict[str, Any]) -> str:
    """The median of each per scenario total before and after, and what changed in what
    was measured. Reads the two files only."""
    lines = [f"before: {before['label']}  after: {after['label']}"]
    differences = [
        f"  {field}: {before.get(field)} -> {after.get(field)}"
        for field in HEADER_FIELDS
        if before.get(field) != after.get(field)
    ]
    lines += ["measured differently:", *differences] if differences else ["measured the same way"]

    names = list(dict.fromkeys([*before["summary"], *after["summary"]]))
    for name in names:
        lines += _table(
            name,
            _medians(before["summary"].get(name)),
            _medians(after["summary"].get(name)),
        )
    lines += _table("total", before["totals"]["median"], after["totals"]["median"])
    return "\n".join(lines)


def _medians(scenario: dict | None) -> dict | None:
    if scenario is None:
        return None
    return {key: spread["median"] for key, spread in scenario["totals"].items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare two saved cost baselines.")
    commands = parser.add_subparsers(dest="command", required=True)
    compare_command = commands.add_parser("compare", help="print what changed between two runs")
    compare_command.add_argument("before", type=pathlib.Path)
    compare_command.add_argument("after", type=pathlib.Path)
    args = parser.parse_args(argv)

    try:
        before, after = load(args.before), load(args.after)
    except NotABaseline as exc:
        print(exc, file=sys.stderr)
        return 1
    print(compare(before, after))
    return 0


if __name__ == "__main__":
    sys.exit(main())
