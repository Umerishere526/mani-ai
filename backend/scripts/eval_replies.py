# ABOUTME: Runs scripted conversations through the real stack and scores every reply.
# ABOUTME: The validators already encode the specification; this points them at live output.

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import pathlib
import sys
import time
import uuid
from dataclasses import dataclass, field

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from mani import memory  # noqa: E402
from mani.chat.greeting import AFTER_FRAMEWORK_QUESTIONS  # noqa: E402
from mani.auth.jwt import Claims  # noqa: E402
from mani.chat import orchestrator  # noqa: E402
from mani.db import pool, profiles, threads  # noqa: E402
from mani.models.rows import SupportStyle, TechniqueOutcome  # noqa: E402
from scripts.seed import FRAMEWORKS_DIR, parse_framework  # noqa: E402
from tests.evals import validators  # noqa: E402

SCENARIOS = pathlib.Path(__file__).with_name("eval_conversations.yaml")

# What each framework is called, read from the content so the check never lists them itself.
FRAMEWORK_NAMES = [parse_framework(p)["name"] for p in sorted(FRAMEWORKS_DIR.glob("*.md"))]

# Every eval user is created fresh under this domain, so none of them carries another run's
# threads or memory, and they can be found and removed afterwards.
EVAL_EMAIL_DOMAIN = "eval.mani.local"
EVAL_NICKNAME = "Sam"


def _claims_for(user_id: str) -> Claims:
    """Claims carries the verified token's `sub`; `user_id` is a read-only property on it."""
    return Claims(sub=user_id, raw={"sub": user_id, "role": "authenticated"})


@dataclass(frozen=True)
class Exchange:
    """One turn, plus what the production repair pipeline logged about it.

    `repair_notes` is read from the same `logger.info` call orchestrator.py already makes
    after `repairs.apply()` - captured, not recomputed, so this is what production actually
    did on this turn, not a second opinion on it.
    """

    message: str
    reply: str
    repair_notes: list[str] = field(default_factory=list)
    offered: bool = False
    buttons: list[str] = field(default_factory=list)
    # The framework row after this turn, as the database holds it: (id, outcome, phase).
    framework: tuple[str, str, str | None] | None = None
    chat: int = 1
    finding: str | None = None


class _RepairNoteCapture(logging.Handler):
    """Collects the repair notes orchestrator.py already logs. Changes nothing it does."""

    def __init__(self) -> None:
        super().__init__(level=logging.INFO)
        self.notes: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        if record.name == "mani.chat.orchestrator" and record.getMessage().startswith(
            "repaired reply"
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


async def _open_chat(claims: Claims, style: SupportStyle):
    """Greeting, then the style tap - the way every real conversation starts."""
    async with pool.as_user(claims) as conn:
        thread, _ = await orchestrator.start_thread(conn, claims)
    async with pool.as_user(claims) as conn:
        await orchestrator.send(conn, claims, thread.id, style.value.capitalize())
    return thread


async def _framework_after(claims: Claims, thread_id) -> tuple[str, str, str | None] | None:
    async with pool.as_user(claims) as conn:
        ctx = await threads.load_turn_context(conn, thread_id, claims.user_id)
    technique = ctx.technique if ctx else None
    if technique is None:
        return None
    return technique.framework_id, technique.outcome.value, technique.phase


async def _run_one(
    user_id: str, style: SupportStyle, turns: list[str], start_in: dict | None = None
) -> list[Exchange]:
    """One conversation in one style, following the script's tokens:

    - `@accept|<fallback>` taps the offer if the last reply made one; otherwise sends the
      fallback line and tries again at the next `@accept`. Once accepted, later ones are skipped.
    - `@tap:<label>` taps that button; if the last reply did not offer it, the label is sent
      anyway and the turn records the missing button.
    - `@newchat` folds what was said into memory, as starting a chat does in the app, and
      opens a second conversation in the same style.
    """
    claims = _claims_for(user_id)
    exchanges: list[Exchange] = []

    capture = _RepairNoteCapture()
    orch_logger = logging.getLogger("mani.chat.orchestrator")
    orch_logger.addHandler(capture)
    previous_level = orch_logger.level
    orch_logger.setLevel(logging.INFO)

    thread = await _open_chat(claims, style)
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
        for line in turns:
            finding = None
            if line == "@newchat":
                await memory.fold_finished(claims, keep=None)
                thread = await _open_chat(claims, style)
                chat += 1
                last_prompts = []
                continue
            if line.startswith("@accept"):
                if accepted:
                    continue
                offer = next((p for p in last_prompts if p.technique), None)
                if offer is not None:
                    message, accepted = offer.label, True
                else:
                    message = line.partition("|")[2] or "Yes, I'd like some help with this."
            elif line.startswith("@tap:"):
                message = line.removeprefix("@tap:")
                if not any(p.label.lower() == message.lower() for p in last_prompts):
                    finding = f"no '{message}' button to tap"
            else:
                message = line

            capture.notes.clear()
            async with pool.as_user(claims) as conn:
                turn = await orchestrator.send(conn, claims, thread.id, message)
            last_prompts = list(turn.prompts)
            exchanges.append(
                Exchange(
                    message=message, reply=turn.content, repair_notes=list(capture.notes),
                    offered=any(p.technique for p in turn.prompts),
                    buttons=[p.label for p in turn.prompts],
                    framework=await _framework_after(claims, thread.id),
                    chat=chat, finding=finding,
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
        # Everything said so far in this chat, as the live repairs judge it.
        said = " ".join(e.message for e in exchanges[: index + 1] if e.chat == exchange.chat)
        findings += validators.check(exchange.reply, said)
        findings += validators.style_findings(exchange.reply, style.value)
        findings += validators.says_framework(exchange.reply, FRAMEWORK_NAMES)
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
    phases = [(e.framework[2] if e.framework and e.framework[1] == "accepted" else None, e.buttons)
              for e in exchanges]
    findings += validators.missing_handoff(phases, [e.message for e in exchanges])
    if scenario.get("expect_after_questions"):
        tapped = next((i for i, e in enumerate(exchanges) if e.message.lower() == "chat more"), None)
        if tapped is not None:
            findings += validators.after_framework_questions_asked(
                # From the reply to Chat More itself, which asks the first of the three.
                [e.reply for e in exchanges[tapped:]], AFTER_FRAMEWORK_QUESTIONS
            )
    if scenario.get("expect_framework"):
        reached = [e.framework[2] for e in exchanges if e.framework and e.framework[1] == "accepted"]
        if not reached:
            findings.append(validators.Finding("journey", "never entered a framework"))
        elif "somatic" not in reached:
            findings.append(validators.Finding("journey", f"stopped at {reached[-1]}, never reached somatic"))
    return findings


def _first_offer(exchanges: list[Exchange]) -> int | None:
    """Which of their messages the first offer answered, counting the style tap out."""
    return next((i for i, e in enumerate(exchanges, 1) if e.offered and e.chat == 1), None)


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", help="run every scenario as this existing user instead of a fresh one each")
    parser.add_argument("--verbose", action="store_true", help="print every reply")
    parser.add_argument("--scenario", help="run only the scenario with this name")
    args = parser.parse_args()

    scenarios = yaml.safe_load(SCENARIOS.read_text())
    if args.scenario:
        scenarios = [s for s in scenarios if s["name"] == args.scenario]
    failures = 0
    # Every reply per style, for the separation table at the end: the styles are meant to
    # behave differently, and nothing else in the run would show that they do not.
    by_style: dict[str, list[str]] = {}
    offers: dict[str, list[int | None]] = {}

    # pool.as_user() needs the pool open; nothing here runs under FastAPI's lifespan.
    await pool.open_pool()

    for style in SupportStyle:
        for scenario in scenarios:
            user_id = args.user or await _fresh_user(scenario["name"], style)
            exchanges = await _run_one(user_id, style, scenario["turns"], scenario.get("start_in"))
            findings = _score(exchanges, style, scenario)
            by_style.setdefault(style.value, []).extend(e.reply for e in exchanges)
            offers.setdefault(style.value, []).append(_first_offer(exchanges))
            failures += len(findings)

            print(f"\n=== {scenario['name']} / {style.value} ===")
            if args.verbose:
                for exchange in exchanges:
                    print(f"  > {exchange.message}\n  < {exchange.reply}")
                    state = exchange.framework
                    print(f"    [chat {exchange.chat} | framework {state[0]} {state[1]} {state[2]}]"
                          if state else f"    [chat {exchange.chat} | no framework]")
                    if exchange.buttons:
                        print(f"    [buttons] {exchange.buttons}")
                    if exchange.offered:
                        print("    [offered a framework]")
                    if exchange.repair_notes:
                        print(f"    [repair] {'; '.join(exchange.repair_notes)}")
                    print()
            for finding in findings:
                print(f"  FAIL {finding}")
            if not findings:
                print("  clean")

    await pool.close_pool()
    print("\nstyle         replies  avg chars  asks a question  opens with I  first offer at message")
    for name, replies in by_style.items():
        n = len(replies) or 1
        chars = sum(len(r) for r in replies) / n
        asks = 100 * sum("?" in r for r in replies) / n
        own = 100 * sum(r.lstrip().lower().startswith(("i ", "i'", "i\u2019")) for r in replies) / n
        print(f"{name:<13} {len(replies):>7}  {chars:>9.0f}  {asks:>14.0f}%  {own:>11.0f}%  {offers[name]}")
    print(f"\ntotal findings: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
