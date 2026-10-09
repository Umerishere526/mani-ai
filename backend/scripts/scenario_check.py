# ABOUTME: Runs the client's test conversations through the real stack and model, in every style.
# ABOUTME: Reports what the client checks by eye: repeating, styles that sound alike, the offer.

from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import re
import sys
import uuid
from dataclasses import dataclass, field

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from mani.auth.jwt import Claims  # noqa: E402
from mani.chat import orchestrator  # noqa: E402
from mani.chat.greeting import KEEP_CHATTING_LABEL, TELL_ME_MORE_LABEL, TRY_IT_LABEL  # noqa: E402
from mani.db import pool  # noqa: E402
from mani.prompts import cache  # noqa: E402

SCENARIOS = pathlib.Path(__file__).with_name("scenarios.json")
STYLES = ("direct", "supportive", "reflective")
WORD = re.compile(r"[a-z']{4,}")
INTERNAL = re.compile(r"\b(nearest|closest)\b|\bframework_id\b|\boffer_fit\b", re.IGNORECASE)
# The share of a reply's first sentence made of the person's own last words. Past ECHO it is their
# sentence handed back; past OPENS_ON_THEM the reply opens by restating them.
ECHO = 0.6
OPENS_ON_THEM = 0.4
# Two styles whose questions at the same point share this much of their words ask the same thing.
SAME_QUESTION = 0.5
# A question made up almost wholly of words the person has already said is asking for what they said.
ASKS_WHAT_THEY_SAID = 0.8
# Conversations run at once. A turn holds a pool connection while client.complete records its cost
# row on a second, so more than half of MAX_POOL_SIZE at once can leave every turn waiting forever.
AT_ONCE = 4


@dataclass
class Exchange:
    person: str
    reply: str
    buttons: list[str]
    offered: str | None
    flags: list[str] = field(default_factory=list)
    opens_on_them: bool = False
    question: set[str] = field(default_factory=set)


def _words(text: str) -> set[str]:
    return set(WORD.findall(text.lower()))


def _first_sentence(text: str) -> str:
    return re.split(r"(?<=[.!?])\s+", text.strip(), maxsplit=1)[0]


def _question(text: str) -> set[str]:
    asked = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.endswith("?")]
    return _words(asked[-1]) if asked else set()


def _check(exchange: Exchange, registry, told_more: bool, said: set[str]) -> None:
    said, opening = _words(exchange.person), _words(_first_sentence(exchange.reply))
    echo = len(opening & said) / len(opening) if opening else 0.0
    exchange.opens_on_them = echo >= OPENS_ON_THEM
    exchange.question = _question(exchange.reply)
    if echo >= ECHO:
        exchange.flags.append(f"hands their words back ({echo:.0%})")
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


async def _converse(name: str, lines: list[str], style: str, registry) -> list[Exchange]:
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
        for text in lines:
            said |= _words(text)
            exchanges.append(await _exchange(claims, thread.id, text, registry, told_more=False, said=said))
            if exchanges[-1].offered:
                exchanges.append(
                    await _exchange(claims, thread.id, TELL_ME_MORE_LABEL, registry, told_more=True, said=said)
                )
                break
        return exchanges
    finally:
        async with pool.as_admin() as conn:
            await conn.execute("delete from admin.llm_calls where user_id = $1", user)
            await conn.execute("delete from auth.users where id = $1", user)


async def _exchange(
    claims: Claims, thread_id, text: str, registry, *, told_more: bool, said: set[str]
) -> Exchange:
    turn = await _send(claims, thread_id, text)
    exchange = Exchange(
        person=text, reply=turn.content, buttons=[p.label for p in turn.prompts],
        offered=next((p.technique for p in turn.prompts if p.technique), None),
    )
    _check(exchange, registry, told_more, said)
    return exchange


async def _send(claims: Claims, thread_id, text: str):
    async with pool.as_user(claims) as conn:
        return await orchestrator.send(conn, claims, thread_id, text)


def _report(name: str, runs: dict[str, list[Exchange]]) -> int:
    print(f"\n=== {name} ===")
    flagged = 0
    for style, exchanges in runs.items():
        opened = sum(e.opens_on_them for e in exchanges if e.person != TELL_ME_MORE_LABEL)
        offer = next((i + 1 for i, e in enumerate(exchanges) if e.offered), None)
        framework = next((e.offered for e in exchanges if e.offered), None)
        print(f"\n  {style}: opens on their words {opened}/{len(exchanges)}, "
              f"offer at their message {offer or '-'} ({framework or 'none'})")
        for exchange in exchanges:
            flagged += len(exchange.flags)
            mark = "  !! " + "; ".join(exchange.flags) if exchange.flags else ""
            print(f"    > {exchange.person[:60]}\n      {exchange.reply.splitlines()[0][:110]}{mark}")
    for turn in range(max(len(e) for e in runs.values())):
        questions = {s: e[turn].question for s, e in runs.items() if turn < len(e) and e[turn].question}
        pairs = [(a, b) for a in questions for b in questions if a < b]
        for a, b in pairs:
            shared = len(questions[a] & questions[b]) / len(questions[a] | questions[b])
            if shared >= SAME_QUESTION:
                flagged += 1
                print(f"  !! message {turn + 1}: {a} and {b} ask the same question ({shared:.0%})")
    return flagged


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", help="run only this scenario from scenarios.json")
    parser.add_argument("--style", choices=STYLES, help="run only this style")
    args = parser.parse_args()
    scenarios = json.loads(SCENARIOS.read_text())
    chosen = {k: v for k, v in scenarios.items() if not args.scenario or k == args.scenario}
    styles = [args.style] if args.style else list(STYLES)
    await pool.open_pool()
    try:
        registry = (await cache.load()).registry
        jobs = [(name, style) for name in chosen for style in styles]
        gate = asyncio.Semaphore(AT_ONCE)

        async def gated(name: str, style: str) -> list[Exchange]:
            async with gate:
                return await _converse(name, chosen[name]["lines"], style, registry)

        results = await asyncio.gather(*(gated(name, style) for name, style in jobs))
    finally:
        await pool.close_pool()
    by_scenario: dict[str, dict[str, list[Exchange]]] = {}
    for (name, style), exchanges in zip(jobs, results):
        by_scenario.setdefault(name, {})[style] = exchanges
    flagged = sum(_report(name, runs) for name, runs in by_scenario.items())
    print(f"\n{flagged} flag(s) across {len(jobs)} conversation(s)")
    return 1 if flagged else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
