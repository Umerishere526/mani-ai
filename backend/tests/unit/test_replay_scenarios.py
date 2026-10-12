# ABOUTME: Checks every replay scenario is well formed before anyone spends a model call on it.
# ABOUTME: A bad pattern or a missing field would otherwise fail only in the middle of a paid run.

import json
import pathlib
import re

import pytest

SCENARIOS = json.loads(
    (pathlib.Path(__file__).parents[2] / "scripts" / "replay_scenarios.json").read_text()
)


@pytest.mark.parametrize("name", SCENARIOS)
def test_a_scenario_has_what_a_replay_needs(name):
    scenario = SCENARIOS[name]
    for key in ("about", "style", "history", "message"):
        assert scenario[key], f"{name} has no {key}"
    assert scenario["style"] in ("direct", "supportive", "reflective")
    assert all(entry["role"] in ("user", "mani") and entry["content"] for entry in scenario["history"])
    # A framework in progress needs the stage it is on.
    assert bool(scenario.get("framework")) == bool(scenario.get("phase"))
    for pattern in scenario.get("flags", {}).values():
        re.compile(pattern)
