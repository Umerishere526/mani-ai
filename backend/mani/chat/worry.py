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
# 2026-11-20): one such message can be a changed subject, and a worry nobody closes holds every later turn. Danger
# closes the same way, counted from Mani's reply to it, which asked about their safety, unless they say they are safe
# or someone is with them (S1). PROVISIONAL: clinician sign-off required before deploy.
CALM_TO_CLEAR = 2


class Phase(StrEnum):
    """Where this turn is in the question owed after a pause."""

    ORDINARY = "ordinary"
    ASKING = "asking"  # the question how things are is owed, and this turn's reply asks it
    ANSWERING = "answering"  # Mani's last reply asked it, and this message answers it


class Standing(BaseModel):
    """Where safety stands before their message. `about` is whose danger the open worry is about, and is None while
    nothing is open. `settled`: a worry of theirs settled earlier in this conversation. `calm`: how many messages in a
    row were read as no concern while the worry, unsure or danger, stayed open. `end_check`: Mani's last reply asked the safety question
    after a framework's last stage, so this message answers it. `overdose`: the open worry is about an overdose or a
    poisoning. `immediacy`: whether they said if a worry about themselves is immediate (rec.IMMEDIACY_OPEN or
    rec.IMMEDIACY_ANSWERED), None before they confirmed the thoughts. `paused`: the open worry paused the chat."""

    model_config = {"frozen": True}

    state: State
    about: str | None
    phase: Phase
    settled: bool = False
    calm: int = 0
    end_check: bool = False
    overdose: bool = False
    immediacy: str | None = None
    paused: bool = False


@dataclass(frozen=True)
class Outcome:
    """Where safety stands after their message, and what the turn does because of it."""

    state: State
    about: str | None
    pausing: bool
    settled_now: bool
    # The reply must say where to get help: the first danger of its kind that does not pause (S2), even with someone
    # with them (S7), and every later reply that does not pause while danger about a person is held (CR-3).
    # PROVISIONAL: clinician sign-off required before deploy.
    resources_due: bool = False
    calm: int = 0
    # Code raised the model's read to danger on a high-risk phrase (S4).
    raised: bool = False
    # The open worry is about an overdose or a poisoning, as the model marked it on this message or an earlier one.
    overdose: bool = False
    # Where the question of immediate danger to themselves stands after this message (CR-1).
    immediacy: str | None = None
    # The open worry paused the chat, on this message or an earlier one (CR-5).
    paused: bool = False

    @property
    def paused_for(self) -> str | None:
        """What a pause is for, so a client can lead with 911 after an overdose (R90): overdose, or whose danger it is.
        PROVISIONAL: clinician sign-off required before deploy."""
        return "overdose" if self.overdose else self.about


def standing(ctx: TurnContext, check: ReturnCheck | None, answering: str | None) -> Standing:
    """Where the conversation stands as this turn begins."""
    record = ctx.thread.understanding or {}
    phase = Phase.ASKING if check is not None else Phase.ANSWERING if answering is not None else Phase.ORDINARY
    return Standing(state=State(ctx.thread.safety), about=record.get(rec.ABOUT), phase=phase,
                    settled=bool(record.get(rec.SAFETY_SETTLED)), calm=record.get(rec.CALM, 0),
                    end_check=rec.end_check(record) == rec.END_CHECK_ASKED, overdose=bool(record.get(rec.OVERDOSE)),
                    immediacy=record.get(rec.IMMEDIACY), paused=bool(record.get(rec.PAUSED)))


def step(stood: Standing, read: Safety, message: str = "") -> Outcome:
    """The state after their message, and whether the chat pauses.

    A question owed after a pause makes this a safety turn that never pauses, which starts from unsure: safety is not
    established until they answer. Their answer pauses only when it says the danger is still there. Otherwise danger
    pauses the chat when nothing is in place and the danger went on after Mani had answered it (the state before was
    danger), or after Mani had asked what they meant about this kind of worry and the answer says it again. A first
    danger message out of a clear conversation gets Mani's reply first. An answer after a pause that the model reads
    as danger says the danger is still there, whether or not it marked `still_there`.

    Danger to themselves, to someone else or from someone pauses without a refusal. A danger about a symptom in the
    body pauses only when this turn's read has the symptom happening now and they refuse the help for it, at the level
    code holds it (a symptom the model judged unsure counts as danger), and a danger
    of no known kind needs a refusal too, even while a body worry is open.

    A message holding one of the client's high-risk phrases that the model read below danger is danger about
    themselves, with the help due and no pause on that message (S4). PROVISIONAL: clinician sign-off required before
    deploy."""
    floored = read.level != "danger" and safety.high_risk(message)
    if floored:
        read = read.model_copy(update={"level": "danger", "about": "themselves"})
    start = State.UNSURE if stood.phase is Phase.ASKING and stood.state is State.CLEAR else stood.state
    danger = _DANGER[read.level]
    about = read.about or stood.about
    # Whether Mani had already asked what they meant about this worry. A question about one kind of danger is not a question
    # about another (the held-back run, 2026-11-16: asked whether their parents might hurt them, a student said "sometimes
    # I just want to disappear for good" and was paused with no word from Mani). A kind unknown on either side counts.
    asked = stood.state is State.UNSURE and (stood.about is None or read.about is None or stood.about == read.about)
    reopening = stood.settled and start is State.CLEAR
    # The danger as code holds it: a body symptom the model judged lower that has not stopped is danger now.
    held = safety.danger_of(danger, read.about, read.symptom_now, reopening=reopening)
    after = safety.after(start, held, read.declined, about=about, danger_about=stood.about)
    # With no question of Mani's being answered, the first message read as no concern leaves the worry where it was:
    # unsure, or danger unless they said they are safe or someone is with them (S1).
    safe_said = read.says_safe or read.help_in_place
    counting = ((stood.state is State.UNSURE or (stood.state is State.DANGER and not safe_said))
                and stood.phase is Phase.ORDINARY and not stood.end_check
                and after is State.CLEAR and stood.calm + 1 < CALM_TO_CLEAR)
    # Danger that paused the chat closes only on their word that they are safe or someone is with them, in any phase
    # and however many calm messages come (CR-5, PROVISIONAL: clinician sign-off required before deploy).
    held_to_word = stood.paused and stood.state is State.DANGER and not safe_said and after is State.CLEAR
    waits = counting or held_to_word
    if waits:
        after = stood.state
    if about == "body" and read.about is None and danger != "none":
        # A danger of no known kind while a body worry is open is not held to the body's rule: it needs a refusal.
        kind_pauses = read.declined
    elif about == "body":
        kind_pauses = read.declined and held == "now" and read.symptom_now == "yes"
    else:
        kind_pauses = read.declined or about is not None
    if stood.phase is Phase.ASKING:
        goes_on = False
    elif stood.phase is Phase.ANSWERING:
        goes_on = read.still_there or danger == "now"
    elif stood.state is State.UNSURE:
        goes_on = asked and danger == "now"
    else:
        goes_on = stood.state is State.DANGER
    # Danger held only by the count of calm messages is not danger going on, so it never pauses.
    pausing = after is State.DANGER and not waits and not floored and kind_pauses and not read.help_in_place and goes_on
    # The first danger of each kind; and while danger about a person is held, every reply, unless their message says
    # someone is with them (S7). A body symptom's line comes once per rise (muhammad, 2026-11-18). CR-3, PROVISIONAL:
    # clinician sign-off required before deploy.
    first_of_kind = stood.state is not State.DANGER or stood.about != about
    resources_due = (after is State.DANGER and not pausing
                     and (first_of_kind or (about != "body" and not read.help_in_place)))
    return Outcome(
        immediacy=_immediacy(stood, read, after, about, safe_said),
        state=after, about=about if after is not State.CLEAR else None, pausing=pausing,
        settled_now=stood.state is not State.CLEAR and after is State.CLEAR,
        resources_due=resources_due, calm=stood.calm + 1 if counting else 0, raised=floored,
        paused=after is not State.CLEAR and (pausing or stood.paused),
        overdose=after is not State.CLEAR and (read.overdose or stood.overdose),
    )


def _immediacy(stood: Standing, read: Safety, after: State, about: str | None, safe_said: bool) -> str | None:
    """Where the question of immediate danger to themselves stands after this message: open once they confirm thoughts
    of not being here or of hurting themselves (a danger read, or an unsure one after Mani asked about this worry), and
    answered once their message says whether it is immediate or that they are safe. CR-1, PROVISIONAL: clinician
    sign-off required before deploy."""
    if after is State.CLEAR or about != "themselves":
        return None
    if read.immediacy_said or safe_said:
        return rec.IMMEDIACY_ANSWERED
    if stood.phase is Phase.ASKING:
        # Back after a pause, time has passed: code's question asks it again (CR-5).
        return rec.IMMEDIACY_OPEN
    if stood.immediacy == rec.IMMEDIACY_ANSWERED:
        return rec.IMMEDIACY_ANSWERED
    asked = stood.state is not State.CLEAR and stood.about in (None, "themselves")
    confirmed = read.about == "themselves" and (read.level == "danger" or (read.level == "unsure" and asked))
    return rec.IMMEDIACY_OPEN if confirmed or stood.immediacy == rec.IMMEDIACY_OPEN else None


def record_after(record: dict, outcome: Outcome, *, check: ReturnCheck | None, answering: str | None) -> dict:
    """The record with where the return check stands, whose danger the open worry is about and whether it is an overdose
    (both forgotten when it settles), how many calm messages an open worry has had, whether this conversation reached
    danger, and whether a worry settled."""
    after = {key: value for key, value in record.items()
             if key not in (rec.ABOUT, rec.CALM, rec.OVERDOSE, rec.IMMEDIACY, rec.PAUSED)}
    if outcome.about:
        after[rec.ABOUT] = outcome.about
    if outcome.immediacy:
        after[rec.IMMEDIACY] = outcome.immediacy
    if outcome.paused:
        after[rec.PAUSED] = True
    if outcome.overdose:
        after[rec.OVERDOSE] = True
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
        "help_in_place": read.help_in_place or None, "says_safe": read.says_safe or None,
        "overdose": read.overdose or None, "immediacy_said": read.immediacy_said or None,
        "still_there": read.still_there or None,
    }.items() if value is not None}
