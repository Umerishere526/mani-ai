# ABOUTME: Checks the phase machine refuses what it cannot recognise.
# ABOUTME: The implementation this replaces returned valid for anything unknown.

import pytest

from mani.chat.techniques import ENDING_PHASES, OFFERING, Registry, Verdict
from mani.models.rows import Framework, LedgerEntry, StageStatus

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


WITH_ENDING = Framework(
    id="abcde", name="ABCDE", summary="s", body="b",
    phases=["offering", "activate", "closing", *ENDING_PHASES],
)


@pytest.fixture
def ending_registry() -> Registry:
    return Registry([WITH_ENDING, REFRAMING])


@pytest.mark.parametrize("phase", ["closing", "somatic_checkin", "somatic_practice"])
def test_the_ending_opens_on_the_last_own_phase_and_stays_open_through_the_ending(ending_registry, phase):
    assert ending_registry.ending_open("abcde", phase)


@pytest.mark.parametrize("phase", ["offering", "activate", "made_up", None])
def test_a_phase_before_the_ending_cannot_end_the_framework(ending_registry, phase):
    assert not ending_registry.ending_open("abcde", phase)


def test_an_unknown_framework_has_no_ending_to_open(ending_registry):
    assert not ending_registry.ending_open("made_up", "closing")
    assert not ending_registry.ending_open(None, "closing")


def test_a_framework_seeded_without_the_ending_phases_cannot_be_ended_early(ending_registry):
    """A database not yet reseeded: its last phase is not an ending, so nothing opens."""
    assert not ending_registry.ending_open("thought_reframing", "ground")


def test_a_veto_list_a_portal_edit_broke_is_ignored_with_one_error_naming_no_phrase(caplog):
    """The portal skips the seed's checks: a blank phrase would rule a framework out by a space."""
    broken = ABCDE.model_copy(update={"activation": {"never_offer_when_said": ["died", " "]}})
    kept = STOP.model_copy(update={"activation": {"never_offer_when_said": ["funeral"]}})
    text = REFRAMING.model_copy(update={"activation": {"never_offer_when_said": "died"}})
    with caplog.at_level("ERROR", logger="mani.chat.techniques"):
        registry = Registry([broken, kept, text, STOP.model_copy(update={"id": "none", "activation": {}})])

    assert registry.vetoes == {"dbt_stop": ["funeral"]}
    assert [rec.getMessage() for rec in caplog.records] == [
        "framework abcde: never_offer_when_said is not a list of non empty strings, ignored",
        "framework thought_reframing: never_offer_when_said is not a list of non empty strings, ignored",
    ]


# Shaped as the seed writes ABCDE: its own stages, `closing` as the last own phase, then the ending.
SEEDED_ABCDE = Framework(
    id="abcde", name="ABCDE", summary="s", body="b",
    phases=["offering", "activate", "belief", "consequence", "examine", "balanced", "closing", *ENDING_PHASES],
)


def entry(status: StageStatus, turns: int = 0) -> LedgerEntry:
    return LedgerEntry(status=status, turns=turns)


def test_the_ledger_tracks_the_stages_between_the_offer_and_the_last_own_phase():
    registry = Registry([SEEDED_ABCDE])
    assert registry.ledger_stages("abcde") == ["activate", "belief", "consequence", "examine", "balanced"]
    assert registry.ledger_stages("somatic_breathing") == []
    assert registry.ledger_stages(None) == []


def test_a_framework_seeded_without_the_ending_ends_its_own_stages_on_its_last_phase(registry):
    assert registry.ledger_stages("dbt_stop") == ["stop", "step_back", "observe"]
    assert registry.stage_from_ledger("dbt_stop", {}) == "stop"
    done = {s: entry(StageStatus.KNOWN) for s in ("stop", "step_back", "observe")}
    assert registry.stage_from_ledger("dbt_stop", done) == "proceed"


def test_the_stage_asked_is_the_first_one_not_known():
    registry = Registry([SEEDED_ABCDE])
    known = entry(StageStatus.KNOWN)
    assert registry.stage_from_ledger("abcde", {}) == "activate"
    assert registry.stage_from_ledger("abcde", {"activate": known, "belief": known, "consequence": known}) == "examine"
    # A stage with nothing yet, or only part, is still the one to ask, whatever follows it.
    assert registry.stage_from_ledger("abcde", {"activate": known, "belief": entry(StageStatus.PARTIAL), "consequence": known}) == "belief"
    assert registry.stage_from_ledger("abcde", {"belief": known}) == "activate"


def test_every_stage_known_or_passed_is_the_last_own_phase():
    registry = Registry([SEEDED_ABCDE])
    ledger = {s: entry(StageStatus.KNOWN) for s in registry.ledger_stages("abcde")}
    ledger["examine"] = entry(StageStatus.PASSED, turns=4)
    assert registry.stage_from_ledger("abcde", ledger) == "closing"


def test_an_unknown_framework_has_no_stage_to_ask(registry):
    assert registry.stage_from_ledger("somatic_breathing", {}) is None
