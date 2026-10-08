# ABOUTME: Applies what a reply reports of each stage to the stored ledger of a running framework.
# ABOUTME: Ids, statuses and counts only, so no word the person or the model wrote reaches the row.

from __future__ import annotations

from mani.chat.techniques import Registry
from mani.models.rows import LedgerEntry, StageStatus

# How far along a status is, so a report that lowers one can be told apart from one that raises it.
_PROGRESS = {StageStatus.MISSING: 0, StageStatus.PARTIAL: 1, StageStatus.KNOWN: 2}


def stored_stages(
    registry: Registry, framework_id: str, stored: dict[str, LedgerEntry]
) -> dict[str, LedgerEntry]:
    """The stored entries that are stages of the framework as it is now, in its order. A reseed can
    change a framework's phases, and an entry for a stage that is gone is ignored."""
    return {stage: stored[stage] for stage in registry.ledger_stages(framework_id) if stage in stored}


def with_reported(
    ledger: dict[str, LedgerEntry],
    reported: dict[str, StageStatus] | None,
    notes: list[str],
) -> dict[str, LedgerEntry]:
    """A new ledger with each reported status written over the stored one, in either direction, so
    a correction can reopen a stage. A stage the code passed stays passed. A stage moved back is
    noted by id."""
    updated = dict(ledger)
    for stage, status in (reported or {}).items():
        current = updated.get(stage)
        if current is not None and current.status is StageStatus.PASSED:
            continue
        if current is not None and _PROGRESS[status] < _PROGRESS[current.status]:
            notes.append(f"moved the stage back: {stage}")
        updated[stage] = LedgerEntry(status=status, turns=current.turns if current else 0)
    return updated
