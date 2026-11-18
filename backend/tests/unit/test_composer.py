# ABOUTME: Checks what a turn's system prompt says about the person (onboarding, memory, the summary) and that the
# ABOUTME: model, effort and hosts come from the prompt row, with a missing row refused rather than skipped.

import time
import uuid

import pytest

from mani.chat.techniques import Registry
from mani.config import get_settings
from mani.errors import ServiceError
from mani.models.rows import Profile, Prompt, TechniqueTried, ThreadSummary
from mani.prompts import composer
from mani.prompts.cache import Config

USER = uuid.UUID("a0000000-0000-4000-8000-00000000000a")
THREAD = uuid.UUID("b0000000-0000-4000-8000-00000000000b")


def config(*prompts: Prompt) -> Config:
    return Config(prompts={p.name: p for p in prompts}, registry=Registry([]), loaded_at=time.monotonic())


def test_onboarding_answers_reach_the_prompt_but_the_style_does_not():
    """The style is resolved per turn from the conversation first, so the profile's answer is left out here rather
    than contradicting a conversation that chose differently."""
    said = composer.user_context(
        Profile(user_id=USER, nickname="Al", topics=["burnout", "boundaries"], support_style="directive"))
    assert '"Al"' in said and "burnout, boundaries" in said
    assert "directive" not in said.lower()
    assert composer.user_context(Profile(user_id=USER)) is None
    assert composer.user_context(None) is None


def test_the_summary_carries_what_was_tried_and_whether_it_helped():
    summary = composer.summary_layer(ThreadSummary(
        thread_id=THREAD, user_id=USER, summary="Talked about work.",
        techniques_tried=[TechniqueTried(name="abcde", helpful=True)],
    ))
    assert "Talked about work." in summary and "abcde (helpful)" in summary
    assert composer.summary_layer(None) is None


def test_the_model_effort_and_hosts_come_from_the_prompt_row():
    routing = {"only": ["fireworks"], "zdr": True}
    row = Prompt(id=uuid.uuid4(), name="mani", content="MANI", model_id="minimax/minimax-m3.1-flash",
                 model_parameters={"reasoning_effort": "low"}, routing=routing)
    assert composer.model_settings(config(row), "mani") == (
        "minimax/minimax-m3.1-flash", {"reasoning_effort": "low"}, routing)
    unnamed = row.model_copy(update={"model_id": None})
    assert composer.model_settings(config(unnamed), "mani")[0] == get_settings().default_chat_model


def test_a_missing_prompt_row_is_refused_not_skipped():
    """Deactivating the row in the portal must fail the turn, not quietly change Mani."""
    with pytest.raises(ServiceError):
        composer.model_settings(config(), "mani")
