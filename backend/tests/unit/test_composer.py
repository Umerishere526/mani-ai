# ABOUTME: Checks the system prompt's layer order and that a missing layer is not silent.
# ABOUTME: Order is fixed so the large static prefix stays identical and cacheable.

import time
import uuid

import pytest

from mani.chat.techniques import Registry
from mani.errors import ServiceError
from mani.models.rows import Framework, Profile, TechniqueTried, ThreadSummary
from mani.prompts import composer
from mani.prompts.cache import Config

USER = uuid.UUID("a0000000-0000-4000-8000-00000000000a")
THREAD = uuid.UUID("b0000000-0000-4000-8000-00000000000b")


def prompt(name: str, content: str):
    from mani.models.rows import Prompt

    return Prompt(id=uuid.uuid4(), name=name, content=content,
                  model_id="google/gemini-3-flash-preview")


@pytest.fixture
def config() -> Config:
    named = [
        prompt("mani_base", "IDENTITY"),
        prompt("response_format", "FORMAT"),
        prompt("title_generation", "TITLE"),
    ]
    return Config(
        prompts={p.name: p for p in named},
        registry=Registry([]),
        loaded_at=time.monotonic(),
    )


def test_the_layers_come_in_a_fixed_order(config):
    built = composer.compose(
        config,
        Profile(user_id=USER, nickname="Al", topics=["anxiety"], support_style="reflective"),
        should_generate_title=True,
        offered=["abcde"],
        summary=ThreadSummary(
            thread_id=THREAD, user_id=USER, summary="Talked about work.",
            techniques_tried=[TechniqueTried(name="abcde", helpful=True)],
        ),
    )
    assert [name for name, _ in built.layers] == [
        "mani_base", "response_format", "user_context", "title_generation",
        "techniques_used", "summary",
    ]


def test_optional_layers_are_simply_absent(config):
    built = composer.compose(config, None)
    assert [name for name, _ in built.layers] == ["mani_base", "response_format"]


def framework(id: str, name: str, indication: str, distinctions: dict) -> Framework:
    return Framework(
        id=id, name=name, summary="s", body="b", phases=["offering"],
        activation={"central_indication": indication, "distinctions": distinctions},
    )


def test_the_framework_index_is_built_from_the_registry_not_written_by_hand():
    """Every line of it already exists on admin.frameworks. A prose copy beside that is a
    second source of truth, and it drifts the first time somebody edits one and not the
    other - so adding a framework must need no prompt edit at all."""
    registry = Registry([
        framework("abcde", "ABCDE", "A specific event triggered a belief.",
                  {"thought_reframe": "Reframe when one thought is already clear."}),
        framework("dbt_stop", "DBT STOP", "The user is about to act.", {}),
    ])

    index = composer.framework_index(registry)

    assert "| ABCDE | `abcde` | A specific event triggered a belief. |" in index
    assert "| DBT STOP | `dbt_stop` | The user is about to act. |" in index
    # thought_reframe is not in this registry, so it falls back to a readable form of the
    # id rather than a display name it has no way to look up.
    assert "**ABCDE or thought reframe** — Reframe when one thought is already clear." in index


def test_a_distinction_written_from_both_sides_is_emitted_once():
    """Every framework file explains itself against its neighbours, so each pair is written
    twice across the set, and 'continue chatting instead' is written in all six. Correct in
    a file a clinician reads, pure waste in a prompt paid for on every turn."""
    registry = Registry([
        framework("abcde", "ABCDE", "An event and a belief.", {
            "thought_reframe": "ABCDE goes deeper.",
            "continued_conversation": "Keep talking when the issue is unclear.",
        }),
        framework("thought_reframe", "Thought Reframe", "One painful thought.", {
            "abcde": "Reframe is the shorter one.",
            "continued_conversation": "Keep talking when the thought is unclear.",
        }),
    ])

    index = composer.framework_index(registry)

    # The pair appears once, from whichever side was reached first - not twice.
    assert index.count("ABCDE or Thought Reframe") == 1
    assert "Thought Reframe or ABCDE" not in index
    assert index.count("continued conversation") == 1


def test_a_framework_index_with_nothing_to_list_is_left_out_entirely():
    """An empty registry is already logged as a misconfiguration at load. The prompt should
    not carry an empty table announcing frameworks that do not exist."""
    assert composer.framework_index(Registry([])) is None


def test_the_generated_index_reaches_the_composed_prompt(config):
    with_frameworks = Config(
        prompts=config.prompts,
        registry=Registry([framework("abcde", "ABCDE", "A specific event.", {})]),
        loaded_at=time.monotonic(),
    )
    built = composer.compose(with_frameworks, None)

    assert [name for name, _ in built.layers] == [
        "mani_base", "framework_index", "response_format"
    ]
    assert "`abcde`" in built.text


def test_onboarding_answers_reach_the_prompt(config):
    """The reference read only the nickname, so topics and support style shaped nothing."""
    built = composer.compose(
        config,
        Profile(user_id=USER, nickname="Al", topics=["burnout", "boundaries"],
                support_style="direct"),
    )
    assert "burnout, boundaries" in built.text
    assert "direct style of support" in built.text


def test_a_missing_required_layer_is_refused_not_dropped(config):
    """The reference pushed each layer only `if (prompt)`, so deactivating one in the
    portal quietly changed Mani's personality instead of failing."""
    without_format = Config(
        prompts={k: v for k, v in config.prompts.items() if k != "response_format"},
        registry=config.registry,
        loaded_at=config.loaded_at,
    )
    with pytest.raises(ServiceError):
        composer.compose(without_format, None)
