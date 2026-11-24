# ABOUTME: The thread record a turn keeps in threads.understanding: Mani's notes, its questions, the frameworks declined
# ABOUTME: or finished, and the safety keys the pause rules read. Pure helpers; the turn writes the result.

from __future__ import annotations

NOTES = "notes"
# Each open-chat reply, oldest first: the question it asked ("" for none) and what that question was for.
QUESTIONS = "questions"
QUESTIONS_KEPT = 12
DECLINED = "declined"
FINISHED = "finished"
# The safety keys: where the question owed after a pause stands, whether a worry settled and whether danger was reached
# (each lasts the conversation), and whose danger the open worry is about (only while it is open).
RETURN_CHECK = "return_check"
SAFETY_SETTLED = "safety_settled"
DANGER_REACHED = "danger_reached"
ABOUT = "worry_about"
# How many messages in a row were read as no concern while an unsure worry stayed open (worry.CALM_TO_CLEAR).
CALM = "worry_calm"
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


def questions(record: dict) -> list[dict]:
    """The open-chat replies kept, oldest first, each as {"q": the question or "", "intent": what it was for}."""
    return list(record.get(QUESTIONS) or [])


def with_question(record: dict, question: str, intent: str) -> dict:
    """The record with this reply's question added, keeping the latest QUESTIONS_KEPT."""
    return {**record, QUESTIONS: [*questions(record), {"q": question, "intent": intent}][-QUESTIONS_KEPT:]}


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
