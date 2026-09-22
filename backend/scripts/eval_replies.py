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
from mani.models.rows import SupportStyle  # noqa: E402
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


async def _run_one(user_id: str, style: SupportStyle, turns: list[str]) -> list[Exchange]:
    """One conversation in one style."""
    claims = _claims_for(user_id)
    exchanges: list[Exchange] = []

    capture = _RepairNoteCapture()
    orch_logger = logging.getLogger("mani.chat.orchestrator")
    orch_logger.addHandler(capture)
    previous_level = orch_logger.level
    orch_logger.setLevel(logging.INFO)

    async with pool.as_user(claims) as conn:
        async with conn.transaction():
            thread, _ = await orchestrator.start_thread(conn, claims)
            await threads.apply(
                conn, thread.id, user_id, threads.ThreadUpdates(conversation_style=style)
            )

    try:
        for message in turns:
            capture.notes.clear()
            async with pool.as_user(claims) as conn:
                async with conn.transaction():
                    turn = await orchestrator.send(conn, claims, thread.id, message)
            exchanges.append(
                Exchange(message=message, reply=turn.content, repair_notes=list(capture.notes))
            )
    finally:
        orch_logger.removeHandler(capture)
        orch_logger.setLevel(previous_level)

    return exchanges


def _score(exchanges: list[Exchange]) -> list[validators.Finding]:
    findings = [
        finding
        for exchange in exchanges
        for finding in validators.check(exchange.reply, exchange.message)
    ]
    return findings + validators.repeated_openers([e.reply for e in exchanges])


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", required=True, help="an existing auth user id to run as")
    parser.add_argument("--verbose", action="store_true", help="print every reply")
    args = parser.parse_args()

    scenarios = yaml.safe_load(SCENARIOS.read_text())
    failures = 0

    # pool.as_user() needs the pool open; nothing here runs under FastAPI's lifespan.
    await pool.open_pool()

    for style in SupportStyle:
        for scenario in scenarios:
            exchanges = await _run_one(args.user, style, scenario["turns"])
            findings = _score(exchanges)
            failures += len(findings)

            print(f"\n=== {scenario['name']} / {style.value} ===")
            if args.verbose:
                for exchange in exchanges:
                    print(f"  > {exchange.message}\n  < {exchange.reply}")
                    if exchange.repair_notes:
                        print(f"    [repair] {'; '.join(exchange.repair_notes)}")
                    print()
            for finding in findings:
                print(f"  FAIL {finding}")
            if not findings:
                print("  clean")

    await pool.close_pool()
    print(f"\ntotal findings: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
