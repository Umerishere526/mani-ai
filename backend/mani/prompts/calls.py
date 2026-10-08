# ABOUTME: Names the prompt rows that are model calls, and checks each names its thinking level.
# ABOUTME: Seed, the admin writes and every call site share this one check, so none can drift.

from __future__ import annotations

import typing

from mani.errors import ErrorCategory, ServiceError
from mani.llm.chain import ReasoningEffort
from mani.models.rows import Prompt

# Every prompt row a model call is made from. Each must name its own thinking level: the level
# is the biggest lever on what a call costs, so it is a choice made per call, never a default.
# A layer row (response_format, title_generation) is text added to another call's prompt and
# runs at that call's level, so it is not listed.
CALL_PROMPTS = frozenset(
    {"mani_base", "summarization", "memory_fold", "exercise_select", "voice_translation"}
)

EFFORTS: tuple[str, ...] = typing.get_args(ReasoningEffort)


def _level_problem(model_parameters: object) -> str | None:
    """Why these parameters name no usable level, or None when they do. Never raises."""
    if not isinstance(model_parameters, dict):
        return "model_parameters is not an object holding reasoning_effort"
    effort = model_parameters.get("reasoning_effort")
    if effort is None:
        return "model_parameters has no reasoning_effort"
    if not isinstance(effort, str) or effort not in EFFORTS:
        return f"reasoning_effort {effort!r} is not one of {', '.join(EFFORTS)}"
    return None


def effort_problem(name: str, model_parameters: object) -> str | None:
    """Why a row of this name may not be stored with these parameters, or None when it may.

    Never raises, so bad input from the portal is a refused request rather than a crash.
    """
    if name not in CALL_PROMPTS:
        return None
    problem = _level_problem(model_parameters)
    return None if problem is None else f"{name}: {problem}"


def effort_for(prompt: Prompt, name: str) -> ReasoningEffort:
    """The thinking level a call made from this row is sent.

    Raised as a config error before any request goes out, so a row that lost its level costs
    that one call and no tokens, rather than running at a level nobody chose.
    """
    problem = _level_problem(prompt.model_parameters)
    if problem is not None:
        raise ServiceError(
            f"prompt {name!r} cannot be called: {problem}",
            ErrorCategory.CONFIG_ERROR,
            user_message="Mani is not available right now.",
        )
    return prompt.model_parameters["reasoning_effort"]
