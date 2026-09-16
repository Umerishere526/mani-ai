# ABOUTME: Checks the system prompt's layer order and that a missing layer is not silent.
# ABOUTME: Order is fixed so the large static prefix stays identical and cacheable.

import time
import uuid

import pytest

from mani.chat.techniques import Registry
from mani.errors import ServiceError
from mani.models.rows import Profile, TechniqueTried, ThreadSummary
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
        prompt("techniques", "LIBRARY"),
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
        "mani_base", "techniques", "user_context", "title_generation",
        "techniques_used", "response_format", "summary",
    ]


def test_optional_layers_are_simply_absent(config):
    built = composer.compose(config, None)
    assert [name for name, _ in built.layers] == [
        "mani_base", "techniques", "response_format"
    ]


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
