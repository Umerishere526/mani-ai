# ABOUTME: The one rule that moves a conversation's safety each turn: where it stands before their message, the model's
# ABOUTME: read of it, and what follows: the state after, whether the chat pauses, and what the record keeps.

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel

from mani.chat import record as rec
from mani.chat import safety
from mani.chat.pause import ReturnCheck
from mani.chat.reply import Safety
from mani.chat.safety import State
from mani.db.threads import TurnContext

_DANGER = {"none": "none", "unsure": "unsure", "danger": "now"}
# An unsure worry they never answered closes once this many messages in a row are read as no concern (muhammad,
# 2026-11-20): one such message can be a changed subject, and a worry nobody closes holds every later turn.
CALM_TO_CLEAR = 2


class Phase(StrEnum):
    """Where this turn is in the question owed after a pause."""

    ORDINARY = "ordinary"
    ASKING = "asking"  # the question how things are is owed, and this turn's reply asks it
    ANSWERING = "answering"  # Mani's last reply asked it, and this message answers it


class Standing(BaseModel):
    """Where safety stands before their message. `about` is whose danger the open worry is about, and is None while
    nothing is open. `settled`: a worry of theirs settled earlier in this conversation. `reset`: the worry the
    conversation held was settled by their word elsewhere that they are all right. `calm`: how many messages in a row
    were read as no concern while the worry stayed open. `end_check`: Mani's last reply asked the safety question after
    a framework's last stage, so this message answers it."""

    model_config = {"frozen": True}

    state: State
    about: str | None
    phase: Phase
    settled: bool = False
    reset: bool = False
    calm: int = 0
    end_check: bool = False


@dataclass(frozen=True)
class Outcome:
    """Where safety stands after their message, and what the turn does because of it."""

    state: State
    about: str | None
    pausing: bool
    settled_now: bool
    # Code raised this turn to danger on a body worry the model itself judged lower, so the reply gets the call-now line,
    # once per body worry.
    body_emergency: bool = False
    calm: int = 0


def standing(ctx: TurnContext, check: ReturnCheck | None, answering: str | None) -> Standing:
    """Where the conversation stands as this turn begins. A conversation still holding a worry that began before they
    said, in any conversation, that they are all right stands settled: the pause began in one that was never answered
    in, and its next message used to pause with no word from Mani."""
    record = ctx.thread.understanding or {}
    state, about = State(ctx.thread.safety), record.get(rec.ABOUT)
    latest = ctx.pause
    reset = (state is not State.CLEAR and latest is not None and latest.checked_at is not None
             and latest.checked_at > ctx.thread.last_message_at)
    if reset:
        state, about = State.CLEAR, None
    phase = Phase.ASKING if check is not None else Phase.ANSWERING if answering is not None else Phase.ORDINARY
    return Standing(state=state, about=about, phase=phase, settled=bool(record.get(rec.SAFETY_SETTLED)), reset=reset,
                    calm=0 if reset else record.get(rec.CALM, 0),
                    end_check=rec.end_check(record) == rec.END_CHECK_ASKED)


def step(stood: Standing, read: Safety) -> Outcome:
    """The state after their message, and whether the chat pauses.

    A question owed after a pause makes this a safety turn that never pauses, which starts from unsure: safety is not
    established until they answer. Their answer pauses only when it says the danger is still there. Otherwise danger
    pauses the chat when nothing is in place and the danger went on after Mani had answered it (the state before was
    danger), or after Mani had asked what they meant about this kind of worry and the answer says it again. A first
    danger message out of a clear conversation gets Mani's reply first.

    Danger to themselves, to someone else or from someone pauses without a refusal. A danger about a symptom in the
    body pauses only when this turn's read has the symptom happening now and they refuse the help for it, and a danger
    of no known kind needs a refusal too, so a read without `about` never pauses a body chat."""
    start = State.UNSURE if stood.phase is Phase.ASKING and stood.state is State.CLEAR else stood.state
    danger = _DANGER[read.level]
    about = read.about or stood.about
    # Whether Mani had already asked what they meant about this worry. A question about one kind of danger is not a question
    # about another (the held-back run, 2026-11-16: asked whether their parents might hurt them, a student said "sometimes
    # I just want to disappear for good" and was paused with no word from Mani). A kind unknown on either side counts.
    asked = stood.state is State.UNSURE and (stood.about is None or read.about is None or stood.about == read.about)
    reopening = stood.settled and start is State.CLEAR
    after = safety.after(start, safety.danger_of(danger, read.about, read.symptom_now, reopening=reopening),
                         read.declined, about=about, danger_about=stood.about)
    # Unsure with no question of Mani's being answered: the first message read as no concern leaves the worry open.
    waits = (stood.state is State.UNSURE and stood.phase is Phase.ORDINARY and not stood.end_check
             and after is State.CLEAR and stood.calm + 1 < CALM_TO_CLEAR)
    if waits:
        after = State.UNSURE
    if about == "body":
        kind_pauses = read.declined and danger == "now" and read.symptom_now == "yes"
    else:
        kind_pauses = read.declined or about is not None
    if stood.phase is Phase.ASKING:
        goes_on = False
    elif stood.phase is Phase.ANSWERING:
        goes_on = read.still_there
    elif stood.state is State.UNSURE:
        goes_on = asked and danger == "now"
    else:
        goes_on = stood.state is State.DANGER
    # Once per body worry: a conversation already in danger over the body has had the line; danger of another kind has not.
    body_emergency = (read.about == "body" and read.level != "danger" and after is State.DANGER
                      and (stood.state is not State.DANGER or stood.about != "body"))
    return Outcome(
        state=after, about=about if after is not State.CLEAR else None,
        pausing=after is State.DANGER and kind_pauses and not read.help_in_place and goes_on,
        settled_now=stood.reset or (stood.state is not State.CLEAR and after is State.CLEAR),
        body_emergency=body_emergency, calm=stood.calm + 1 if waits else 0,
    )


def record_after(record: dict, outcome: Outcome, *, check: ReturnCheck | None, answering: str | None) -> dict:
    """The record with where the return check stands, whose danger the open worry is about (forgotten when it settles),
    how many calm messages an open worry has had, whether this conversation reached danger, and whether a worry
    settled."""
    after = {key: value for key, value in record.items() if key not in (rec.ABOUT, rec.CALM)}
    if outcome.about:
        after[rec.ABOUT] = outcome.about
    if outcome.calm:
        after[rec.CALM] = outcome.calm
    if check is not None:
        after = rec.return_check(after, str(check.pause_id), "asked")
    elif answering is not None:
        after = rec.return_check(after, answering, "answered")
    if outcome.state is State.DANGER:
        after[rec.DANGER_REACHED] = True
    if outcome.settled_now:
        after[rec.SAFETY_SETTLED] = True
    return after


def traced(read: Safety) -> dict:
    """The judgment as the turn's trace keeps it: closed values only, never its line of why."""
    return {key: value for key, value in {
        "level": read.level, "about": read.about, "declined": read.declined or None, "symptom_now": read.symptom_now,
        "help_in_place": read.help_in_place or None, "still_there": read.still_there or None,
    }.items() if value is not None}
