# ABOUTME: Checks the phase machine refuses what it cannot recognise.
# ABOUTME: The implementation this replaces returned valid for anything unknown.

import pytest

from mani.chat.techniques import OFFERING, Registry, Verdict
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


@pytest.fixture
def registry() -> Registry:
    return Registry([REFRAMING, ABCDE, STOP])


def test_the_opening_move_is_offering(registry):
    assert registry.validate_transition("thought_reframing", None, OFFERING).ok


def test_one_step_forward_is_allowed(registry):
    assert registry.validate_transition("thought_reframing", "offering", "surface").ok


def test_holding_on_a_phase_is_allowed(registry):
    # A person may need more than one turn in the same place.
    assert registry.validate_transition("thought_reframing", "surface", "surface").ok


def test_stepping_back_is_allowed(registry):
    assert registry.validate_transition("thought_reframing", "explore", "surface").ok


def test_jumping_ahead_is_refused_and_names_what_was_skipped(registry):
    t = registry.validate_transition("thought_reframing", "offering", "explore")
    assert not t.ok
    assert t.verdict is Verdict.SKIPPED_PHASES
    assert t.skipped == ["surface", "externalize"]
    assert t.expected_next == "surface"


def test_starting_mid_technique_is_refused(registry):
    t = registry.validate_transition("thought_reframing", None, "explore")
    assert t.verdict is Verdict.MISSING_OFFERING
    assert t.expected_next == OFFERING


# The two that were backwards. Both previously returned valid, which meant one
# hallucinated identifier disabled the guard and was then written to the database.

def test_an_unknown_framework_fails_closed(registry):
    t = registry.validate_transition("somatic_breathing", "offering", "surface")
    assert not t.ok
    assert t.verdict is Verdict.UNKNOWN_FRAMEWORK


def test_an_unknown_phase_fails_closed(registry):
    t = registry.validate_transition("thought_reframing", "offering", "vibing")
    assert not t.ok
    assert t.verdict is Verdict.UNKNOWN_PHASE


@pytest.mark.parametrize("attack", ["constructor", "__class__", "toString", "valueOf"])
def test_prototype_style_keys_are_just_unknown(registry, attack):
    """In JavaScript these returned a truthy non-array and crashed on .indexOf."""
    assert registry.validate_transition(attack, None, OFFERING).verdict is Verdict.UNKNOWN_FRAMEWORK
    assert registry.validate_transition("abcde", None, attack).verdict is Verdict.UNKNOWN_PHASE


def test_phases_belong_to_their_own_framework(registry):
    # 'belief' is an ABCDE phase; thought_reframing must not accept it.
    assert registry.validate_transition("thought_reframing", "offering", "belief").verdict \
        is Verdict.UNKNOWN_PHASE
    assert registry.validate_transition("abcde", "activate", "belief").ok


def test_clamp_corrects_instead_of_discarding_the_turn(registry):
    # A skip is worth a corrected field, not another paid model call.
    assert registry.clamp("thought_reframing", "offering", "explore") == "surface"
    assert registry.clamp("thought_reframing", None, "explore") == OFFERING
    assert registry.clamp("thought_reframing", "offering", "surface") == "surface"


def test_clamp_records_nothing_when_nothing_is_trustworthy(registry):
    assert registry.clamp("made_up", "offering", "surface") is None
    assert registry.clamp("abcde", "activate", "made_up") is None


def test_registry_membership_is_the_closed_set(registry):
    assert "abcde" in registry
    assert "made_up" not in registry
    assert sorted(registry.ids) == ["abcde", "dbt_stop", "thought_reframing"]
    assert len(registry) == 3


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
