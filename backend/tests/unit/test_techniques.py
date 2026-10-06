# ABOUTME: Checks the phase machine refuses what it cannot recognise.
# ABOUTME: The implementation this replaces returned valid for anything unknown.

import pytest

from mani.chat.techniques import OFFERING, Registry, Verdict, moves_on_after
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


# Ends the way every seeded framework does: the body check follows the last stage.
BODY_CHECKED = Framework(
    id="staged", name="Staged", summary="s", body="b",
    phases=["offering", "activate", "belief", "closing", "somatic_checkin", "somatic_practice"],
)


@pytest.fixture
def registry() -> Registry:
    return Registry([REFRAMING, ABCDE, STOP])


@pytest.fixture
def body_checked() -> Registry:
    return Registry([BODY_CHECKED])


def test_the_opening_move_is_offering(registry):
    assert registry.validate_transition("thought_reframing", None, OFFERING).ok


def test_one_step_forward_is_allowed(registry):
    assert registry.validate_transition("thought_reframing", "offering", "surface").ok


def test_holding_on_a_phase_is_allowed(registry):
    # A person may need more than one turn in the same place.
    assert registry.validate_transition("thought_reframing", "surface", "surface").ok


def test_stepping_back_is_allowed(registry):
    assert registry.validate_transition("thought_reframing", "explore", "surface").ok


def test_moving_past_steps_already_answered_is_allowed(registry):
    """The model judges when a step is done, so it may move forward past steps the person has
    already answered (spec 0010, AC-5)."""
    assert registry.validate_transition("thought_reframing", "offering", "explore").ok


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
    # A framework that has not started is corrected to its offering, not another paid call;
    # a step forward past answered ones is kept.
    assert registry.clamp("thought_reframing", "offering", "explore") == "explore"
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


@pytest.mark.parametrize(
    "phase,moves_on",
    [
        (None, False),
        ("offering", False),
        ("activate", True),
        ("belief", True),
        ("closing", True),
        ("somatic_checkin", False),
        ("somatic_practice", False),
        ("a_stage_since_renamed", False),
    ],
)
def test_a_reply_is_answered_by_the_next_stage_from_the_first_stage_to_the_last_before_the_body_check(
    phase, moves_on
):
    assert moves_on_after(BODY_CHECKED, phase) is moves_on


def test_nothing_moves_on_in_a_framework_that_is_not_there():
    assert not moves_on_after(None, "belief")


def test_a_turn_that_moves_on_may_hold_or_go_forward_one_stage(body_checked):
    assert body_checked.validate_transition("staged", "belief", "belief", moving_on=True).ok
    assert body_checked.validate_transition("staged", "belief", "closing", moving_on=True).ok


def test_a_turn_that_moves_on_never_asks_a_stage_again(body_checked):
    went_back = body_checked.validate_transition("staged", "belief", "activate", moving_on=True)
    assert went_back.verdict is Verdict.STEPPED_BACK
    assert went_back.expected_next == "closing"
    assert body_checked.clamp("staged", "belief", "activate", moving_on=True) == "closing"
    assert body_checked.clamp("staged", "belief", OFFERING, moving_on=True) == "closing"


def test_a_turn_that_moves_on_records_the_next_stage_for_one_the_framework_does_not_have(body_checked):
    unknown = body_checked.validate_transition("staged", "belief", "examine", moving_on=True)
    assert unknown.verdict is Verdict.UNKNOWN_PHASE
    assert body_checked.clamp("staged", "belief", "examine", moving_on=True) == "closing"
    assert body_checked.clamp("staged", "belief", "examine") is None


def test_a_turn_that_moves_on_may_pass_a_stage_but_never_past_the_body_check_in(body_checked):
    assert body_checked.clamp("staged", "activate", "closing", moving_on=True) == "closing"
    assert body_checked.validate_transition("staged", "activate", "somatic_checkin", moving_on=True).ok
    past = body_checked.validate_transition("staged", "belief", "somatic_practice", moving_on=True)
    assert past.verdict is Verdict.PAST_THE_CHECK_IN
    assert body_checked.clamp("staged", "belief", "somatic_practice", moving_on=True) == "somatic_checkin"
    # The practice after the check in belongs to the body route.
    assert body_checked.validate_transition("staged", "somatic_checkin", "somatic_practice").ok
