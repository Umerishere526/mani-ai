# ABOUTME: Runs the client's test conversations through the real stack and model, in every style.
# ABOUTME: Reports what the client checks by eye (asking again, the check, the offer, each letter) and each turn's cost.

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
from mani.chat import orchestrator  # noqa: E402
from mani.chat import repairs, reply_checks, understanding  # noqa: E402
from mani.chat.greeting import KEEP_CHATTING_LABEL, TELL_ME_MORE_LABEL, TRY_IT_LABEL  # noqa: E402
from mani.db import pool  # noqa: E402
from mani.prompts import cache  # noqa: E402

SCENARIOS = pathlib.Path(__file__).with_name("scenarios.json")
STYLES = ("directive", "supportive", "reflective")
WORD = re.compile(r"[a-z']{4,}")
INTERNAL = re.compile(r"\bframework_id\b|\bmay_check\b|\bcheck_answer\b", re.IGNORECASE)
# What the scripted person says to Mani's check of its understanding, unless the conversation names
# its own `check_answer` (spec 0006).
DEFAULT_CHECK_ANSWER = "Yes, that's right."
# Mani explaining how people feel instead of finding out ("can make it hard to separate one piece of
# feedback from…", live 2026-10-13). Eval tooling only, read by a person.
EXPLAINS_PEOPLE = re.compile(
    r"\bcan (?:make|leave)\b|\bcan be (?:hard|difficult|painful)\b|\bit'?s (?:natural|normal|common|understandable)\b",
    re.IGNORECASE,
)
# One of their messages per step before the check: the problem, its core issue, the feeling underneath.
EARLIEST_CHECK = len(understanding.STEPS)
# Offer wording: the model offering in its own text instead of the offer field, which code never
# sends as an offer. Eval tooling only; nothing at runtime reads it.
OFFER_WORDS = re.compile(r"\bframework\b|would you like to try|\btry it\b", re.IGNORECASE)
OFFER_WORDS_FLAG = "offer words in text"
# Mani speaking about the person instead of to them, as a third person note pasted into a client line
# does ("From what you've shared, their boss…", live 2026-10-13). Eval tooling only. A stored word
# right after "shared" or "mentioned" may still name someone else's, so a flag is read by a person.
TALKS_ABOUT_THEM = re.compile(r"\bthe user\b|\b(?:shared|mentioned),? (?:their|they)\b", re.IGNORECASE)
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
    # The stage ids and statuses after the turn, while a framework runs (orchestrator.Turn.stage_trace).
    trace: list[dict] | None = None
    # What Mani understands of them as stored after the turn (orchestrator.Turn.understanding).
    understanding: dict | None = None
    # When Mani's latest check was made, after the turn (orchestrator.Turn.check_at_message_count).
    check_at: int | None = None
    # Whether this reply was Mani's check of its understanding.
    checked: bool = False


def _words(text: str) -> set[str]:
    return set(WORD.findall(text.lower()))


def _question(text: str) -> set[str]:
    asked = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.endswith("?")]
    return _words(asked[-1]) if asked else set()


def offer_words_in_text(text: str, registry) -> bool:
    """Whether a reply that is not the client's offer still offers: a set's name, the word
    framework, or the permission question, all of which only the rendered offer carries."""
    names = [registry.get(fid).name for fid in registry.ids]
    return bool(OFFER_WORDS.search(text) or any(name.lower() in text.lower() for name in names))


def matches_template(text: str, template: str) -> bool:
    """Whether a reply is the client's template word for word, with only its slots changed."""
    fixed = [re.escape(part) for part in re.split(r"<[^<>]+>", template)]
    return re.fullmatch(".+?".join(fixed), text) is not None


def _offering(registry, framework_id: str | None, key: str, style: str) -> str | None:
    framework = registry.get(framework_id)
    return (((framework.stages or {}).get("offering") or {}).get(key) or {}).get(style) if framework else None


def stage_flags(reply: str, trace: list[dict] | None, before: list[dict] | None, stages: dict, style: str) -> list[str]:
    """Inside a framework: a stage reached opens with its letter line, and a stage stored as known or
    possible is said back, never asked with the client's question (spec 0004)."""
    asking = next((row for row in trace or [] if row["asking"]), None)
    if asking is None:
        return []
    was = next((row["stage"] for row in before or [] if row["asking"]), None)
    stage = stages.get(asking["stage"]) or {}
    flags = []
    if asking["stage"] != was and stage.get("intro") and not reply.startswith(stage["intro"]):
        flags.append("stage reply without its letter line")
    ask = (stage.get("ask") or {}).get(style)
    if asking["status"] in ("known", "possible") and ask and ask in reply:
        flags.append("asked a stage already known")
    return flags


def _check(
    exchange: Exchange, registry, told_more: bool, said: set[str], style: str, previous: Exchange | None,
    framework_id: str | None,
) -> None:
    exchange.question = _question(exchange.reply)
    framework = registry.get(framework_id)
    if framework:
        exchange.flags += stage_flags(
            exchange.reply, exchange.trace, previous.trace if previous else None, framework.stages, style,
        )
    # A stage said back to confirm it reuses their words on purpose, so it is not asking for them again.
    confirming = any(row["asking"] and row["status"] in ("known", "possible", "partial") for row in exchange.trace or [])
    if (not confirming and exchange.question
            and len(exchange.question & said) / len(exchange.question) >= ASKS_WHAT_THEY_SAID):
        exchange.flags.append("asks what they already said")
    if INTERNAL.search(exchange.reply):
        exchange.flags.append("internal words")
    if TALKS_ABOUT_THEM.search(exchange.reply):
        exchange.flags.append("talks about them, not to them")
    if not exchange.offered and framework is None:
        if EXPLAINS_PEOPLE.search(exchange.reply):
            exchange.flags.append("explains people")
    if not exchange.offered:
        # The text that was sent, which inside a framework is mostly code's, not the model's draft.
        if previous and reply_checks.repeats(exchange.reply, previous.reply):
            exchange.flags.append("sent text repeats the last question")
        if offer_words_in_text(exchange.reply, registry):
            exchange.flags.append(OFFER_WORDS_FLAG)
        return
    template = repairs.offer_template(registry.get(exchange.offered), style)
    if not told_more and template and not matches_template(exchange.reply, template):
        exchange.flags.append("offer not the client's template")
    expected = [TRY_IT_LABEL, KEEP_CHATTING_LABEL] if told_more else [
        TRY_IT_LABEL, TELL_ME_MORE_LABEL, KEEP_CHATTING_LABEL]
    if exchange.buttons != expected:
        exchange.flags.append(f"capsules {exchange.buttons}")


# What a stage reached should be, by the status the walk stored for it as it was reached.
_REACHED_AS = {"said back": ("known", "possible", "partial"), "asked": ("missing",)}


def reached_flags(trace: list[dict] | None, expected: dict[str, str], seen: set[str]) -> list[str]:
    """A stage reached for the first time other than the conversation expects: "said back" when they had
    already said it, whole or in part, "asked" when nothing (2026-10-13: C, D and E were asked again though
    they had said them)."""
    asking = next((row for row in trace or [] if row["asking"]), None)
    if asking is None or asking["stage"] in seen:
        return []
    seen.add(asking["stage"])
    want = expected.get(asking["stage"])
    if want and asking["status"] not in _REACHED_AS[want]:
        return [f"reached {asking['stage']} as {asking['status']}, expected {want}"]
    return []


def conversations(groups: dict) -> dict[str, dict]:
    """Every conversation in scenarios.json by name, carrying its group's expectations under its own."""
    return {
        name: {**conversation, "group": group_name,
               "expect": {**group.get("expect", {}), **conversation.get("expect", {})}}
        for group_name, group in groups.items()
        for name, conversation in group["conversations"].items()
    }


def timing_flags(checked_at: int | None, lines: int, expect: dict) -> dict[int, str]:
    """What is wrong with when Mani's first check came, keyed by the person's line the flag belongs
    on. `check_from` is the earliest line a check may follow; `check_by` the latest, by default the
    conversation's last line, checked only when the conversation reaches it (spec 0006)."""
    earliest = expect.get("check_from", EARLIEST_CHECK)
    latest = expect.get("check_by", lines)
    if checked_at is not None and checked_at < earliest:
        return {checked_at: f"checked at their message {checked_at}, expected from {earliest}"}
    if checked_at is not None and checked_at > latest:
        return {checked_at: f"checked at their message {checked_at}, expected by {latest}"}
    if checked_at is None and lines >= latest:
        return {latest: f"no check by their message {latest}"}
    return {}


async def _converse(name: str, conversation: dict, style: str, registry) -> list[Exchange]:
    """One conversation in one style. Each check Mani makes is answered with `check_answer`; a yes
    is expected to bring the offer, then its Tell me more, or the answers in `after_offer`."""
    lines, expect, after = conversation["lines"], conversation["expect"], conversation.get("after_offer")
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
        on_line: dict[int, Exchange] = {}
        said: set[str] = set()
        billed = [0]
        checked_at = None

        async def say(text: str, *, told_more: bool = False, framework_id: str | None = None) -> Exchange:
            previous = exchanges[-1] if exchanges else None
            exchange = await _exchange(
                claims, thread.id, text, registry, told_more=told_more, said=said, billed=billed, style=style,
                previous=previous, framework_id=framework_id,
            )
            exchange.checked = exchange.check_at is not None and exchange.check_at != (previous.check_at if previous else None)
            exchanges.append(exchange)
            return exchange

        for number, text in enumerate(lines, start=1):
            said |= _words(text)
            on_line[number] = exchange = await say(text)
            if exchange.offered:
                exchange.flags.append("offer without a confirmed check")
            if not exchange.checked:
                continue
            checked_at = checked_at or number
            answer = conversation.get("check_answer", DEFAULT_CHECK_ANSWER)
            said |= _words(answer)
            answered = await say(answer)
            if not expect.get("check_confirms", True):
                if answered.offered:
                    answered.flags.append("offered after a check they did not confirm")
                continue
            if not answered.offered:
                answered.flags.append("confirmed check, no offer")
                break
            framework = answered.offered
            seen: set[str] = set()
            for line in (after or {}).get("lines") or [TELL_ME_MORE_LABEL]:
                reached = await say(line, told_more=line == TELL_ME_MORE_LABEL, framework_id=framework)
                reached.flags += reached_flags(reached.trace, (after or {}).get("stages") or {}, seen)
            if after and after.get("answer") == "no":
                keep = _offering(registry, framework, "keep_chatting", style)
                declined = exchanges[exchanges.index(answered) + 1]
                if keep and not matches_template(declined.reply, keep):
                    declined.flags.append("keep chatting not the client's template")
            break
        for number, flag in timing_flags(checked_at, len(lines), expect).items():
            if number in on_line:
                on_line[number].flags.append(flag)
        return exchanges
    finally:
        async with pool.as_admin() as conn:
            await conn.execute("delete from admin.llm_calls where user_id = $1", user)
            await conn.execute("delete from auth.users where id = $1", user)


async def _exchange(
    claims: Claims, thread_id, text: str, registry, *, told_more: bool, said: set[str], billed: list[int],
    style: str, previous: Exchange | None, framework_id: str | None,
) -> Exchange:
    started = time.perf_counter()
    turn = await _send(claims, thread_id, text)
    seconds = time.perf_counter() - started
    exchange = Exchange(
        person=text, reply=turn.content, buttons=[p.label for p in turn.prompts],
        offered=next((p.technique for p in turn.prompts if p.technique), None),
        cost=await _cost(thread_id, seconds, billed), checks=turn.checks, trace=turn.stage_trace,
        understanding=turn.understanding, check_at=turn.check_at_message_count,
    )
    _check(exchange, registry, told_more, said, style, previous, framework_id)
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


def _report(name: str, runs: dict[str, list[Exchange]], *, full: bool = False) -> int:
    print(f"\n=== {name} ===")
    flagged = 0
    for style, exchanges in runs.items():
        checks = sum(e.checked for e in exchanges)
        framework = next((e.offered for e in exchanges if e.offered), None)
        print(f"\n  {style}: {checks} check(s), offer: {framework or 'none'}")
        for exchange in exchanges:
            flagged += len(exchange.flags)
            mark = "  !! " + "; ".join(exchange.flags) if exchange.flags else ""
            cost, checked = exchange.cost, f"  [{'; '.join(exchange.checks)}]" if exchange.checks else ""
            said = " ".join(exchange.reply.split())
            said = said if full else said[:110]
            person = exchange.person if full else exchange.person[:60]
            print(f"    > {person}\n      {said}{mark}{checked}\n"
                  f"      {cost.seconds:.1f} s, {cost.calls} call(s), {cost.input_tokens} in "
                  f"({cost.cached_tokens} cached), {cost.output_tokens} out ({cost.reasoning_tokens} thinking)")
            if exchange.checked:
                # Read by a person: does the check use only their words?
                print(f"      check: {' '.join(exchange.reply.split())}")
            if exchange.offered:
                # Read side by side by a person: does the offer's slot hold the feeling they named?
                feeling = (exchange.understanding or {}).get("feeling") or "-"
                print(f"      feeling stored: {feeling}\n      offer: {' '.join(exchange.reply.split())}")
    return flagged


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", help="run only this conversation, or this group, from scenarios.json")
    parser.add_argument("--style", choices=STYLES, help="run only this style")
    parser.add_argument("--full", action="store_true", help="print every line whole, as a transcript")
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
                return await _converse(name, chosen[name], style, registry)

        results = await asyncio.gather(*(gated(name, style) for name, style in jobs))
    finally:
        await pool.close_pool()
    by_scenario: dict[str, dict[str, list[Exchange]]] = {}
    for (name, style), exchanges in zip(jobs, results):
        by_scenario.setdefault(name, {})[style] = exchanges
    flagged = sum(_report(name, runs, full=args.full) for name, runs in by_scenario.items())
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
    worded = sum(OFFER_WORDS_FLAG in e.flags for e in exchanges)
    print(f"  offer words in a reply's own text: {worded} of {len(exchanges)} replies")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
