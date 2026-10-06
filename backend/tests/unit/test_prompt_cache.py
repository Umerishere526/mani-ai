# ABOUTME: Checks what the prompt cache refuses at load, so a bad setting never reaches a turn.
# ABOUTME: Pure checks on prompt rows; nothing here needs a database.

import uuid

import pytest

from mani.errors import ErrorCategory, ServiceError
from mani.models.rows import Prompt
from mani.prompts import cache


def prompt(name: str = "mani_base", **parameters) -> Prompt:
    return Prompt(id=uuid.uuid4(), name=name, content="c", model_parameters=parameters)


@pytest.mark.parametrize("effort", ["low", "medium", "high"])
def test_the_efforts_the_provider_understands_are_accepted(effort):
    cache.refuse_unknown_reasoning_efforts([prompt(reasoning_effort=effort)])


def test_a_prompt_with_no_effort_is_accepted():
    cache.refuse_unknown_reasoning_efforts([prompt(temperature=1)])


@pytest.mark.parametrize("effort", ["max", "LOW", "", "none", 3])
def test_any_other_effort_is_refused_by_name_before_a_turn_uses_it(effort):
    """covers spec 0006 AC-1: a misspelt effort would reach OpenRouter on every reply."""
    with pytest.raises(ServiceError) as refused:
        cache.refuse_unknown_reasoning_efforts([prompt("summarization", reasoning_effort=effort)])
    assert refused.value.category is ErrorCategory.CONFIG_ERROR
    assert "summarization" in str(refused.value)
