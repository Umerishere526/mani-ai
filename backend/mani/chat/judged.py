# ABOUTME: Safety from the turn's reply, through the pause rules kept unchanged (pause.pauses_now, safety.after,
# ABOUTME: safety.danger_of): where the conversation stands on safety after this message, and whether it pauses.

from __future__ import annotations

from dataclasses import dataclass

from mani.chat import pause, record as rec, safety
from mani.chat.reply import Safety

_DANGER = {"none": "none", "unsure": "unsure", "danger": "now"}


@dataclass(frozen=True)
class Judged:
    """Where safety stands after this message, and what the turn does because of it."""

    state_after: safety.State
    pausing: bool
    about: str | None
    settled_now: bool
    # Code raised this turn to danger on a body worry the model itself judged lower, so the reply gets the call-now line,
    # once per body worry.
    body_emergency: bool = False


def danger_value(level: str) -> str:
    """The reply's level as the pause rules name it."""
    return _DANGER[level]


def judge(
    before: safety.State, read: Safety, record: dict, *, return_check: pause.ReturnCheck | None,
    answering_return: str | None,
) -> Judged:
    """The state after their message and whether the chat pauses. A return check owed this turn makes it a safety
    turn that never pauses; the answer to it pauses only when it says the danger is still there."""
    state_now = safety.State.UNSURE if return_check is not None and before is safety.State.CLEAR else before
    danger = danger_value(read.level)
    about = read.about or record.get(rec.DANGER_ABOUT)
    asked = safety.asked_about_this(before, record.get(rec.ASKED_ABOUT), read.about)
    reopening = bool(record.get(rec.SAFETY_SETTLED)) and state_now is safety.State.CLEAR
    state_after = safety.after(state_now, safety.danger_of(danger, read.about, read.symptom_now, reopening=reopening),
                               read.declined, about=about, asked=asked)
    pausing = pause.pauses_now(
        before, state_after, help_in_place=read.help_in_place, declined=read.declined, about=about, danger=danger,
        symptom_now=read.symptom_now, asked=asked, after_return_check=answering_return is not None,
        is_return_check=return_check is not None, still_there=read.still_there,
    )
    settled_now = before is not safety.State.CLEAR and state_after is safety.State.CLEAR
    # Once per body worry: a thread already in danger over the body has had the line; danger of another kind has not.
    body_emergency = (read.about == "body" and read.level != "danger" and state_after is safety.State.DANGER
                      and (before is not safety.State.DANGER or record.get(rec.DANGER_ABOUT) != "body"))
    return Judged(state_after=state_after, pausing=pausing, about=about, settled_now=settled_now,
                  body_emergency=body_emergency)


def safety_record(
    record: dict, *, return_check: pause.ReturnCheck | None, answering_return: str | None, judged: Judged,
    read_about: str | None,
) -> dict:
    """The record with where the return check stands, whether this conversation reached danger and whose, whether a
    worry settled, and whose danger an open question is about, kept only while the conversation is unsure."""
    asked_about = (read_about or record.get(rec.ASKED_ABOUT)) if judged.state_after is safety.State.UNSURE else None
    after = {key: value for key, value in record.items() if key != rec.ASKED_ABOUT}
    if asked_about:
        after[rec.ASKED_ABOUT] = asked_about
    if return_check is not None:
        after = rec.return_check(after, str(return_check.pause_id), "asked")
    elif answering_return is not None:
        after = rec.return_check(after, answering_return, "answered")
    if judged.state_after is safety.State.DANGER:
        after[rec.DANGER_REACHED] = True
        if judged.about:
            after[rec.DANGER_ABOUT] = judged.about
    if judged.settled_now:
        after[rec.SAFETY_SETTLED] = True
    return after


def traced(read: Safety) -> dict:
    """The judgment as the turn's trace keeps it: closed values only, never its line of why."""
    return {key: value for key, value in {
        "level": read.level, "about": read.about, "declined": read.declined or None, "symptom_now": read.symptom_now,
        "help_in_place": read.help_in_place or None, "still_there": read.still_there or None,
    }.items() if value is not None}
