# ABOUTME: Lets an eval run try another model in its own process, on a route that keeps no data.
# ABOUTME: Also prices a run's calls from admin.llm_calls, so the cost of a model is measured.

from __future__ import annotations

import pathlib
import subprocess
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from mani.db import pool
from mani.prompts import composer
from mani.prompts.cache import Config


@dataclass(frozen=True)
class Prices:
    """Dollars per million tokens. Cached input is inside the input count and priced apart."""

    input: float
    cached_input: float
    output: float


@dataclass(frozen=True)
class Trial:
    """One model to try, and the route it must be served on."""

    model: str
    provider: str
    reasoning_effort: str | None = None
    max_tokens: int | None = None
    exercise_max_tokens: int | None = None
    prices: Prices | None = None


def from_flags(
    *,
    model: str | None,
    provider: str | None,
    reasoning_effort: str | None = None,
    max_tokens: int | None = None,
    exercise_max_tokens: int | None = None,
    prices: Prices | None = None,
) -> Trial | None:
    """The trial the command line asks for, or None when it asks for none.

    A model with no named provider is refused: it would be served from the default tier,
    which keeps no promise about the data in a conversation.
    """
    if model is None:
        return None
    if not provider:
        raise ValueError("a model to try needs a provider (--provider), to pin where it is served")
    return Trial(model, provider, reasoning_effort, max_tokens, exercise_max_tokens, prices)


def routing_for(trial: Trial) -> dict[str, Any]:
    """Pinned to one endpoint, no fallback, zero data retention, and an endpoint that cannot
    honour the structured reply or the reasoning is refused rather than ignored. There is no
    way to turn zero retention off."""
    return {
        "order": [trial.provider],
        "allow_fallbacks": False,
        "zdr": True,
        "require_parameters": True,
    }


def override_for(
    trial: Trial, original: Callable[[Config], tuple[str, dict, dict]] | None = None
) -> Callable[[Config], tuple[str, dict, dict]]:
    """A replacement for `composer.model_settings` that returns the trial's model, parameters
    and route. The loaded prompt row is read through `original`, never changed."""
    original = original or composer.model_settings

    def settings(config: Config) -> tuple[str, dict, dict]:
        _, parameters, _ = original(config)
        parameters = dict(parameters)
        for key, value in (
            ("reasoning_effort", trial.reasoning_effort),
            ("maxTokens", trial.max_tokens),
            ("exerciseMaxTokens", trial.exercise_max_tokens),
        ):
            if value is not None:
                parameters[key] = value
        return trial.model, parameters, routing_for(trial)

    return settings


def install(trial: Trial) -> Callable[[], None]:
    """Make this process's chat, title and exercise calls use the trial; returns the undo.
    Nothing outside this process changes: not the database, not the seeded prompts."""
    original = composer.model_settings
    composer.model_settings = override_for(trial, original)

    def restore() -> None:
        composer.model_settings = original

    return restore


def cost_dollars(input_tokens: int, cached_tokens: int, output_tokens: int, prices: Prices) -> float:
    """Cached tokens are counted inside the input, so they are taken out of it first. Reasoning
    tokens are inside the output and are not reported apart."""
    return (
        (input_tokens - cached_tokens) * prices.input
        + cached_tokens * prices.cached_input
        + output_tokens * prices.output
    ) / 1_000_000


@dataclass(frozen=True)
class Summary:
    calls: int
    schema_failures: int
    cost: float | None
    lines: list[str] = field(default_factory=list)


def summarise(rows: Iterable[Mapping[str, Any]], trial: Trial | None) -> Summary:
    """One conversation's calls, grouped as admin.llm_calls holds them. Only the trial model's
    own calls are priced; another model's calls (a summary, a memory fold) are listed apart."""
    rows = list(rows)
    lines: list[str] = []
    priced = (0, 0, 0)
    for row in rows:
        mine = trial is not None and row["model"] == trial.model
        lines.append(
            f"    {row['purpose']:<16} {row['outcome']:<15} x{row['calls']:<3} "
            f"in {row['input']:>7} (cached {row['cached']:>7}) out {row['output']:>6}  {row['model']}"
        )
        if mine:
            priced = (priced[0] + row["input"], priced[1] + row["cached"], priced[2] + row["output"])
    cost = None
    if trial is not None and trial.prices is not None:
        cost = cost_dollars(*priced, trial.prices)
        lines.append(f"    cost of the {trial.model} calls: ${cost:.4f}")
    return Summary(
        calls=sum(r["calls"] for r in rows),
        schema_failures=sum(r["calls"] for r in rows if r["outcome"] == "schema_invalid"),
        cost=cost,
        lines=lines,
    )


FIGURES_SQL = """
    select purpose, model, outcome, count(*)::int as calls,
           coalesce(sum(input_tokens), 0)::bigint as input,
           coalesce(sum(cached_input_tokens), 0)::bigint as cached,
           coalesce(sum(output_tokens), 0)::bigint as output
      from admin.llm_calls
     where user_id = $1
     group by purpose, model, outcome
     order by purpose, model, outcome
"""


async def figures_for(user_id: str, trial: Trial | None) -> Summary:
    """What one run's user cost, read from admin.llm_calls before the run removes them."""
    async with pool.as_admin() as conn:
        rows = await conn.fetch(FIGURES_SQL, user_id)
    return summarise([dict(r) for r in rows], trial)


def header(trial: Trial | None, instructions: Mapping[str, str]) -> list[str]:
    """What this run used, printed first so a transcript says what produced it."""
    lines = [
        f"instructions: commit {instructions.get('git_commit', '?')}"
        f"{' plus uncommitted changes' if instructions.get('git_dirty') == 'yes' else ''}, "
        f"mani_base md5 {instructions.get('mani_base_md5', '?')}, "
        f"seeded model {instructions.get('model', '?')}",
    ]
    if trial is None:
        lines.append("model: as seeded")
        return lines
    routing = routing_for(trial)
    lines += [
        f"model: {trial.model} (this process only)",
        f"reasoning effort: {trial.reasoning_effort or 'not sent'}, "
        f"max tokens: {trial.max_tokens or 'as seeded'}, "
        f"exercise pick max tokens: {trial.exercise_max_tokens or 'as seeded'}",
        f"route: {', '.join(f'{k}={v}' for k, v in routing.items())}",
    ]
    return lines


async def instructions_in_force() -> dict[str, str]:
    """The seeded mani_base's model, version and a digest of its text, and the git commit."""
    async with pool.as_admin() as conn:
        base = await conn.fetchrow(
            "select model_id, version, md5(content) as digest from admin.prompts where name = 'mani_base'"
        )
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=False,
        cwd=pathlib.Path(__file__).parent,
    ).stdout.strip()
    uncommitted = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True, check=False,
        cwd=pathlib.Path(__file__).parent,
    ).stdout.strip()
    return {
        "model": base["model_id"], "mani_base_version": str(base["version"]),
        "mani_base_md5": base["digest"], "git_commit": commit,
        "git_dirty": "yes" if uncommitted else "no",
    }
