# ABOUTME: Turns one regression run into a summary (committed, for comparing runs), a full record (gitignored, with
# ABOUTME: transcripts) and a Markdown report, and compares the summary with the previous run's.

from __future__ import annotations

import json
import pathlib
from collections import Counter, defaultdict

from evals.regression.checks import DETERMINISTIC, GAP, PENDING, PERFORMANCE
from evals.regression.metrics import spread

RESULTS = pathlib.Path(__file__).resolve().parents[1] / "results"
SUMMARIES = RESULTS / "summaries"
# Each stage of a turn the latency table reports, by its key in a turn's figures, in the table's order.
STAGES = (("End to end", "end_to_end_s"), ("Model", "model_s"), ("Model, to first chunk", "first_token_s"),
          ("Read pass", "read_s"), ("Write pass", "write_s"), ("Backend (end to end − model)", "backend_s"))


def summarize(run: dict) -> dict:
    """What is kept in git: every check's outcome and the figures, never a full transcript."""
    scenarios, totals, seconds = [], Counter(), defaultdict(list)
    for s in run["scenarios"]:
        checks = s.get("checks", [])
        for c in checks:
            totals[f"{c['kind']}_{'passed' if c['passed'] else 'failed'}"] += 1
        for t in s.get("turns", []):
            for _, key in STAGES:
                if t.get(key) is not None:
                    seconds[key].append(t[key])
        scenarios.append({
            "id": s["id"], "title": s["title"], "group": s["group"], "status": s["status"],
            "gap_reason": s.get("gap_reason"),
            "checks": checks,
            "judge": {k: v["score"] for k, v in (s.get("judge") or {}).get("scores", {}).items()} or None,
            "judge_summary": (s.get("judge") or {}).get("summary"),
            "usage": s.get("usage"),
        })
    failed = [(s["id"], c) for s in run["scenarios"] for c in s.get("checks", []) if not c["passed"]]
    return {
        "run_id": run["run_id"], "git_sha": run["git_sha"], "chat_models": run["chat_models"],
        "scenarios": scenarios,
        "totals": dict(totals),
        "critical_failures": [{"scenario": sid, **c} for sid, c in failed if c["critical"]],
        "latency": {key: spread(seconds[key]) for _, key in STAGES},
        "cost_usd": _sum([(s.get("usage") or {}).get("cost_usd") for s in run["scenarios"] if s.get("usage")]),
    }


def _sum(values: list[float | None]) -> float | None:
    return sum(values) if values and all(v is not None for v in values) else None


def previous_summary(before: str) -> dict | None:
    """The latest full run before this one; benchmark runs (`regress-bench-…`) are never the baseline."""
    earlier = sorted(p for p in SUMMARIES.glob("regress-2*.json") if p.stem < f"regress-{before}")
    return json.loads(earlier[-1].read_text()) if earlier else None


def compare(now: dict, before: dict | None) -> dict | None:
    """Checks that changed outcome since the previous run, and how the median turn and cost moved."""
    if before is None:
        return None
    def outcomes(summary: dict) -> dict[tuple[str, str], bool]:
        return {(s["id"], c["check"]): c["passed"] for s in summary["scenarios"] for c in s["checks"]}
    old, new = outcomes(before), outcomes(now)
    p50 = lambda s: s["latency"]["end_to_end_s"]["p50"]  # noqa: E731
    return {
        "previous_run": before["run_id"],
        "newly_failing": sorted(f"{sid} {check}" for (sid, check), ok in new.items() if not ok and old.get((sid, check))),
        "newly_passing": sorted(f"{sid} {check}" for (sid, check), ok in new.items() if ok and old.get((sid, check)) is False),
        "p50_end_to_end_s": {"before": p50(before), "now": p50(now)},
        "cost_usd": {"before": before.get("cost_usd"), "now": now.get("cost_usd")},
    }


def repeated_patterns(run: dict) -> list[str]:
    return [f"{s['id']} turn {c['turn']}: {c['detail']}" for s in run["scenarios"] for c in s.get("checks", [])
            if not c["passed"] and c["check"] in ("no_repeated_question", "no_repeated_opener")]


def markdown(run: dict, summary: dict, comparison: dict | None) -> str:
    t, lat = summary["totals"], summary["latency"]
    fmt = lambda v: "n/a" if v is None else f"{v:.2f}"  # noqa: E731
    lines = [f"# Mani regression run {run['run_id']}", "",
             f"Commit `{run['git_sha']}` · chat model(s) {', '.join(summary['chat_models']) or 'unknown'} · "
             f"{sum(1 for s in run['scenarios'] if s['status'] == 'run')} scenarios run, "
             f"{sum(1 for s in run['scenarios'] if s['status'] == 'gap')} reported as gaps", "",
             "## Deterministic assertions", "",
             f"- Passed {t.get(f'{DETERMINISTIC}_passed', 0)}, failed {t.get(f'{DETERMINISTIC}_failed', 0)}",
             f"- Critical safety failures: {len(summary['critical_failures'])}",
             f"- Latency over the scenario limit: {t.get(f'{PERFORMANCE}_failed', 0)} scenario(s)",
             f"- Requirement gaps (paused or retired by a Decision in force): {t.get(f'{GAP}_failed', 0)}",
             f"- Pending requirements (not yet recorded in docs/client and approved; never fail the run): failed "
             f"{t.get(f'{PENDING}_failed', 0)}, passed {t.get(f'{PENDING}_passed', 0)}", ""]
    if summary["critical_failures"]:
        lines += ["### Critical", ""] + [f"- **{c['scenario']}** `{c['check']}` turn {c['turn']}: {c['detail']}"
                                         for c in summary["critical_failures"]] + [""]
    lines += ["## By scenario", ""]
    for s in run["scenarios"]:
        if s["status"] == "gap":
            lines += [f"### {s['id']} {s['title']} — gap", "", s.get("gap_reason") or "", ""]
            continue
        failed = [c for c in s["checks"] if not c["passed"]]
        lines += [f"### {s['id']} {s['title']} — {'PASS' if not any(c['kind'] == DETERMINISTIC for c in failed) else 'FAIL'}", ""]
        for c in failed:
            # A check's turn counts within its own conversation; only the isolation check reads the second one.
            own = [x for x in s.get("exchanges", []) if x["conversation"] == (2 if c["check"] == "isolation" else 1)]
            turn = own[c["turn"] - 1] if c["turn"] and c["turn"] <= len(own) else None
            source = f" (source: {c['source']})" if c.get("source") else ""
            lines.append(f"- `{c['kind']}` **{c['check']}**: {c['detail']}{source}")
            if turn:
                lines += [f"  - YOU: {turn['said']}", f"  - MANI: {turn['reply']}"]
        if judged := s.get("judge"):
            if "error" in judged:
                lines.append(f"- Judge failed: {judged['error']}")
            else:
                scores = ", ".join(f"{k} {v['score']}" for k, v in judged["scores"].items())
                lines += [f"- Judged: {scores}", f"- Judge: {judged['summary']}"]
                if judged["missing"]:
                    lines.append(f"- Judge skipped: {', '.join(judged['missing'])}")
        lines.append("")
    if patterns := repeated_patterns(run):
        lines += ["## Repeated questions and openers", ""] + [f"- {p}" for p in patterns] + [""]
    lines += ["## Latency (seconds)", "", "| | n | p50 | p95 | p99 | max |", "|---|---|---|---|---|---|"]
    for name, key in STAGES:
        d = lat[key]
        if not d["n"] and key != "end_to_end_s":
            continue
        lines.append(f"| {name} | {d['n']} | {fmt(d['p50'])} | {fmt(d['p95'])} | {fmt(d['p99'])} | {fmt(d['max'])} |")
    lines += ["", f"p99 over {lat['end_to_end_s']['n']} turns is indicative only.", "",
              f"Cost: {'$' + format(summary['cost_usd'], '.5f') if summary['cost_usd'] is not None else 'unknown (a chat call recorded no cost)'}", ""]
    if comparison:
        lines += [f"## Against {comparison['previous_run']}", "",
                  f"- Newly failing: {', '.join(comparison['newly_failing']) or 'none'}",
                  f"- Newly passing: {', '.join(comparison['newly_passing']) or 'none'}",
                  f"- Median turn: {fmt(comparison['p50_end_to_end_s']['before'])} s → "
                  f"{fmt(comparison['p50_end_to_end_s']['now'])} s", ""]
    return "\n".join(lines)


def write(run: dict) -> pathlib.Path:
    summary = summarize(run)
    comparison = compare(summary, previous_summary(run["run_id"]))
    SUMMARIES.mkdir(parents=True, exist_ok=True)
    (SUMMARIES / f"regress-{run['run_id']}.json").write_text(json.dumps({**summary, "comparison": comparison},
                                                                        indent=1, default=str))
    (RESULTS / f"regress-{run['run_id']}-full.json").write_text(json.dumps(run, indent=1, default=str))
    out = RESULTS / "regress-latest.md"
    out.write_text(markdown(run, summary, comparison))
    return out
