# ABOUTME: Latency, token, retry and cost figures for the regression suite: wall time per turn from the driver, and the
# ABOUTME: model's side, each call's billed cost included, from admin.llm_calls.

from __future__ import annotations

import math
import uuid

import asyncpg

from evals.drive import Conversation
from mani.db.llm_calls import Outcome


def percentile(values: list[float], p: float) -> float | None:
    """Nearest-rank percentile; None for no values."""
    if not values:
        return None
    ranked = sorted(values)
    return ranked[max(0, math.ceil(p / 100 * len(ranked)) - 1)]


def spread(values: list[float]) -> dict:
    return {"n": len(values), "p50": percentile(values, 50), "p95": percentile(values, 95),
            "p99": percentile(values, 99), "max": max(values) if values else None}


async def chat_calls(conn: asyncpg.Connection, thread_ids: list[uuid.UUID]) -> list[dict]:
    """Every chat attempt the threads made, a retry being its own row."""
    rows = await conn.fetch(
        "select message_id, model, latency_ms, input_tokens, output_tokens, cached_input_tokens, reasoning_tokens, "
        "outcome::text as outcome, cost_usd from admin.llm_calls "
        "where thread_id = any($1::uuid[]) and purpose = 'chat' order by created_at", thread_ids)
    return [dict(r) for r in rows]


def _seconds(ms: int | None) -> float | None:
    return round(ms / 1000, 3) if ms is not None else None


def turn_figures(conversation: Conversation) -> list[dict]:
    """Per answered turn: end-to-end seconds around runner.send, and from the trace the model's time, its wait for the
    first chunk and the read and write passes, each None when the trace does not carry it. `backend_s` is end to end
    less the model, which no single stage covers."""
    out = []
    for e in conversation.exchanges:
        model_ms = e.trace.get("latency_ms")
        out.append({"end_to_end_s": round(e.seconds, 3),
                    "model_s": _seconds(model_ms),
                    "backend_s": round(e.seconds - model_ms / 1000, 3) if model_ms is not None else None,
                    "first_token_s": _seconds(e.trace.get("first_token_ms")),
                    "read_s": _seconds(e.trace.get("read_ms")),
                    "write_s": _seconds(e.trace.get("write_ms"))})
    return out


def usage(calls: list[dict], model_turns: int) -> dict:
    """Tokens and retries across a scenario's chat calls; cost only when every call recorded one."""
    costs = [c["cost_usd"] for c in calls]
    total_cost = float(sum(costs)) if costs and all(c is not None for c in costs) else None
    return {
        "calls": len(calls),
        "retries": max(0, len(calls) - model_turns),
        "failed_calls": sum(1 for c in calls if c["outcome"] != Outcome.OK),
        "models": sorted({c["model"] for c in calls}),
        "input_tokens": sum(c["input_tokens"] for c in calls),
        "cached_input_tokens": sum(c["cached_input_tokens"] for c in calls),
        "output_tokens": sum(c["output_tokens"] for c in calls),
        "reasoning_tokens": sum(c["reasoning_tokens"] for c in calls),
        "cost_usd": total_cost,
        "cost_per_turn_usd": total_cost / model_turns if total_cost is not None and model_turns else None,
    }
