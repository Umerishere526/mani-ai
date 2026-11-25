# ABOUTME: Plays one regression scenario through the real stack (runner.send and the database) and gathers what the
# ABOUTME: report needs: the exchanges, every check's result, timings, the chat calls' usage and the judge's verdict.

from __future__ import annotations

import time
import uuid

import httpx

from evals.drive import Conversation, Exchange, converse, new_person
from evals.regression import checks, metrics
from evals.regression.judge import judge
from mani.chat import greeting, runner, turn as chat_turn
from mani.db import pool
from mani.errors import ErrorCategory, ServiceError

# What the person sends after a pause, to see that no ordinary reply comes back.
AFTER_PAUSE = "are you still there?"


async def _send(conversation: Conversation, said: str) -> Exchange:
    """One more message in a conversation already under way, recorded like converse records its own."""
    started = time.monotonic()
    got = await runner.send(conversation.claims, conversation.thread_id, said, uuid.uuid4())
    exchange = Exchange(said=said, tapped=True, reply=got.content, buttons=[p.label for p in got.prompts],
                        trace=got.trace or {}, seconds=time.monotonic() - started,
                        paused=got.paused_until is not None, crisis=got.crisis_detected)
    conversation.exchanges.append(exchange)
    return exchange


async def _refused_after_pause(conversation: Conversation) -> bool | None:
    """True when a message after the pause is refused as paused; None when the conversation never paused."""
    if not any(e.paused for e in conversation.exchanges):
        return None
    try:
        await runner.send(conversation.claims, conversation.thread_id, AFTER_PAUSE, uuid.uuid4())
    except ServiceError as error:
        return error.category == ErrorCategory.CHAT_PAUSED
    return False


def _offered(exchange: Exchange) -> bool:
    return bool(set(greeting.LEAD_IN_LABELS) & set(exchange.buttons))


async def _tap_lead_in(scenario: dict, label: str) -> tuple[Conversation, str]:
    """The scenario's opening until the offer shows, then a tap on `label`; its reply, or "" when no offer came."""
    c = await converse(scenario["style"], scenario["turns"], scenario.get("persona", ""), scenario["script"],
                       until=_offered)
    return c, (await _send(c, label)).reply if c.exchanges and _offered(c.exchanges[-1]) else ""


async def _lead_in_buttons(scenario: dict) -> tuple[list[Conversation], list[checks.Result]]:
    """The same opening three times, each tapping a different lead-in button once the offer shows."""
    conversations, replies = [], {}
    for label in greeting.LEAD_IN_LABELS:
        c, replies[label] = await _tap_lead_in(scenario, label)
        conversations.append(c)
    return conversations, [checks.lead_in_differs(replies)]


async def _isolation(scenario: dict) -> tuple[list[Conversation], list[checks.Result]]:
    """A first conversation full of details, then a second for the same person that must not know them."""
    first = await converse(scenario["style"], len(scenario["script"]), "", scenario["script"])
    async with pool.as_user(first.claims) as conn:
        second_thread = (await chat_turn.start_thread(conn, first.claims)).id
    second = await converse(scenario["style"], len(scenario["second_script"]), "", scenario["second_script"],
                            person=(first.claims, second_thread))
    return [first, second], [checks.isolation(second, scenario["isolation_details"])]


async def _after_past_pause(scenario: dict) -> tuple[list[Conversation], list[checks.Result]]:
    """A person whose pause, in an earlier conversation, has run out, then a new conversation for them: it must open
    and go on normally (R179). The pause is written directly, so the case does not depend on a model reaching one."""
    claims, paused_thread = await new_person("regress")
    async with pool.as_admin() as conn:
        await conn.execute("insert into public.chat_pauses (user_id, thread_id, started_at, ends_at, reason) "
                           "values ($1, $2, now() - interval '20 minutes', now() - interval '5 minutes', $3)",
                           uuid.UUID(claims.sub), paused_thread, scenario["pause_reason"])
    async with pool.as_user(claims) as conn:
        thread = (await chat_turn.start_thread(conn, claims)).id
    c = await converse(scenario["style"], len(scenario["script"]), "", scenario["script"], person=(claims, thread))
    return [c], [checks.no_past_pause(c)]


def _exchange_dict(e: Exchange, conversation: int) -> dict:
    keep = ("action", "framework", "stage", "safety", "paused", "refused", "question_cut", "latency_ms", "first_token_ms",
            "read_ms", "write_ms", "total_ms")
    return {"conversation": conversation, "said": e.said, "tapped": e.tapped, "reply": e.reply, "buttons": e.buttons,
            "trace": {k: e.trace[k] for k in keep if k in e.trace}, "seconds": round(e.seconds, 3), "paused": e.paused,
            "crisis": e.crisis}


def error_record(scenario: dict, error: Exception) -> dict:
    """A scenario that could not be played (a failed call of the person's or the judge's): a failure of its own that
    never ends the rest of the run."""
    result = checks.Result("ran_cleanly", checks.DETERMINISTIC, False, f"{type(error).__name__}: {error}"[:300],
                           critical=True)
    return {**_head(scenario), "checks": [result.as_dict()], "exchanges": [], "turns": []}


def gap_record(scenario: dict) -> dict:
    result = checks.Result("requirement_active", checks.GAP, False, scenario.get("gap_reason", ""))
    return {**_head(scenario), "status": "gap", "checks": [result.as_dict()], "exchanges": [], "turns": []}


def _head(scenario: dict) -> dict:
    return {"id": scenario["id"], "title": scenario["title"], "group": scenario["group"],
            "gap_reason": scenario.get("gap_reason"), "status": "run"}


async def play(scenario: dict, stages: dict[str, list[str]], names: dict[str, str], allowed: frozenset[str], *,
               judged: bool, http: httpx.AsyncClient) -> dict:
    setup = scenario.get("setup")
    if setup == "lead_in_buttons":
        conversations, extra = await _lead_in_buttons(scenario)
    elif setup == "lead_in_tap":
        # A label that is not a lead-in button is tapped as typed words, and stage_after_tap reports it never tapped.
        name = scenario["expect"]["stage_after_tap"]
        conversations, extra = [(await _tap_lead_in(scenario, checks.lead_in_label(name) or name))[0]], []
    elif setup == "isolation":
        conversations, extra = await _isolation(scenario)
    elif setup == "past_pause":
        conversations, extra = await _after_past_pause(scenario)
    else:
        conversations, extra = [await converse(scenario["style"], scenario["turns"], scenario.get("persona", ""),
                                               scenario["script"])], []
    main = conversations[0]
    results = checks.evaluate(main, scenario, stages, allowed, await _refused_after_pause(main), names) + extra
    for other in conversations[1:]:
        if other.error:
            results.append(checks.ran_cleanly(other))

    async with pool.as_admin() as conn:
        calls = await metrics.chat_calls(conn, [c.thread_id for c in conversations if c.thread_id])
    model_turns = sum(1 for c in conversations for e in c.exchanges if e.trace.get("latency_ms") is not None)

    verdict = None
    if judged:
        try:
            verdict = await judge(http, main, scenario)
        except Exception as error:  # noqa: BLE001 - a failed judge call is reported, never allowed to end the run
            verdict = {"error": f"{type(error).__name__}: {error}"}
    return {**_head(scenario),
            "checks": [r.as_dict() for r in results],
            "exchanges": [_exchange_dict(e, n) for n, c in enumerate(conversations, 1) for e in c.exchanges],
            "turns": [t for c in conversations for t in metrics.turn_figures(c)],
            "usage": metrics.usage(calls, model_turns),
            "judge": verdict}
