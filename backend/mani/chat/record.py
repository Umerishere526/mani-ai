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
# Where the safety question after a framework's last stage stands.
END_CHECK_ASKED = "asked"
END_CHECK_DONE = "done"


def declined(record: dict) -> list[str]:
    """The frameworks declined in this conversation, never offered again."""
    return list(record.get(DECLINED) or [])


def finished(record: dict) -> list[str]:
    """The frameworks finished in this conversation, after which no framework is offered."""
    return list(record.get(FINISHED) or [])


def return_check(record: dict, pause_id: str, state: str) -> dict:
    """The record with the question about pause `pause_id` at `state`: asked, or answered."""
    return {**record, RETURN_CHECK: {"pause": pause_id, "state": state}}


def return_check_pause(record: dict, *, state: str | None = None) -> str | None:
    """The pause the record's return check is about, or None; with `state`, only while it stands at that state."""
    check = record.get(RETURN_CHECK) or {}
    return check.get("pause") if state is None or check.get("state") == state else None


def end_check(record: dict) -> str | None:
    """Where the safety question after a framework's last stage stands: asked, done, or None."""
    return record.get(SAFETY_END_CHECK)


def with_outcomes(record: dict, *, notes: str | None, declined: list[str], finished: list[str]) -> dict:
    """The record with this turn's outcomes; `notes=None` keeps the notes already stored."""
    after = {**record, DECLINED: declined, FINISHED: finished}
    if notes is not None:
        after[NOTES] = notes
    return after
