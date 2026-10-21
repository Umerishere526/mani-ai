# ABOUTME: Checks the framework registry: its closed set of ids, and where each framework finishes.
# ABOUTME: Nothing it does not recognise counts as a framework or as finished.

import pytest

from mani.chat.techniques import Registry
from mani.models.rows import Framework

REFRAMING = Framework(
    id="thought_reframing", name="Thought Reframing", summary="s", body="b",
    phases=["offering", "surface", "externalize", "explore", "land", "ground"],
)
ABCDE = Framework(
    id="abcde", name="ABCDE", summary="s", body="b",
    phases=["offering", "activate", "belief", "consequence", "dispute", "effect", "ground"],
)
# Ends somewhere other than "ground", which is what completion used to be detected by.
STOP = Framework(
    id="dbt_stop", name="DBT STOP", summary="s", body="b",
    phases=["offering", "stop", "step_back", "observe", "proceed"],
)


# What every seeded framework looks like: content stages, a closing, then the body route.
WITH_BODY_ROUTE = Framework(
    id="with_body_route", name="With body route", summary="s", body="b",
    phases=["offering", "one", "two", "three", "closing", "somatic_body", "somatic_practice"],
)


@pytest.fixture
def registry() -> Registry:
    return Registry([REFRAMING, ABCDE, STOP, WITH_BODY_ROUTE])


def test_registry_membership_is_the_closed_set(registry):
    assert "abcde" in registry
    assert "made_up" not in registry
    assert sorted(registry.ids) == ["abcde", "dbt_stop", "thought_reframing", "with_body_route"]
    assert len(registry) == 4


def test_the_last_phase_is_what_finishes_a_framework(registry):
    assert registry.is_final("thought_reframing", "ground")
    assert not registry.is_final("thought_reframing", "land")


def test_completion_is_a_position_not_a_phase_name(registry):
    """Matching a literal phase id recognises only the frameworks that happen to end on
    it, and makes any phase appended after it unreachable."""
    assert registry.is_final("dbt_stop", "proceed")
    assert not registry.is_final("dbt_stop", "ground")


def test_nothing_unrecognised_ever_counts_as_finished(registry):
    assert not registry.is_final("made_up", "ground")
    assert not registry.is_final("abcde", "made_up")
    assert not registry.is_final("abcde", None)
    assert not registry.is_final(None, "ground")
