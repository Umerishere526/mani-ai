# ABOUTME: Scores the one-call turn's replies against ChatGPT's on muhammad's real test messages, several runs each.
# ABOUTME: Usage: python evals/run_eval.py [--variant NAME=MODEL[,EFFORT[,HOST|HOST...]]] [--prompt FILE] [--samples 3]

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import pathlib
import statistics
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402
from openai.lib._pydantic import to_strict_json_schema  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from mani.chat.facts import framework_guide  # noqa: E402
from mani.chat.reply import TurnReply  # noqa: E402
from mani.config import get_settings  # noqa: E402
from mani.db import pool  # noqa: E402
from mani.prompts import cache  # noqa: E402
from scripts.seed import PROMPTS_DIR, parse_prompt  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
JUDGE_MODEL = "openai/gpt-6.1-sol"
CRITERIA = {
    "understanding": "Shows it understood what is really at stake for them, and adds something they did not say.",
    "no_assumptions": "Invites their story before concluding; never assumes a cause, a feeling or that there is no reason.",
    "ideas": "Gives ideas to explore: a fair perspective, a distinction, something highlighted, permission, both feelings.",
    "question": "Ends on one good question: open, or options each with a reason. Not a thin either-or, not a fact-check.",
    "voice": "Warm, plain everyday words, no therapy talk, no lecture, no solutions or advice, no emojis.",
    "overall": "Compared with the reference reply: 5 = as good or better, 3 = clearly weaker, 1 = much worse.",
}


class Score(BaseModel):
    understanding: int = Field(ge=1, le=5)
    no_assumptions: int = Field(ge=1, le=5)
    ideas: int = Field(ge=1, le=5)
    question: int = Field(ge=1, le=5)
    voice: int = Field(ge=1, le=5)
    overall: int = Field(ge=1, le=5)
    why: str = Field(description="One or two sentences on the biggest difference from the reference.")


class RuleVerdict(BaseModel):
    passed: bool
    why: str


def variant(spec: str) -> dict:
    name, _, rest = spec.partition("=")
    model, effort, hosts = (rest.split(",") + [None, None])[:3]
    return {"name": name, "model": model, "effort": effort or None,
            "hosts": [h for h in (hosts or "").split("|") if h]}


async def post(http, settings, body) -> tuple[dict, float]:
    began = time.monotonic()
    for attempt in range(3):
        r = await http.post(f"{settings.openrouter_base_url}/chat/completions", json=body, timeout=180,
                            headers={"Authorization": f"Bearer {settings.openrouter_api_key}"})
        if r.status_code == 200 and r.json().get("choices"):
            return r.json(), time.monotonic() - began
        await asyncio.sleep(2 * (attempt + 1))
    raise RuntimeError(f"{body['model']}: {r.status_code} {r.text[:300]}")


async def reply(http, settings, v, system, case) -> dict:
    facts = "Facts for this reply (never mention them):\n" + "\n".join(
        f"- {line}" for line in [f"Their style: {case['style']}.", *case["facts"]])
    body = {"model": v["model"], "messages": [{"role": "system", "content": system},
                                              {"role": "assistant", "content": case["opener"]}]
            + case["turns"] + [{"role": "system", "content": facts}],
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "reply", "strict": True, "schema": to_strict_json_schema(TurnReply)}},
            "usage": {"include": True}}
    if v["effort"]:
        body["reasoning"] = {"effort": v["effort"]}
    if v["hosts"]:
        body["provider"] = {"only": v["hosts"], "zdr": True}
    if v["model"].startswith("anthropic/"):
        body["cache_control"] = {"type": "ephemeral"}
    try:
        raw, took = await post(http, settings, body)
        out = json.loads(raw["choices"][0]["message"]["content"])
        return {**out, "seconds": round(took, 1), "cost": (raw.get("usage") or {}).get("cost")}
    except Exception as error:  # noqa: BLE001
        return {"error": str(error)[:300], "text": "", "seconds": None, "cost": None}


async def judge(http, settings, case, got) -> dict:
    convo = "\n\n".join(f"{t['role'].upper()}: {t['content']}" for t in case["turns"])
    rubric = "\n".join(f"- {k}: {v}" for k, v in CRITERIA.items())
    if case["reference"] is not None:
        prompt = (f"You are judging a reply from MANI, a supportive chat companion, against a reference reply.\n\n"
                  f"Conversation so far (the person chose the {case['style']} style):\n\n{convo}\n\n"
                  f"REFERENCE REPLY:\n{case['reference']}\n\nCANDIDATE REPLY:\n{got['text']}\n\n"
                  f"Score the candidate 1-5 on each criterion. Judge quality, not similarity of wording. "
                  f"Length alone is neither good nor bad.\n{rubric}")
        schema = Score
    else:
        prompt = (f"Conversation so far:\n\n{convo}\n\nREPLY:\n{got['text']}\n\nRule: {case['checks']['judge']}\n"
                  f"Does the reply pass the rule?")
        schema = RuleVerdict
    body = {"model": JUDGE_MODEL, "reasoning": {"effort": "low"},
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "verdict", "strict": True, "schema": to_strict_json_schema(schema)}}}
    raw, _ = await post(http, settings, body)
    return json.loads(raw["choices"][0]["message"]["content"])


def rule_checks(case, got) -> list[str]:
    """What code can check from the reply's fields; empty when it passes."""
    failed, checks = [], case["checks"]
    if "action" in checks and got.get("action") != checks["action"]:
        failed.append(f"action {got.get('action')} != {checks['action']}")
    if "action_not" in checks and got.get("action") == checks["action_not"]:
        failed.append(f"action was {checks['action_not']}")
    if "stage_in" in checks and got.get("stage") not in checks["stage_in"]:
        failed.append(f"stage {got.get('stage')} not in {checks['stage_in']}")
    if "safety" in checks and (got.get("safety") or {}).get("level") != checks["safety"]:
        failed.append(f"safety {(got.get('safety') or {}).get('level')} != {checks['safety']}")
    return failed


async def run_variant(http, settings, system, v, cases, samples, gate) -> list[dict]:
    async def one(case, n):
        async with gate:
            got = await reply(http, settings, v, system, case)
            if got.get("error"):
                return {"case": case["id"], "sample": n, "got": got, "verdict": None, "code_fails": ["call failed"]}
            verdict = await judge(http, settings, case, got)
            fails = rule_checks(case, got) if case["reference"] is None else []
            return {"case": case["id"], "sample": n, "got": got, "verdict": verdict, "code_fails": fails}
    return await asyncio.gather(*(one(c, n) for c in cases for n in range(samples)))


def summarise(name, rows) -> list[str]:
    quality = [r for r in rows if r["verdict"] and "overall" in r["verdict"]]
    rules = [r for r in rows if r["case"].startswith("rule-")]
    lines = [f"## {name}", ""]
    if quality:
        lines.append("| " + " | ".join(CRITERIA) + " |")
        lines.append("|" + "---|" * len(CRITERIA))
        lines.append("| " + " | ".join(f"{statistics.mean(r['verdict'][k] for r in quality):.2f}" for k in CRITERIA) + " |")
    passed = sum(1 for r in rules if r["verdict"] and r["verdict"].get("passed") and not r["code_fails"])
    secs = [r["got"]["seconds"] for r in rows if r["got"].get("seconds")]
    costs = [r["got"]["cost"] for r in rows if r["got"].get("cost")]
    failed_calls = sum(1 for r in rows if r["got"].get("error"))
    lines += ["", f"Rules passed: {passed}/{len(rules)}. Failed calls: {failed_calls}/{len(rows)}.",
              f"Seconds: median {statistics.median(secs):.1f}, slowest {max(secs):.1f}." if secs else "",
              f"Cost per reply (OpenRouter's figure): mean ${statistics.mean(costs):.5f}." if costs else "", ""]
    for r in rules:
        if not (r["verdict"] and r["verdict"].get("passed")) or r["code_fails"]:
            lines.append(f"- FAILED {r['case']} #{r['sample']}: {'; '.join(r['code_fails'])} {(r['verdict'] or {}).get('why', '')}")
    return lines


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", action="append", type=variant,
                        help="a model to run; without one, the prompt file's own model, effort and hosts")
    parser.add_argument("--prompt", type=pathlib.Path, default=PROMPTS_DIR / "mani.md")
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--label", default="run")
    args = parser.parse_args()
    cases = json.loads((HERE / "cases.json").read_text())
    every = cases["quality"] + cases["rules"]
    await pool.open_pool()
    try:
        config = await cache.load()
    finally:
        await pool.close_pool()
    settings = get_settings()
    prompt = parse_prompt(args.prompt)
    system = prompt["content"] + "\n\n" + framework_guide(config.registry)
    if not args.variant:
        args.variant = [{"name": "current", "model": prompt["model_id"],
                         "effort": prompt["model_parameters"].get("reasoning_effort"),
                         "hosts": prompt["routing"].get("only") or []}]
    gate = asyncio.Semaphore(12)
    out_dir = HERE / "results" / f"{dt.datetime.now():%Y%m%d-%H%M}-{args.label}"
    out_dir.mkdir(parents=True, exist_ok=True)
    report = [f"# Eval {args.label}", "", f"Prompt: `{args.prompt}`. Samples per case: {args.samples}. "
              f"Judge: `{JUDGE_MODEL}`.", ""]
    async with httpx.AsyncClient() as http:
        results = await asyncio.gather(*(run_variant(http, settings, system, v, every, args.samples, gate)
                                         for v in args.variant))
    for v, rows in zip(args.variant, results):
        report += summarise(f"{v['name']} (`{v['model']}`, effort {v['effort']})", rows)
        (out_dir / f"{v['name']}.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False))
        side = [f"# {v['name']}", ""]
        for r in rows:
            side += [f"## {r['case']} #{r['sample']}", "", r["got"].get("text") or r["got"].get("error", ""), "",
                     f"_verdict: {json.dumps(r['verdict'], ensure_ascii=False)}_", ""]
        (out_dir / f"{v['name']}-replies.md").write_text("\n".join(side))
    (out_dir / "report.md").write_text("\n".join(report))
    print("\n".join(report))
    print(f"\nWritten to {out_dir}")


asyncio.run(main())
