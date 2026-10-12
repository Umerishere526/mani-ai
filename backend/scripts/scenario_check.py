# ABOUTME: Runs the client's test conversations through the real stack and model, in every style.
# ABOUTME: Reports what the client checks by eye (asking again, the offer and its timing) and what each turn cost.

from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import re
import statistics
import sys
import time
import uuid
from collections import Counter
from dataclasses import dataclass, field

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from mani.auth.jwt import Claims  # noqa: E402
from mani.chat import context, orchestrator  # noqa: E402
from mani.chat.greeting import KEEP_CHATTING_LABEL, TELL_ME_MORE_LABEL, TRY_IT_LABEL  # noqa: E402
from mani.db import pool  # noqa: E402
from mani.prompts import cache  # noqa: E402

SCENARIOS = pathlib.Path(__file__).with_name("scenarios.json")
STYLES = ("directive", "supportive", "reflective")
WORD = re.compile(r"[a-z']{4,}")
INTERNAL = re.compile(r"\bframework_id\b|\boffer_window\b", re.IGNORECASE)
# A question made up almost wholly of words the person has already said is asking for what they said.
ASKS_WHAT_THEY_SAID = 0.8
# What a turn is held to (R2, muhammad 2026-10-12). Reported, never a failure: one run is noise.
MEDIAN_TURN_SECONDS = 4.0
SLOWEST_TURN_SECONDS = 10.0
# Conversations run at once. A turn holds a pool connection while client.complete records its cost
# row on a second, so more than half of MAX_POOL_SIZE at once can leave every turn waiting forever.
AT_ONCE = 4


@dataclass
class Cost:
    """What one turn's model calls billed and how long the person waited."""

    seconds: float = 0.0
    calls: int = 0
    input_tokens: int = 0
    cached_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0


@dataclass
class Exchange:
    person: str
    reply: str
    buttons: list[str]
    offered: str | None
    flags: list[str] = field(default_factory=list)
    question: set[str] = field(default_factory=set)
    cost: Cost = field(default_factory=Cost)
    checks: list[str] = field(default_factory=list)


def _words(text: str) -> set[str]:
    return set(WORD.findall(text.lower()))


def _question(text: str) -> set[str]:
    asked = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.endswith("?")]
    return _words(asked[-1]) if asked else set()


def _check(exchange: Exchange, registry, told_more: bool, said: set[str]) -> None:
    exchange.question = _question(exchange.reply)
    if exchange.question and len(exchange.question & said) / len(exchange.question) >= ASKS_WHAT_THEY_SAID:
        exchange.flags.append("asks what they already said")
    if INTERNAL.search(exchange.reply):
        exchange.flags.append("internal words")
    if not exchange.offered:
        return
    framework = registry.get(exchange.offered)
    letters = re.compile(r"[^a-z0-9]")
    if framework and letters.sub("", framework.name.lower()) not in letters.sub("", exchange.reply.lower()):
        exchange.flags.append("framework not named")
    if framework and framework.summary and not told_more and framework.summary in exchange.reply:
        exchange.flags.append("description in the offer")
    expected = [TRY_IT_LABEL, KEEP_CHATTING_LABEL] if told_more else [
        TRY_IT_LABEL, TELL_ME_MORE_LABEL, KEEP_CHATTING_LABEL]
    if exchange.buttons != expected:
        exchange.flags.append(f"capsules {exchange.buttons}")


def conversations(groups: dict) -> dict[str, dict]:
    """Every conversation in scenarios.json by name, carrying its group's expectations under its own."""
    return {
        name: {**conversation, "group": group_name,
               "expect": {**group.get("expect", {}), **conversation.get("expect", {})}}
        for group_name, group in groups.items()
        for name, conversation in group["conversations"].items()
    }


def timing_flags(offered_at: int | None, lines: int, expect: dict) -> dict[int, str]:
    """What is wrong with when the offer came, keyed by the person's message the flag belongs on.
    `offer_from` is the earliest message an offer may follow; `offer_by` the latest, checked only
    when the conversation reaches it."""
    earliest = expect.get("offer_from", context.FIRST_OFFER_OPENS)
    latest = expect.get("offer_by")
    if offered_at is not None and offered_at < earliest:
        return {offered_at: f"offered at their message {offered_at}, expected from {earliest}"}
    if latest is not None and offered_at is not None and offered_at > latest:
        return {offered_at: f"offered at their message {offered_at}, expected by {latest}"}
    if latest is not None and offered_at is None and lines >= latest:
        return {latest: f"no offer by their message {latest}"}
    return {}


async def _converse(name: str, lines: list[str], expect: dict, style: str, registry) -> list[Exchange]:
    """One conversation in one style, up to the first offer and its Tell me more."""
    user = uuid.uuid4()
    claims = Claims(sub=str(user), raw={"sub": str(user), "role": "authenticated"})
    async with pool.as_admin() as conn:
        await conn.execute(
            "insert into auth.users (id, email) values ($1, $2)", user, f"{name}.{style}.{user}@scenario.check"
        )
    try:
        async with pool.as_user(claims) as conn:
            thread, _ = await orchestrator.start_thread(conn, claims)
        await _send(claims, thread.id, style.capitalize())
        exchanges: list[Exchange] = []
        said: set[str] = set()
        billed = [0]
        offered_at = None
        for number, text in enumerate(lines, start=1):
            said |= _words(text)
            exchanges.append(
                await _exchange(claims, thread.id, text, registry, told_more=False, said=said, billed=billed)
            )
            if exchanges[-1].offered:
                offered_at = number
                exchanges.append(await _exchange(
                    claims, thread.id, TELL_ME_MORE_LABEL, registry, told_more=True, said=said, billed=billed
                ))
                break
        for number, flag in timing_flags(offered_at, len(lines), expect).items():
            exchanges[number - 1].flags.append(flag)
        return exchanges
    finally:
        async with pool.as_admin() as conn:
            await conn.execute("delete from admin.llm_calls where user_id = $1", user)
            await conn.execute("delete from auth.users where id = $1", user)


async def _exchange(
    claims: Claims, thread_id, text: str, registry, *, told_more: bool, said: set[str], billed: list[int]
) -> Exchange:
    started = time.perf_counter()
    turn = await _send(claims, thread_id, text)
    seconds = time.perf_counter() - started
    exchange = Exchange(
        person=text, reply=turn.content, buttons=[p.label for p in turn.prompts],
        offered=next((p.technique for p in turn.prompts if p.technique), None),
        cost=await _cost(thread_id, seconds, billed), checks=turn.checks,
    )
    _check(exchange, registry, told_more, said)
    return exchange


async def _cost(thread_id, seconds: float, billed: list[int]) -> Cost:
    """The calls this turn made, read before the conversation's rows are deleted. `billed` is how
    many of the thread's rows earlier turns already own."""
    async with pool.as_admin() as conn:
        rows = await conn.fetch(
            "select input_tokens, cached_input_tokens, output_tokens, reasoning_tokens "
            "from admin.llm_calls where thread_id = $1 order by created_at offset $2",
            thread_id, billed[0],
        )
    billed[0] += len(rows)
    return Cost(
        seconds=seconds, calls=len(rows),
        input_tokens=sum(r["input_tokens"] for r in rows),
        cached_tokens=sum(r["cached_input_tokens"] for r in rows),
        output_tokens=sum(r["output_tokens"] for r in rows),
        reasoning_tokens=sum(r["reasoning_tokens"] for r in rows),
    )


async def _send(claims: Claims, thread_id, text: str):
    async with pool.as_user(claims) as conn:
        return await orchestrator.send(conn, claims, thread_id, text)


def _report(name: str, runs: dict[str, list[Exchange]]) -> int:
    print(f"\n=== {name} ===")
    flagged = 0
    for style, exchanges in runs.items():
        offer = next((i + 1 for i, e in enumerate(exchanges) if e.offered), None)
        framework = next((e.offered for e in exchanges if e.offered), None)
        print(f"\n  {style}: offer at their message {offer or '-'} ({framework or 'none'})")
        for exchange in exchanges:
            flagged += len(exchange.flags)
            mark = "  !! " + "; ".join(exchange.flags) if exchange.flags else ""
            cost, checked = exchange.cost, f"  [{'; '.join(exchange.checks)}]" if exchange.checks else ""
            print(f"    > {exchange.person[:60]}\n      {exchange.reply.splitlines()[0][:110]}{mark}{checked}\n"
                  f"      {cost.seconds:.1f} s, {cost.calls} call(s), {cost.input_tokens} in "
                  f"({cost.cached_tokens} cached), {cost.output_tokens} out ({cost.reasoning_tokens} thinking)")
    return flagged


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", help="run only this conversation, or this group, from scenarios.json")
    parser.add_argument("--style", choices=STYLES, help="run only this style")
    args = parser.parse_args()
    scenarios = conversations(json.loads(SCENARIOS.read_text()))
    chosen = {
        name: c for name, c in scenarios.items()
        if not args.scenario or args.scenario in (name, c["group"])
    }
    styles = [args.style] if args.style else list(STYLES)
    await pool.open_pool()
    try:
        registry = (await cache.load()).registry
        jobs = [(name, style) for name in chosen for style in styles]
        gate = asyncio.Semaphore(AT_ONCE)

        async def gated(name: str, style: str) -> list[Exchange]:
            async with gate:
                return await _converse(name, chosen[name]["lines"], chosen[name]["expect"], style, registry)

        results = await asyncio.gather(*(gated(name, style) for name, style in jobs))
    finally:
        await pool.close_pool()
    by_scenario: dict[str, dict[str, list[Exchange]]] = {}
    for (name, style), exchanges in zip(jobs, results):
        by_scenario.setdefault(name, {})[style] = exchanges
    flagged = sum(_report(name, runs) for name, runs in by_scenario.items())
    _report_cost([e for runs in by_scenario.values() for exchanges in runs.values() for e in exchanges])
    print(f"\n{flagged} flag(s) across {len(jobs)} conversation(s)")
    return 1 if flagged else 0


def _report_cost(exchanges: list[Exchange]) -> None:
    """How long people waited and what the turns billed, against the targets. A run over a
    target is reported, not failed: one run is noise, three before and three after is not."""
    seconds = [e.cost.seconds for e in exchanges]
    median, slowest = statistics.median(seconds), max(seconds)
    over = "  !! over" if median > MEDIAN_TURN_SECONDS else ""
    print(f"\n  turn time: median {median:.1f} s (target {MEDIAN_TURN_SECONDS:.0f}){over}", end="")
    print(f", slowest {slowest:.1f} s (target {SLOWEST_TURN_SECONDS:.0f})"
          + ("  !! over" if slowest > SLOWEST_TURN_SECONDS else ""))
    calls = sum(e.cost.calls for e in exchanges)
    print(f"  {calls} model call(s) over {len(exchanges)} turn(s), "
          f"{sum(e.cost.input_tokens for e in exchanges)} in "
          f"({sum(e.cost.cached_tokens for e in exchanges)} cached), "
          f"{sum(e.cost.output_tokens for e in exchanges)} out "
          f"({sum(e.cost.reasoning_tokens for e in exchanges)} thinking)")
    missed = Counter(check for e in exchanges for check in e.checks)
    print("  reply checks missed: " + (", ".join(f"{n} x {c}" for c, n in missed.most_common()) or "none"))


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
