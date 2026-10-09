# ABOUTME: Runs scripted conversations through the real stack and scores every reply.
# ABOUTME: The validators already encode the specification; this points them at live output.

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import pathlib
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from mani import memory  # noqa: E402
from mani.auth.jwt import Claims  # noqa: E402
from mani.chat import orchestrator  # noqa: E402
from mani.config import get_settings  # noqa: E402
from mani.db import pool, profiles, threads  # noqa: E402
from mani.llm import chain  # noqa: E402
from mani.models.rows import SupportStyle, TechniqueOutcome  # noqa: E402
from mani.prompts import cache as prompt_cache, calls, composer  # noqa: E402
from scripts import baseline  # noqa: E402
from scripts.seed import (  # noqa: E402
    FRAMEWORKS_DIR,
    load_replies,
    load_tuning,
    parse_framework,
)
from tests.evals import validators  # noqa: E402

SCENARIOS = pathlib.Path(__file__).with_name("eval_conversations.yaml")

# What each framework is called, read from the content so the check never lists them itself.
FRAMEWORK_NAMES = [parse_framework(p)["name"] for p in sorted(FRAMEWORKS_DIR.glob("*.md"))]

# Every eval user is created fresh under this domain, so none of them carries another run's
# threads or memory, and they can be found and removed afterwards.
EVAL_EMAIL_DOMAIN = "eval.mani.local"
EVAL_NICKNAME = "Sam"

# How many times --baseline plays the tagged set, unless --runs says otherwise. One run is
# noise: the same prompt has given 3 findings and then 7.
DEFAULT_BASELINE_RUNS = 3


def _claims_for(user_id: str) -> Claims:
    """Claims carries the verified token's `sub`; `user_id` is a read-only property on it."""
    return Claims(sub=user_id, raw={"sub": user_id, "role": "authenticated"})


@dataclass(frozen=True)
class Exchange:
    """One turn, plus what the production guards logged about it.

    `guard_notes` is read from the same `logger.info` call orchestrator.py already makes
    after `guards.check()` - captured, not recomputed, so this is what production actually
    did on this turn, not a second opinion on it. It is the one measure of how often the
    model slips on structure.
    """

    message: str
    reply: str
    guard_notes: list[str] = field(default_factory=list)
    offered: bool = False
    buttons: list[str] = field(default_factory=list)
    # The framework row after this turn, as the database holds it: (id, outcome, phase).
    framework: tuple[str, str, str | None] | None = None
    chat: int = 1
    finding: str | None = None
    # Where the line sits in the scenario's script (from 1), the line as written, and what was
    # sent for it: `typed`, `tap`, `accept` (the offer button) or `fallback` (no offer to tap).
    line: int = 0
    token: str = ""
    kind: str = "typed"
    # Measured runs only: the admin.llm_calls rows this turn wrote, and the wall time of send.
    cost_rows: list[dict] = field(default_factory=list)
    turn_latency_ms: int = 0


class TurnFailed(Exception):
    """A script line whose turn raised. The run stops there rather than go on half measured."""

    def __init__(self, line: int) -> None:
        super().__init__(f"line {line}")
        self.line = line


class _GuardNoteCapture(logging.Handler):
    """Collects the guard notes orchestrator.py already logs. Changes nothing it does."""

    def __init__(self) -> None:
        super().__init__(level=logging.INFO)
        self.notes: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        if record.name == "mani.chat.orchestrator" and record.getMessage().startswith(
            "checked reply"
        ):
            self.notes.append(record.getMessage())


async def _fresh_user(scenario: str, style: SupportStyle) -> str:
    """A new person for one scenario in one style: no threads, no memory, a nickname.

    Scenarios used to share one user, and "New chat" reuses an empty thread, so scenarios
    started together ran in the same conversation - and every prompt carried that user's
    folded memory. One person per run is the only way the transcript is the scenario's own.
    """
    user_id = str(uuid.uuid4())
    run = f"{int(time.time())}-{os.getpid()}"
    async with pool.as_admin() as conn:
        await conn.execute(
            "insert into auth.users (id, email) values ($1, $2)",
            user_id, f"{scenario}.{style.value}.{run}@{EVAL_EMAIL_DOMAIN}",
        )
    claims = _claims_for(user_id)
    async with pool.as_user(claims) as conn:
        await profiles.upsert(conn, user_id, nickname=EVAL_NICKNAME)
    return user_id


async def _remove_users(user_ids: list[str]) -> None:
    """Take out what this run created. The cost rows go first: deleting a user only blanks
    `user_id` on them, which leaves synthetic rows that skew every cost and cache average."""
    if not user_ids:
        return
    async with pool.as_admin() as conn:
        # Read before they go: the run's own cost, latency and failure rate, which is what a
        # prompt change is compared on alongside the findings.
        cost = await conn.fetch(
            "select purpose, outcome, count(*) calls, round(avg(input_tokens)) avg_in, "
            "round(avg(output_tokens)) avg_out, max(output_tokens) max_out, "
            "round(avg(latency_ms) / 1000.0, 1) avg_s, round(max(latency_ms) / 1000.0, 1) max_s, "
            "round(100.0 * sum(cached_input_tokens) / nullif(sum(input_tokens), 0)) pct_cached "
            "from admin.llm_calls where user_id = any($1::uuid[]) group by 1, 2 order by 1, 2",
            user_ids,
        )
        print("\npurpose         outcome          calls  avg in  avg out  max out  avg s  max s  cached")
        for r in cost:
            print(
                f"{r['purpose']:<15} {r['outcome']:<15} {r['calls']:>6} {r['avg_in']:>7} "
                f"{r['avg_out']:>8} {r['max_out']:>8} {r['avg_s']:>6} {r['max_s']:>6} "
                f"{r['pct_cached'] or 0:>6}%"
            )
        await conn.execute("delete from admin.llm_calls where user_id = any($1::uuid[])", user_ids)
        await conn.execute("delete from auth.users where id = any($1::uuid[])", user_ids)


async def _new_cost_rows(thread_id, seen: set) -> list[dict]:
    """The thread's cost rows not seen yet, in the order they were written, now marked seen.

    Each scenario has its own user and thread, and every row a turn makes is committed before
    orchestrator.send returns, so what is new after a turn is exactly that turn's calls.
    """
    async with pool.as_admin() as conn:
        rows = await conn.fetch(
            "select id, purpose::text, outcome::text, input_tokens, cached_input_tokens, "
            "output_tokens, reasoning_tokens, latency_ms from admin.llm_calls "
            "where thread_id = $1 and not (id = any($2::uuid[])) order by created_at, id",
            thread_id, list(seen),
        )
    seen.update(r["id"] for r in rows)
    return [dict(r) for r in rows]


async def _has_reasoning_column() -> bool:
    async with pool.as_admin() as conn:
        return await conn.fetchval(
            "select exists (select 1 from information_schema.columns where table_schema = "
            "'admin' and table_name = 'llm_calls' and column_name = 'reasoning_tokens')"
        )


async def _open_chat(claims: Claims, style: SupportStyle):
    """Greeting, then the style tap - the way every real conversation starts."""
    async with pool.as_user(claims) as conn:
        thread, _ = await orchestrator.start_thread(conn, claims)
    async with pool.as_user(claims) as conn:
        await orchestrator.send(conn, claims, thread.id, load_replies().style_labels[style.value])
    return thread


async def _framework_after(claims: Claims, thread_id) -> tuple[str, str, str | None] | None:
    async with pool.as_user(claims) as conn:
        ctx = await threads.load_turn_context(
            conn, thread_id, claims.user_id, load_tuning().windows.style_window
        )
    technique = ctx.technique if ctx else None
    if technique is None:
        return None
    return technique.framework_id, technique.outcome.value, technique.phase


async def _run_one(
    user_id: str, style: SupportStyle, turns: list[str], start_in: dict | None = None,
    *, measure: bool = False,
) -> list[Exchange]:
    """One conversation in one style, following the script's tokens:

    - `@accept|<fallback>` taps the offer if the last reply made one; otherwise sends the
      fallback line and tries again at the next `@accept`. Once accepted, later ones are skipped.
    - `@tap:<label>` taps that button; if the last reply did not offer it, the label is sent
      anyway and the turn records the missing button.
    - `@newchat` folds what was said into memory, as starting a chat does in the app, and
      opens a second conversation in the same style.

    With `measure`, each turn also carries the cost rows it wrote and its wall time. The
    greeting and the style tap are not script lines, so their rows are never counted.
    """
    claims = _claims_for(user_id)
    exchanges: list[Exchange] = []

    capture = _GuardNoteCapture()
    orch_logger = logging.getLogger("mani.chat.orchestrator")
    orch_logger.addHandler(capture)
    previous_level = orch_logger.level
    orch_logger.setLevel(logging.INFO)

    thread = await _open_chat(claims, style)
    seen: set = set()
    if measure:
        await _new_cost_rows(thread.id, seen)
    chat = 1
    if start_in:
        # A scenario that tests the stages themselves starts with the framework already
        # accepted, rather than depending on the model offering it on a particular turn.
        async with pool.as_user(claims) as conn:
            await threads.set_technique_outcome(
                conn, thread.id, user_id, start_in["framework"], TechniqueOutcome.ACCEPTED,
                at_message_count=0, phase=start_in["phase"],
            )

    accepted = bool(start_in)
    last_prompts: list = []
    try:
        for line_number, line in enumerate(turns, 1):
            finding = None
            kind = "typed"
            if line == "@newchat":
                await memory.fold_finished(claims, keep=None)
                thread = await _open_chat(claims, style)
                if measure:
                    await _new_cost_rows(thread.id, seen)
                chat += 1
                last_prompts = []
                continue
            if line.startswith("@accept"):
                if accepted:
                    continue
                offer = next((p for p in last_prompts if p.technique), None)
                if offer is not None:
                    message, accepted, kind = offer.label, True, "accept"
                else:
                    message = line.partition("|")[2] or "Yes, I'd like some help with this."
                    kind = "fallback"
            elif line.startswith("@tap:"):
                message = line.removeprefix("@tap:")
                kind = "tap"
                if not any(p.label.lower() == message.lower() for p in last_prompts):
                    finding = f"no '{message}' button to tap"
            else:
                message = line

            capture.notes.clear()
            try:
                async with pool.as_user(claims) as conn:
                    started = time.perf_counter()
                    turn = await orchestrator.send(conn, claims, thread.id, message)
                    # Inside the block, so the commit when the connection closes is not counted.
                    turn_latency_ms = int((time.perf_counter() - started) * 1000)
            except Exception as exc:
                raise TurnFailed(line_number) from exc
            last_prompts = list(turn.prompts)
            exchanges.append(
                Exchange(
                    message=message, reply=turn.content, guard_notes=list(capture.notes),
                    offered=any(p.technique for p in turn.prompts),
                    buttons=[p.label for p in turn.prompts],
                    framework=await _framework_after(claims, thread.id),
                    chat=chat, finding=finding, line=line_number, token=line, kind=kind,
                    cost_rows=await _new_cost_rows(thread.id, seen) if measure else [],
                    turn_latency_ms=turn_latency_ms,
                )
            )
    finally:
        orch_logger.removeHandler(capture)
        orch_logger.setLevel(previous_level)

    return exchanges


def _score(exchanges: list[Exchange], style: SupportStyle, scenario: dict) -> list[validators.Finding]:
    """Every check that applies to this scenario.

    `heard`: someone asking only to be heard, where a reply with no question is right.
    `expect_framework`: a journey, which must reach a framework and hand off at its end.
    `markers`: words only the first chat used, which the second must not bring across.
    """
    findings: list[validators.Finding] = []
    for index, exchange in enumerate(exchanges):
        # Everything said so far in this chat.
        said = " ".join(e.message for e in exchanges[: index + 1] if e.chat == exchange.chat)
        # An offer and the reply to Tell me more are the seeded words, not the model's, and both
        # carry the offer's technique button: the framework's name in them is meant.
        if not exchange.offered:
            findings += validators.check(exchange.reply, said)
            findings += validators.says_framework(exchange.reply, FRAMEWORK_NAMES)
        findings += validators.style_findings(exchange.reply, style.value)
        if exchange.finding:
            findings.append(validators.Finding("script", exchange.finding))
        if exchange.chat > 1 and scenario.get("markers"):
            findings += validators.references_other_chat(exchange.reply, scenario["markers"], said)
    for chat in sorted({e.chat for e in exchanges}):
        in_chat = [e for e in exchanges if e.chat == chat]
        findings += validators.repeated_openers([e.reply for e in in_chat])
        findings += validators.repeated_question([e.reply for e in in_chat])
        if not scenario.get("heard"):
            findings += validators.unasked_before_offer([(e.reply, e.offered) for e in in_chat])
    for index, exchange in enumerate(exchanges):
        state = exchange.framework
        if state and state[1] == "accepted" and state[2] not in (None, "offering", "closing") \
                and not str(state[2]).startswith("somatic"):
            said = " ".join(e.message for e in exchanges[: index + 1] if e.chat == exchange.chat)
            findings += validators.names_their_situation(exchange.reply, said)
            findings += validators.asks_to_confirm(exchange.reply)
    phases = [(e.framework[2] if e.framework and e.framework[1] == "accepted" else None, e.buttons)
              for e in exchanges]
    findings += validators.missing_handoff(phases, [e.message for e in exchanges])
    if scenario.get("expect_after_questions"):
        tapped = next((i for i, e in enumerate(exchanges) if e.message.lower() == "chat more"), None)
        if tapped is not None:
            findings += validators.after_framework_questions_asked(
                # From the reply to Chat More itself, which asks the first of the three.
                [e.reply for e in exchanges[tapped:]], load_replies().after_framework_questions
            )
    if scenario.get("expect_framework"):
        reached = [e.framework[2] for e in exchanges if e.framework and e.framework[1] == "accepted"]
        if not reached:
            findings.append(validators.Finding("journey", "never entered a framework"))
        elif not any(str(phase).startswith("somatic") for phase in reached):
            findings.append(validators.Finding("journey", f"stopped at {reached[-1]}, never reached somatic"))
    return findings


def _first_offer(exchanges: list[Exchange]) -> str | None:
    """Which of their messages the first offer answered, counting the style tap out, and
    which framework it offered."""
    found = next(
        ((i, e) for i, e in enumerate(exchanges, 1) if e.offered and e.chat == 1), None
    )
    if found is None:
        return None
    index, exchange = found
    return f"{index}:{exchange.framework[0] if exchange.framework else '?'}"


def _print_scenario(title: str, exchanges: list[Exchange], findings: list, verbose: bool) -> None:
    print(f"\n=== {title} ===")
    if verbose:
        for exchange in exchanges:
            print(f"  > {exchange.message}\n  < {exchange.reply}")
            state = exchange.framework
            print(f"    [chat {exchange.chat} | framework {state[0]} {state[1]} {state[2]}]"
                  if state else f"    [chat {exchange.chat} | no framework]")
            if exchange.buttons:
                print(f"    [buttons] {exchange.buttons}")
            if exchange.offered:
                print("    [offered a framework]")
            if exchange.guard_notes:
                print(f"    [guard] {'; '.join(exchange.guard_notes)}")
            print()
    for finding in findings:
        print(f"  FAIL {finding}")
    if not findings:
        print("  clean")


def _print_styles(by_style: dict[str, list[str]], offers: dict[str, list[str | None]]) -> None:
    print("\nstyle         replies  avg chars  asks a question  opens with I  first offer at message")
    for name, replies in by_style.items():
        n = len(replies) or 1
        chars = sum(len(r) for r in replies) / n
        asks = 100 * sum("?" in r for r in replies) / n
        own = 100 * sum(r.lstrip().lower().startswith(("i ", "i'", "i\u2019")) for r in replies) / n
        print(f"{name:<13} {len(replies):>7}  {chars:>9.0f}  {asks:>14.0f}%  {own:>11.0f}%  {offers[name]}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", help="run every scenario as this existing user instead of a fresh one each")
    parser.add_argument("--verbose", action="store_true", help="print every reply")
    parser.add_argument("--scenario", help="run only the scenario with this name")
    parser.add_argument(
        "--style", choices=[s.value for s in SupportStyle],
        help="play each scenario in this style only, rather than all three",
    )
    parser.add_argument(
        "--baseline", action="store_true",
        help="measure what each turn costs in the scenarios tagged `baseline: true`, Supportive "
             "only, and save it to scripts/baselines/ (local database only)",
    )
    parser.add_argument(
        "--runs", type=int, help=f"how many times --baseline plays the set (default {DEFAULT_BASELINE_RUNS})"
    )
    parser.add_argument("--label", help="names the --baseline file: letters, digits, - and _")
    args = parser.parse_args()

    if not args.baseline:
        if args.runs is not None or args.label is not None:
            parser.error("--runs and --label only apply with --baseline")
        return args
    if args.scenario or args.user or args.style:
        parser.error("--scenario, --user and --style cannot be used with --baseline: every "
                     "baseline runs the same set with fresh users, in Supportive")
    if args.label is None:
        parser.error("--baseline needs --label")
    if not baseline.LABEL.fullmatch(args.label):
        parser.error("--label takes letters, digits, - and _ only")
    if args.runs is not None and args.runs < 1:
        parser.error("--runs must be at least 1")
    return args


async def main() -> int:
    args = _parse_args()
    scenarios = yaml.safe_load(SCENARIOS.read_text())
    if args.baseline:
        return await _measure(args, [s for s in scenarios if s.get("baseline")])

    if args.scenario:
        scenarios = [s for s in scenarios if s["name"] == args.scenario]
    failures = 0
    # Every reply per style, for the separation table at the end: the styles are meant to
    # behave differently, and nothing else in the run would show that they do not.
    by_style: dict[str, list[str]] = {}
    offers: dict[str, list[str | None]] = {}

    # pool.as_user() needs the pool open; nothing here runs under FastAPI's lifespan.
    await pool.open_pool()

    created: list[str] = []
    try:
        for style in [SupportStyle(args.style)] if args.style else SupportStyle:
            for scenario in scenarios:
                user_id = args.user or await _fresh_user(scenario["name"], style)
                if not args.user:
                    created.append(user_id)
                try:
                    exchanges = await _run_one(user_id, style, scenario["turns"], scenario.get("start_in"))
                except TurnFailed as failed:
                    print(f"\nstopped: {scenario['name']} / {style.value}, {failed} raised: "
                          f"{failed.__cause__!r}", file=sys.stderr)
                    return 1
                findings = _score(exchanges, style, scenario)
                by_style.setdefault(style.value, []).extend(e.reply for e in exchanges)
                offers.setdefault(style.value, []).append(_first_offer(exchanges))
                failures += len(findings)
                _print_scenario(f"{scenario['name']} / {style.value}", exchanges, findings, args.verbose)
    finally:
        # Also when a turn raised or the run was interrupted, so no synthetic user or cost
        # row is left behind to skew the averages.
        await _remove_users(created)
        await pool.close_pool()

    _print_styles(by_style, offers)
    print(f"\ntotal findings: {failures}")
    return 1 if failures else 0


async def _measure(args: argparse.Namespace, scenarios: list[dict]) -> int:
    """--baseline: the tagged scenarios in Supportive, the whole set once per run, every
    turn's cost kept and saved. Findings are reported beside the cost, never as the exit code."""
    settings = get_settings()
    if not baseline.is_local(settings.database_url):
        print("a baseline runs against a local database only, and DATABASE_URL names another "
              "host; nothing was run", file=sys.stderr)
        return 1
    started_at = datetime.now(UTC)
    path = baseline.BASELINES_DIR / f"{started_at:%Y-%m-%d}-{args.label}.json"
    if path.exists():
        print(f"{path} already exists; choose another --label. Nothing was run.", file=sys.stderr)
        return 1
    runs = args.runs if args.runs is not None else DEFAULT_BASELINE_RUNS
    style = SupportStyle.SUPPORTIVE

    await pool.open_pool()
    created: list[str] = []
    results: list[dict] = []
    replies: list[str] = []
    offers: list[str | None] = []
    failures = 0
    where = "the start"
    try:
        if not await _has_reasoning_column():
            print("admin.llm_calls.reasoning_tokens does not exist; apply migration 018 first. "
                  "Nothing was run.", file=sys.stderr)
            return 1
        config = await prompt_cache.load()
        model, _, _ = composer.model_settings(config)
        exercise_row = config.require("exercise_select")
        efforts = {
            "chat": chain.effective_effort(
                model, calls.effort_for(config.require("mani_base"), "mani_base")
            ),
            "exercise_select": chain.effective_effort(
                exercise_row.model_id or settings.default_chat_model,
                calls.effort_for(exercise_row, "exercise_select"),
            ),
        }
        content = baseline.content_hashes(config)

        for run in range(1, runs + 1):
            for scenario in scenarios:
                where = f"{scenario['name']}, run {run}"
                user_id = await _fresh_user(scenario["name"], style)
                created.append(user_id)
                exchanges = await _run_one(
                    user_id, style, scenario["turns"], scenario.get("start_in"), measure=True
                )
                # Every chat turn makes at least one call, so a turn with no row means the
                # rows were lost, and counting it as zero would make the run look cheaper.
                silent = next((e for e in exchanges if not e.cost_rows), None)
                if silent is not None:
                    print(f"\nstopped: {where}, line {silent.line} wrote no cost row; no baseline "
                          "written", file=sys.stderr)
                    return 1
                findings = _score(exchanges, style, scenario)
                failures += len(findings)
                replies.extend(e.reply for e in exchanges)
                offers.append(_first_offer(exchanges))
                results.append(baseline.scenario_result(
                    run=run, scenario=scenario["name"], findings=len(findings),
                    turns=[
                        baseline.turn_row(
                            line=e.line, token=e.token, kind=e.kind, rows=e.cost_rows,
                            turn_latency_ms=e.turn_latency_ms,
                        )
                        for e in exchanges
                    ],
                ))
                _print_scenario(f"{scenario['name']} / {style.value} / run {run}", exchanges,
                                findings, args.verbose)
    except TurnFailed as failed:
        print(f"\nstopped: {where}, {failed} raised: {failed.__cause__!r}; no baseline written",
              file=sys.stderr)
        return 1
    except asyncio.CancelledError:
        print(f"\ninterrupted during {where}; no baseline written", file=sys.stderr)
        raise
    finally:
        await _remove_users(created)
        await pool.close_pool()

    reported = baseline.reasoning_reported(efforts, results)
    if not reported:
        print("\nwarning: the calls were asked to think but no call reported any reasoning tokens; "
              "the count is being lost somewhere", file=sys.stderr)
    document = {
        "label": args.label,
        "created_at": started_at.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "git": baseline.git_state(),
        "model": model,
        "reasoning_effort": efforts,
        "reasoning_reported": reported,
        "content": content,
        "scripts": baseline.digest([{"name": s["name"], "turns": s["turns"]} for s in scenarios]),
        "database_host": baseline.database_host(settings.database_url),
        "style": style.value,
        "runs": runs,
        "scenarios": [s["name"] for s in scenarios],
        "results": results,
        **baseline.summarize(results),
    }
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + "\n")

    _print_styles({style.value: replies}, {style.value: offers})
    print(f"\ntotal findings: {failures}")
    print(f"baseline written to {path.relative_to(baseline.REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        # The users were already removed on the way out; this only sets the exit code.
        sys.exit(1)
