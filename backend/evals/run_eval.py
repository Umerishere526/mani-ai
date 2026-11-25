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

from evals import reply_rules  # noqa: E402
from mani.chat import crisis, questions, repairs  # noqa: E402
from mani.chat.enforce import banned_phrases, forbidden_words  # noqa: E402
from mani.chat.facts import NO_OFFER, facts_block, framework_guide  # noqa: E402
from mani.chat.greeting import style_label  # noqa: E402
from mani.chat.reply import shaped  # noqa: E402
from mani.config import get_settings  # noqa: E402
from mani.llm import chain, client  # noqa: E402
from mani.db import pool  # noqa: E402
from mani.prompts import cache  # noqa: E402
from scripts.seed import PROMPTS_DIR, parse_prompt  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
JUDGE_MODEL = "openai/gpt-6.1-sol"
CRITERIA = {
    "understanding": "Shows it understood what is really at stake for them, and adds something they did not say.",
    "no_assumptions": "Invites their story before concluding; never assumes a cause, a feeling or that there is no reason.",
    "ideas": "Gives ideas to explore: a fair perspective, a distinction, something highlighted, permission, both feelings.",
    "question": ("Asks a question only when it helps, and never more than one: open, or options each with a reason. "
                 "Not a thin either-or, not a fact-check. A reply that rightly asks nothing is not marked down."),
    "voice": "Warm, plain everyday words, no therapy talk, no lecture, no advice they did not ask for, no emojis.",
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
    only = [h for h in (hosts or "").split("|") if h]
    return {"name": name, "model": model, "effort": effort or None, "parameters": {},
            "routing": {"only": only, "zdr": True} if only else None}


# OpenRouter holds each running request's estimated cost against a low balance and refuses new ones while the holds
# are full (402, in_flight_budget_exhausted); the refusal is temporary and says how long to wait.
IN_FLIGHT_WAITS = 6


async def post(http, settings, body) -> tuple[dict, float]:
    began = time.monotonic()
    attempt = waits = 0
    while True:
        try:
            r = await http.post(f"{settings.openrouter_base_url}/chat/completions", json=body, timeout=180,
                                headers={"Authorization": f"Bearer {settings.openrouter_api_key}"})
        except httpx.TransportError as error:
            # A dropped connection is retried like a failed answer, never allowed to end the run.
            attempt += 1
            if attempt == 3:
                raise RuntimeError(f"{body['model']}: {type(error).__name__}") from error
            await asyncio.sleep(2 * attempt)
            continue
        if r.status_code == 200 and r.json().get("choices"):
            return r.json(), time.monotonic() - began
        if r.status_code == 402 and "in_flight" in r.text and waits < IN_FLIGHT_WAITS:
            waits += 1
            await asyncio.sleep(float(r.headers.get("retry-after") or 5))
            continue
        attempt += 1
        if attempt == 3:
            raise RuntimeError(f"{body['model']}: {r.status_code} {r.text[:300]}")
        await asyncio.sleep(2 * attempt)


def reply_schema(case, offers: tuple[str, ...]) -> type:
    """The reply's schema as the turn chooses it from the case's facts: no offer when they say none may be made,
    otherwise the active sets (`offers`) they name no decline of."""
    if NO_OFFER in case["facts"]:
        return shaped(())
    declined = " ".join(fact for fact in case["facts"] if fact.startswith("They declined"))
    return shaped(tuple(framework_id for framework_id in offers if framework_id not in declined))


async def reply(http, settings, v, system, case, offers: tuple[str, ...]) -> dict:
    """One reply, sent as the turn sends it: the same request fields and reply schema beside the messages
    (chain.request_body, chain.sampling and reply_schema), and the facts in the turn's own format."""
    facts = facts_block([f"Their style: {style_label(case['style'])}.", *case["facts"]])
    parameters = v["parameters"]
    body = {"model": v["model"], "messages": [{"role": "system", "content": system},
                                              {"role": "assistant", "content": case["opener"]}]
            + turns(case, settings) + [{"role": "system", "content": facts}],
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "reply", "strict": True, "schema": to_strict_json_schema(reply_schema(case, offers))}},
            **chain.sampling(v["model"], parameters.get("temperature", client.DEFAULT_TEMPERATURE),
                             parameters.get("maxTokens", client.DEFAULT_MAX_TOKENS)),
            **chain.request_body(v["model"], settings, v["routing"], v["effort"])}
    try:
        raw, took = await post(http, settings, body)
        out = json.loads(raw["choices"][0]["message"]["content"])
        sent, cut = received(case, out)
        return {**out, "sent": sent, "question_cut": cut, "seconds": round(took, 1),
                "cost": (raw.get("usage") or {}).get("cost")}
    except Exception as error:  # noqa: BLE001
        return {"error": str(error)[:300], "text": "", "sent": "", "seconds": None, "cost": None}


# The lines code writes in a conversation, which a case names by `fixed` in its turns so that what it shows is what the
# person was sent under the settings in force.
FIXED = {
    "pause": lambda turn, settings: crisis.pause_reply(turn.get("about"), settings.crisis_pause_seconds),
    "return_check": lambda turn, settings: crisis.return_check_reply(turn.get("about")),
}


def turns(case, settings) -> list[dict]:
    """The case's conversation, with each line code writes in its words under these settings."""
    return [{"role": turn["role"], "content": FIXED[turn["fixed"]](turn, settings)} if "fixed" in turn else turn
            for turn in case["turns"]]


# How the facts say a safety worry is open (facts.facts), which holds the turn.
SAFETY_WORRY_OPEN = "A safety worry is open in this conversation"


def received(case, got) -> tuple[str, str | None]:
    """The reply's words as the person would receive them, through the turn's own repairs, and why a question was cut.
    A case whose facts put a set, an offer or a safety worry in play says `open_chat` false. A safety worry open in its
    facts guards the turn, and so does this reply's own safety judgment, as it would out of a clear conversation."""
    guarded = (any(fact.startswith(SAFETY_WORRY_OPEN) for fact in case.get("facts", []))
               or (got.get("safety") or {}).get("level", "none") != "none")
    open_chat = case.get("open_chat", True) and questions.in_open_chat(
        in_play=False, guarded=guarded, action=got.get("action", "none"))
    question = got.get("question") or {}
    sent, _asked, cut = repairs.sent_text(got.get("text") or "", question.get("ask", ""), guarded=guarded,
                                          open_chat=open_chat, latest=question.get("latest", ""))
    return sent, cut


async def judge(http, settings, case, got) -> dict:
    convo = "\n\n".join(f"{t['role'].upper()}: {t['content']}" for t in turns(case, settings))
    rubric = "\n".join(f"- {k}: {v}" for k, v in CRITERIA.items())
    if case["reference"] is not None:
        prompt = (f"You are judging a reply from MANI, a supportive chat companion, against a reference reply.\n\n"
                  f"Conversation so far (the person chose the {case['style']} style):\n\n{convo}\n\n"
                  f"REFERENCE REPLY:\n{case['reference']}\n\nCANDIDATE REPLY:\n{got['sent']}\n\n"
                  f"Score the candidate 1-5 on each criterion. Judge quality, not similarity of wording. "
                  f"Length alone is neither good nor bad.{SHORT_BY_DESIGN if case['style'] == 'Directive' else ''}"
                  f"\n{rubric}")
        schema = Score
    else:
        prompt = (f"Conversation so far:\n\n{convo}\n\nREPLY:\n{got['sent']}\n\nRule: {case['checks']['judge']}\n"
                  f"Does the reply pass the rule?")
        schema = RuleVerdict
    return await structured(http, settings, JUDGE_MODEL, [{"role": "user", "content": prompt}], schema)


async def structured(http, settings, model: str, messages: list[dict], schema: type[BaseModel]) -> dict:
    """A call the evaluation makes for itself (the judge, the model-played person), straight to OpenRouter at effort
    low: never recorded as a chat call, and never on the chat's priority tier."""
    # A set output budget keeps OpenRouter's hold for the call small; a ten-criterion verdict with its quotes runs past
    # 2000 tokens (5 of 10 verdicts were cut off on 2026-11-25), so the budget is 8000.
    body = {"model": model, "reasoning": {"effort": "low"}, "max_tokens": 8000, "messages": messages,
            "response_format": {"type": "json_schema", "json_schema": {
                "name": schema.__name__.lower(), "strict": True, "schema": to_strict_json_schema(schema)}}}
    raw, _ = await post(http, settings, body)
    return json.loads(raw["choices"][0]["message"]["content"])


# Directive replies are short by design (muhammad, 2026-11-18), so a Directive case is judged with length set aside,
# and the 0.15 gate compares the other styles only.
SHORT_BY_DESIGN = (" In this style short replies are the aim: never count shortness, or fewer ideas than the "
                   "reference gives, against the candidate.")
GATED_STYLES = ("Supportive", "Reflective")


def rule_checks(case, got) -> list[str]:
    """What code can check from the reply's fields and the words the person receives; empty when it passes. The client's
    forbidden words and banned lines are checked on every rule case (approved by muhammad, 2026-11-24)."""
    failed, checks, text = [], case["checks"], got.get("sent") or ""
    failed += [f"used forbidden {word!r}" for word in forbidden_words(text)]
    failed += [f"said banned {line!r}" for line in banned_phrases(text)]
    if "max_questions" in checks and (count := len(reply_rules.questions(text))) > checks["max_questions"]:
        failed.append(f"{count} questions > {checks['max_questions']}")
    if checks.get("no_invented_pronoun"):
        said = " ".join(t.get("content", "") for t in case["turns"] if t["role"] == "user")
        failed += [f"said {g!r} before the person did"
                   for g in sorted(reply_rules.pronouns(text) - reply_rules.genders_named(said))]
    if "max_sentences" in checks and (count := len(questions.sentences(text))) > checks["max_sentences"]:
        failed.append(f"{count} sentences > {checks['max_sentences']}")
    words = len(text.split())
    if "max_words" in checks and words > checks["max_words"]:
        failed.append(f"{words} words > {checks['max_words']}")
    if "min_words" in checks and words < checks["min_words"]:
        failed.append(f"{words} words < {checks['min_words']}")
    if "action" in checks and got.get("action") != checks["action"]:
        failed.append(f"action {got.get('action')} != {checks['action']}")
    if "action_not" in checks and got.get("action") == checks["action_not"]:
        failed.append(f"action was {checks['action_not']}")
    if "stage_in" in checks and got.get("stage") not in checks["stage_in"]:
        failed.append(f"stage {got.get('stage')} not in {checks['stage_in']}")
    if "safety" in checks and (got.get("safety") or {}).get("level") != checks["safety"]:
        failed.append(f"safety {(got.get('safety') or {}).get('level')} != {checks['safety']}")
    for field in ("about", "still_there"):
        if field in checks and (got.get("safety") or {}).get(field) != checks[field]:
            failed.append(f"safety {field} {(got.get('safety') or {}).get(field)} != {checks[field]}")
    if "corrected" in checks and bool(got.get("corrected")) != checks["corrected"]:
        failed.append(f"corrected {got.get('corrected')} != {checks['corrected']}")
    for word in checks.get("text_excludes", []):
        if word.lower() in text.lower():
            failed.append(f"said {word!r}")
    return failed


async def run_variant(http, settings, system, v, cases, samples, gate, offers) -> list[dict]:
    async def one(case, n):
        async with gate:
            got = await reply(http, settings, v, system, case, offers)
            if got.get("error"):
                return {"case": case["id"], "style": case["style"], "sample": n, "got": got, "verdict": None,
                        "code_fails": ["call failed"]}
            try:
                verdict = await judge(http, settings, case, got)
            except RuntimeError as error:
                return {"case": case["id"], "style": case["style"], "sample": n, "got": got, "verdict": None,
                        "code_fails": [f"judge failed: {str(error)[:120]}"]}
            fails = rule_checks(case, got) if case["reference"] is None else []
            return {"case": case["id"], "style": case["style"], "sample": n, "got": got, "verdict": verdict,
                    "code_fails": fails}
    return await asyncio.gather(*(one(c, n) for c in cases for n in range(c.get("samples", samples))))


def summarise(name, rows) -> list[str]:
    quality = [r for r in rows if r["verdict"] and "overall" in r["verdict"]]
    rules = [r for r in rows if r["case"].startswith("rule-")]
    lines = [f"## {name}", ""]
    if quality:
        lines.append("| " + " | ".join(CRITERIA) + " |")
        lines.append("|" + "---|" * len(CRITERIA))
        lines.append("| " + " | ".join(f"{statistics.mean(r['verdict'][k] for r in quality):.2f}" for k in CRITERIA) + " |")
        style_of = {r["case"]: r["style"] for r in rows if "style" in r}
        by_style = {style: [r["verdict"]["overall"] for r in quality if style_of.get(r["case"]) == style]
                    for style in ("Directive", *GATED_STYLES)}
        lines.append("Overall by style: " + ", ".join(f"{style} {statistics.mean(v):.2f}" for style, v in by_style.items() if v))
        gated = [x for style in GATED_STYLES for x in by_style[style]]
        if gated:
            lines.append(f"Gate (Supportive and Reflective overall): {statistics.mean(gated):.2f}")
    passed = sum(1 for r in rules if r["verdict"] and r["verdict"].get("passed") and not r["code_fails"])
    secs = [r["got"]["seconds"] for r in rows if r["got"].get("seconds")]
    costs = [r["got"]["cost"] for r in rows if r["got"].get("cost")]
    failed_calls = sum(1 for r in rows if r["got"].get("error"))
    unjudged = sum(1 for r in rows if any(f.startswith("judge failed") for f in r["code_fails"]))
    lines += ["", f"Rules passed: {passed}/{len(rules)}. Failed calls: {failed_calls}/{len(rows)}. "
                  f"Unjudged: {unjudged}/{len(rows)}.",
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
                         "parameters": prompt["model_parameters"], "routing": prompt["routing"] or None}]
    # Four at a time: more can fill OpenRouter's in-flight budget on a low balance.
    gate = asyncio.Semaphore(4)
    out_dir = HERE / "results" / f"{dt.datetime.now():%Y%m%d-%H%M}-{args.label}"
    out_dir.mkdir(parents=True, exist_ok=True)
    report = [f"# Eval {args.label}", "", f"Prompt: `{args.prompt}`. Samples per case: {args.samples}. "
              f"Judge: `{JUDGE_MODEL}`.", ""]
    async with httpx.AsyncClient() as http:
        results = await asyncio.gather(*(run_variant(http, settings, system, v, every, args.samples, gate,
                                                     tuple(config.registry.ids))
                                         for v in args.variant))
    for v, rows in zip(args.variant, results):
        report += summarise(f"{v['name']} (`{v['model']}`, effort {v['effort']})", rows)
        (out_dir / f"{v['name']}.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False))
        side = [f"# {v['name']}", ""]
        for r in rows:
            side += [f"## {r['case']} #{r['sample']}", "", r["got"].get("sent") or r["got"].get("error", ""), "",
                     f"_verdict: {json.dumps(r['verdict'], ensure_ascii=False)}_", ""]
        (out_dir / f"{v['name']}-replies.md").write_text("\n".join(side))
    (out_dir / "report.md").write_text("\n".join(report))
    print("\n".join(report))
    print(f"\nWritten to {out_dir}")


if __name__ == "__main__":
    asyncio.run(main())
