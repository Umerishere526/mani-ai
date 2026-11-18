# ABOUTME: The thread record a turn keeps in threads.understanding: Mani's notes, the frameworks declined or finished,
# ABOUTME: and the safety keys the pause rules read. Pure helpers; the turn writes the result.

from __future__ import annotations

NOTES = "notes"
DECLINED = "declined"
FINISHED = "finished"
# The keys the kept pause rules and the check after a framework read, unchanged from the turn they came from.
RETURN_CHECK = "return_check"
SAFETY_SETTLED = "safety_settled"
DANGER_REACHED = "danger_reached"
DANGER_ABOUT = "danger_about"
ASKED_ABOUT = "asked_about"
SAFETY_END_CHECK = "safety_end_check"


def declined(record: dict) -> list[str]:
    """The frameworks declined in this conversation, never offered again."""
    return list(record.get(DECLINED) or [])


def finished(record: dict) -> list[str]:
    """The frameworks finished in this conversation, after which no framework is offered."""
    return list(record.get(FINISHED) or [])


def with_outcomes(record: dict, *, notes: str | None, declined: list[str], finished: list[str]) -> dict:
    """The record with this turn's outcomes; `notes=None` keeps the notes already stored."""
    after = {**record, DECLINED: declined, FINISHED: finished}
    if notes is not None:
        after[NOTES] = notes
    return after
