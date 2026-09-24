# ABOUTME: Runs scripted conversations through the real stack and scores every reply.
# ABOUTME: The validators already encode the specification; this points them at live output.

from __future__ import annotations

import argparse
import asyncio
import logging
import pathlib
import sys
from dataclasses import dataclass, field

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from mani.auth.jwt import Claims  # noqa: E402
from mani.chat import orchestrator  # noqa: E402
from mani.db import pool, threads  # noqa: E402
from mani.models.rows import SupportStyle, TechniqueOutcome  # noqa: E402
from tests.evals import validators  # noqa: E402

SCENARIOS = pathlib.Path(__file__).with_name("eval_conversations.yaml")


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


async def _run_one(
    user_id: str, style: SupportStyle, turns: list[str], start_in: dict | None = None
) -> list[Exchange]:
    """One conversation in one style."""
    claims = _claims_for(user_id)
    exchanges: list[Exchange] = []

    capture = _RepairNoteCapture()
    orch_logger = logging.getLogger("mani.chat.orchestrator")
    orch_logger.addHandler(capture)
    previous_level = orch_logger.level
    orch_logger.setLevel(logging.INFO)

    # The client's own opening: the greeting asks how to speak, the person taps a style, and
    # Mani answers with that style's opener - so every scenario starts the way a real one does.
    async with pool.as_user(claims) as conn:
        async with conn.transaction():
            thread, _ = await orchestrator.start_thread(conn, claims)
    async with pool.as_user(claims) as conn:
        async with conn.transaction():
            await orchestrator.send(conn, claims, thread.id, style.value.capitalize())
    if start_in:
        # A scenario that tests the stages themselves starts with the framework already
        # accepted, rather than depending on the model offering it on a particular turn.
        async with pool.as_user(claims) as conn:
            async with conn.transaction():
                await threads.set_technique_outcome(
                    conn, thread.id, user_id, start_in["framework"], TechniqueOutcome.ACCEPTED,
                    at_message_count=0, phase=start_in["phase"],
                )

    try:
        for message in turns:
            capture.notes.clear()
            async with pool.as_user(claims) as conn:
                async with conn.transaction():
                    turn = await orchestrator.send(conn, claims, thread.id, message)
            exchanges.append(
                Exchange(
                    message=message, reply=turn.content, repair_notes=list(capture.notes),
                    offered=any(p.technique for p in turn.prompts),
                )
            )
    finally:
        orch_logger.removeHandler(capture)
        orch_logger.setLevel(previous_level)

    return exchanges


def _score(
    exchanges: list[Exchange], style: SupportStyle, *, heard: bool = False
) -> list[validators.Finding]:
    """`heard`: the scenario is someone asking only to be heard, where a reply with no
    question is the right answer, so the stalled-reply check does not apply."""
    findings: list[validators.Finding] = []
    for index, exchange in enumerate(exchanges):
        # Everything they have said so far, as the live repairs judge it: a feeling named
        # two messages ago is theirs to have mirrored now.
        said = " ".join(e.message for e in exchanges[: index + 1])
        findings += validators.check(exchange.reply, said)
        findings += validators.style_findings(exchange.reply, style.value)
    findings += validators.repeated_openers([e.reply for e in exchanges])
    if not heard:
        findings += validators.unasked_before_offer([(e.reply, e.offered) for e in exchanges])
    return findings


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", required=True, help="an existing auth user id to run as")
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

    # pool.as_user() needs the pool open; nothing here runs under FastAPI's lifespan.
    await pool.open_pool()

    for style in SupportStyle:
        for scenario in scenarios:
            exchanges = await _run_one(
                args.user, style, scenario["turns"], scenario.get("start_in")
            )
            findings = _score(exchanges, style, heard=scenario.get("heard", False))
            by_style.setdefault(style.value, []).extend(e.reply for e in exchanges)
            failures += len(findings)

            print(f"\n=== {scenario['name']} / {style.value} ===")
            if args.verbose:
                for exchange in exchanges:
                    print(f"  > {exchange.message}\n  < {exchange.reply}")
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
    print("\nstyle         replies  avg chars  asks a question  opens with I")
    for name, replies in by_style.items():
        n = len(replies) or 1
        chars = sum(len(r) for r in replies) / n
        asks = 100 * sum("?" in r for r in replies) / n
        own = 100 * sum(r.lstrip().lower().startswith(("i ", "i'", "i\u2019")) for r in replies) / n
        print(f"{name:<13} {len(replies):>7}  {chars:>9.0f}  {asks:>14.0f}%  {own:>11.0f}%")
    print(f"\ntotal findings: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
