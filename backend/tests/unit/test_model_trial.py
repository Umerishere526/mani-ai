# ABOUTME: Checks the model trial helper: the route it pins, what it overrides, and the cost it reports.
# ABOUTME: Pure logic over fake rows and a fake prompt config; no model is called.

import time
import uuid

import pytest

from mani.config import Settings
from mani.models.rows import Prompt
from mani.prompts import composer
from mani.prompts.cache import Config
from mani.chat.techniques import Registry
from scripts import model_trial
from scripts.model_trial import Prices, Trial

PRICES = Prices(input=0.75, cached_input=0.075, output=3.75)


def trial(**changes) -> Trial:
    base = dict(
        model="google/gemini-3.8-flash", provider="google-vertex/global",
        reasoning_effort="low", max_tokens=4096, exercise_max_tokens=1024, prices=PRICES,
    )
    return Trial(**{**base, **changes})


def config() -> Config:
    base = Prompt(
        id=uuid.uuid4(), name="mani_base", content="c", model_id="google/gemini-3.1-flash-lite",
        model_parameters={"temperature": 1}, routing={},
    )
    return Config(prompts={"mani_base": base}, registry=Registry([]), loaded_at=time.monotonic())


def test_the_route_is_pinned_to_one_endpoint_that_keeps_nothing_and_refuses_no_fallback():
    """covers spec 0006 AC-3, AC-4: a refusal stops the run, it never falls back."""
    routing = model_trial.routing_for(trial())
    assert routing == {
        "order": ["google-vertex/global"], "allow_fallbacks": False,
        "zdr": True, "require_parameters": True,
    }
    # Merged over the settings, the rule against training use stays.
    merged = Settings(
        database_url="postgresql://localhost/none", supabase_url="https://x.supabase.co",
        supabase_jwt_secret="s",
    ).routing(routing)
    assert merged["data_collection"] == "deny"


def test_a_model_without_a_provider_is_refused():
    """The flag that would send a health conversation to the default tier is not allowed."""
    with pytest.raises(ValueError, match="provider"):
        model_trial.from_flags(model="m", provider=None)


def test_no_model_means_no_trial():
    assert model_trial.from_flags(model=None, provider=None) is None


def test_the_override_replaces_the_model_effort_room_and_route_and_keeps_the_rest():
    original = config()
    model, parameters, routing = model_trial.override_for(trial())(original)
    assert model == "google/gemini-3.8-flash"
    assert parameters == {
        "temperature": 1, "reasoning_effort": "low", "maxTokens": 4096, "exerciseMaxTokens": 1024,
    }
    assert routing["order"] == ["google-vertex/global"] and routing["zdr"] is True
    # The loaded row itself is untouched.
    row = original.prompts["mani_base"]
    assert row.model_id == "google/gemini-3.1-flash-lite"
    assert row.model_parameters == {"temperature": 1} and row.routing == {}


def test_an_unset_effort_or_room_is_not_added():
    _, parameters, _ = model_trial.override_for(trial(
        reasoning_effort=None, max_tokens=None, exercise_max_tokens=None
    ))(config())
    assert parameters == {"temperature": 1}


def test_installing_the_override_changes_composer_for_this_process_and_can_be_undone(monkeypatch):
    original = composer.model_settings
    restore = model_trial.install(trial())
    try:
        assert composer.model_settings(config())[0] == "google/gemini-3.8-flash"
    finally:
        restore()
    assert composer.model_settings is original


def test_cost_counts_cached_input_once_at_its_own_price():
    """Cached tokens are inside the input count, so they are taken out of it first."""
    # 1,000,000 input of which 600,000 cached, 100,000 output.
    cost = model_trial.cost_dollars(1_000_000, 600_000, 100_000, PRICES)
    assert cost == pytest.approx(0.4 * 0.75 + 0.6 * 0.075 + 0.1 * 3.75)


def test_figures_price_only_the_trial_model_and_count_schema_failures():
    rows = [
        {"purpose": "chat", "model": "google/gemini-3.8-flash", "outcome": "ok",
         "calls": 9, "input": 90_000, "cached": 40_000, "output": 6_000},
        {"purpose": "chat", "model": "google/gemini-3.8-flash", "outcome": "schema_invalid",
         "calls": 2, "input": 18_000, "cached": 0, "output": 4_096},
        {"purpose": "memory_fold", "model": "google/gemini-3.1-flash-lite", "outcome": "ok",
         "calls": 1, "input": 5_000, "cached": 0, "output": 300},
    ]
    summary = model_trial.summarise(rows, trial())
    assert summary.calls == 12
    assert summary.schema_failures == 2
    expected = model_trial.cost_dollars(108_000, 40_000, 10_096, PRICES)
    assert summary.cost == pytest.approx(expected)
    assert "memory_fold" in "\n".join(summary.lines)


def test_figures_without_prices_report_tokens_and_no_cost():
    rows = [{"purpose": "chat", "model": "m", "outcome": "ok", "calls": 1,
             "input": 10, "cached": 0, "output": 5}]
    summary = model_trial.summarise(rows, trial(prices=None))
    assert summary.cost is None
    assert "cost" not in "\n".join(summary.lines).lower()


def test_the_header_says_when_the_commit_is_not_all_that_was_measured():
    base = {"git_commit": "abc123", "mani_base_md5": "d41d8"}
    assert "uncommitted" in "\n".join(model_trial.header(None, {**base, "git_dirty": "yes"}))
    assert "uncommitted" not in "\n".join(model_trial.header(None, {**base, "git_dirty": "no"}))


def test_the_header_names_everything_the_run_used():
    lines = "\n".join(model_trial.header(trial(), {"git_commit": "abc123", "mani_base_md5": "d41d8"}))
    for expected in (
        "google/gemini-3.8-flash", "low", "4096", "1024", "google-vertex/global",
        "zdr", "abc123", "d41d8",
    ):
        assert expected in lines
