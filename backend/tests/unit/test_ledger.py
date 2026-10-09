# ABOUTME: Checks a running framework's stage ledger: reported statuses, one more turn each, passed at the cap.
# ABOUTME: Plain ledgers in and out, no database; the orchestrator's use of it is in tests/integration.

from mani.chat import ledger
from mani.models.rows import LedgerEntry, StageStatus

CAP = 4


def test_a_stage_still_not_known_at_the_cap_is_passed_and_noted():
    notes: list[str] = []
    stored = {"activating_event": LedgerEntry(status=StageStatus.KNOWN), "belief": LedgerEntry(status=StageStatus.PARTIAL, turns=2)}

    once = ledger.counted(stored, "belief", CAP, notes)
    assert once["belief"] == LedgerEntry(status=StageStatus.PARTIAL, turns=3)
    assert notes == []

    capped = ledger.counted(once, "belief", CAP, notes)
    assert capped["belief"] == LedgerEntry(status=StageStatus.PASSED, turns=4)
    assert capped["activating_event"] == stored["activating_event"]
    assert notes == ["passed by the cap: belief"]


def test_a_stage_with_no_entry_starts_counting_from_missing():
    assert ledger.counted({}, "dispute", CAP, []) == {"dispute": LedgerEntry(status=StageStatus.MISSING, turns=1)}


def test_a_known_or_passed_stage_keeps_its_status_past_the_cap():
    notes: list[str] = []
    stored = {
        "belief": LedgerEntry(status=StageStatus.KNOWN, turns=3),
        "dispute": LedgerEntry(status=StageStatus.PASSED, turns=4),
    }

    counted = ledger.counted(ledger.counted(stored, "belief", CAP, notes), "dispute", CAP, notes)

    assert counted == {
        "belief": LedgerEntry(status=StageStatus.KNOWN, turns=4),
        "dispute": LedgerEntry(status=StageStatus.PASSED, turns=5),
    }
    assert notes == []


def test_a_passed_stage_a_later_reply_reports_known_is_known_and_keeps_its_count():
    notes: list[str] = []
    stored = {"consequences": LedgerEntry(status=StageStatus.PASSED, turns=4)}

    updated = ledger.with_reported(stored, {"consequences": StageStatus.KNOWN}, CAP, notes)

    assert updated == {"consequences": LedgerEntry(status=StageStatus.KNOWN, turns=4)}
    assert notes == []


def test_a_passed_stage_reported_anything_short_of_known_stays_passed():
    stored = {"consequences": LedgerEntry(status=StageStatus.PASSED, turns=4)}

    for status in (StageStatus.MISSING, StageStatus.PARTIAL):
        assert ledger.with_reported(stored, {"consequences": status}, CAP, []) == stored


def test_a_stage_at_the_cap_is_never_moved_back_so_no_stage_is_asked_past_it():
    notes: list[str] = []
    stored = {
        "belief": LedgerEntry(status=StageStatus.KNOWN, turns=1),
        "consequences": LedgerEntry(status=StageStatus.KNOWN, turns=4),
    }

    updated = ledger.with_reported(
        stored, {"belief": StageStatus.PARTIAL, "consequences": StageStatus.PARTIAL}, CAP, notes
    )

    assert updated == {
        "belief": LedgerEntry(status=StageStatus.PARTIAL, turns=1),
        "consequences": LedgerEntry(status=StageStatus.KNOWN, turns=4),
    }
    assert notes == ["moved the stage back: belief"]
