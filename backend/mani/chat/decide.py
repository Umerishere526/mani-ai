# ABOUTME: What code does with the turn's reply: the guarantees the model cannot be trusted with alone. Which offer is
# ABOUTME: made, how far a framework moves, when it starts, finishes or is declined, and which buttons are shown.

from __future__ import annotations

import dataclasses
import uuid
from dataclasses import dataclass, field

from mani.chat import record as rec
from mani.chat.questions import WANTS_TO_STOP
from mani.chat.greeting import CONTINUE_CHATTING_LABEL, FINISH_LABEL, VISIT_LIBRARY_LABEL
from mani.chat.repairs import feelings_buttons, lead_in_buttons, start_buttons
from mani.chat.reply import TurnReply
from mani.chat.taps import TapEvent
from mani.chat.techniques import FEELINGS, OFFERING, STEPS, Registry, stages_of
from mani.llm.schema import LibrarySection, SmartPrompt
from mani.models.rows import Framework, TechniqueOutcome, TechniqueState


# The person's message an offer may come with at the earliest; the style tap is not one of theirs. The same opening
# offered on the 2nd message in one run and the 3rd in the next (muhammad, 2026-11-18).
OFFER_FROM_MESSAGE = 3


@dataclass(frozen=True)
class Decision:
    """What this reply changes: the buttons under it, the framework row, and the record's outcomes."""

    prompts: list[SmartPrompt] = field(default_factory=list)
    technique: TechniqueState | None = None
    retire_technique: bool = False
    declined: list[str] = field(default_factory=list)
    finished: list[str] = field(default_factory=list)
    end_check: bool = False
    refused: str | None = None
    # The five steps code adds after the reply: a typed answer to the lead-in gets the reply, then the steps.
    show_steps: Framework | None = None


def stage_of(framework: Framework, reported: str | None, current: str | None) -> str | None:
    """The stage the reply reports, held to one step past where the framework stood. The starting turn opens the first
    stage only: the client's sequence asks every letter on its own reply. A stage of another framework is None."""
    stages = stages_of(framework)
    if reported not in stages:
        return None
    furthest = stages.index(current) + 1 if current in stages else 0
    return stages[min(stages.index(reported), furthest, len(stages) - 1)]


def offer_current(open_offer: TechniqueState, message_count: int) -> bool:
    """Whether the open offer is still what they are answering: at its lead-in, only while the lead-in is Mani's last
    reply. After a turn about something else (a safety exchange), the lead-in has passed and the offer lapses rather
    than pushing the five steps onto their next message (the final review, 2026-11-18)."""
    return open_offer.phase != OFFERING or open_offer.at_message_count == message_count


def closing_buttons(*, with_finish: bool = True) -> list[SmartPrompt]:
    """The close: Continue chatting and Visit library, and Finish for Now unless they already said they are done."""
    buttons = [SmartPrompt(label=CONTINUE_CHATTING_LABEL),
               SmartPrompt(label=VISIT_LIBRARY_LABEL, library=LibrarySection.HOME.value)]
    return [*buttons, SmartPrompt(label=FINISH_LABEL)] if with_finish else buttons


def decide(
    reply: TurnReply, registry: Registry, *, thread_id: uuid.UUID, running: TechniqueState | None,
    open_offer: TechniqueState | None, tap: TapEvent, record: dict, guarded: bool, count_after: int,
    end_check_due: bool, end_check_asked: bool, person_messages: int,
) -> Decision:
    """The spec's guarantees, in order: a start, a running framework's move, an open offer's answer, a new offer, and
    the library. A guarded turn (a safety worry open or found) changes no framework state and makes no offer. When they
    want to stop, a running or offered set stops too, and the close follows a reply that asks nothing (R95)."""
    base = Decision(declined=rec.declined(record), finished=rec.finished(record))
    if guarded:
        return dataclasses.replace(base, refused="offer" if reply.action == "offer" else None)
    stopping = reply.question.latest.strip().lower() == WANTS_TO_STOP
    if stopping:
        reply = reply.model_copy(update={"action": "stop", "stage": None})
    if tap.starting is not None:
        decision = _started(base, reply, tap.starting, thread_id, count_after)
    elif (open_offer is not None and open_offer.phase == STEPS and (offered := registry.get(open_offer.framework_id))
          and stage_of(offered, reply.stage, None)):
        decision = _started(base, reply, offered, thread_id, count_after)
    elif running is not None and (framework := registry.get(running.framework_id)):
        decision = _moved(base, reply, framework, running, end_check_due, end_check_asked)
    elif open_offer is not None:
        offered = registry.get(open_offer.framework_id) if offer_current(open_offer, count_after - 2) else None
        decision = _answered_offer(base, open_offer, offered, tap, reply)
    else:
        decision = base
    # An offer is refused while a set runs or is offered, and before their 3rd message: each is said in the facts first.
    decision = _offer(decision, reply, registry, thread_id, count_after,
                      blocked=(running is not None or open_offer is not None or tap.starting is not None
                               or person_messages < OFFER_FROM_MESSAGE))
    if reply.action == "library" and not decision.prompts:
        decision = dataclasses.replace(decision, prompts=[
            SmartPrompt(label=VISIT_LIBRARY_LABEL, library=LibrarySection.HOME.value)])
    if stopping:
        decision = dataclasses.replace(decision, prompts=closing_buttons(with_finish=False))
    return decision


def _started(base: Decision, reply: TurnReply, framework: Framework, thread_id, count_after: int) -> Decision:
    phase = stage_of(framework, reply.stage, None) or stages_of(framework)[0]
    return dataclasses.replace(base, technique=TechniqueState(
        thread_id=thread_id, framework_id=framework.id, outcome=TechniqueOutcome.ACCEPTED, phase=phase,
        at_message_count=count_after))


def _moved(base: Decision, reply: TurnReply, framework: Framework, running: TechniqueState, end_check_due: bool,
           end_check_asked: bool) -> Decision:
    if running.phase == FEELINGS:
        # Their answer to how they feel, tapped or typed, closes the set.
        return dataclasses.replace(base, finished=[*base.finished, framework.id], retire_technique=True,
                                   prompts=closing_buttons())
    if reply.action == "stop":
        return dataclasses.replace(base, declined=[*base.declined, framework.id], technique=running.model_copy(
            update={"outcome": TechniqueOutcome.DECLINED, "phase": None}))
    on_last = running.phase == stages_of(framework)[-1]
    # A turn that reaches decide after the safety question was asked is one whose answer settled it: it closes the set.
    if on_last and (reply.action == "finish" or end_check_asked):
        if end_check_due and not end_check_asked:
            return dataclasses.replace(base, end_check=True)
        return dataclasses.replace(base, technique=running.model_copy(update={"phase": FEELINGS}),
                                   prompts=feelings_buttons())
    stage = stage_of(framework, reply.stage, running.phase)
    if stage is not None and stage != running.phase:
        return dataclasses.replace(base, technique=running.model_copy(update={"phase": stage}))
    return base


def _answered_offer(base: Decision, open_offer: TechniqueState, offered: Framework | None, tap: TapEvent,
                    reply: TurnReply) -> Decision:
    """A clear no declines the offer. Talk more first sets it aside for now. Show me how is the reply's walk through the
    steps on their own situation, then the choice to start. A typed answer to the lead-in gets the five steps after the
    reply (muhammad, 2026-11-18); any other answer after the steps lets the offer lapse."""
    if reply.action == "stop":
        return dataclasses.replace(base, declined=[*base.declined, open_offer.framework_id], technique=open_offer.model_copy(
            update={"outcome": TechniqueOutcome.DECLINED, "phase": None}))
    if offered is not None and tap.demonstrate is not None:
        return dataclasses.replace(base, prompts=start_buttons(offered, with_example=False),
                                   technique=open_offer.model_copy(update={"phase": STEPS}))
    if offered is not None and open_offer.phase == OFFERING and not tap.set_aside:
        return dataclasses.replace(base, show_steps=offered, prompts=start_buttons(offered, with_example=True),
                                   technique=open_offer.model_copy(update={"phase": STEPS}))
    return dataclasses.replace(base, retire_technique=True)


def _offer(decision: Decision, reply: TurnReply, registry: Registry, thread_id, count_after: int, *,
           blocked: bool) -> Decision:
    if reply.action != "offer":
        return decision
    allowed = (not blocked and reply.framework in registry and reply.framework not in decision.declined
               and not decision.finished)
    if not allowed:
        return dataclasses.replace(decision, refused="offer")
    return dataclasses.replace(
        decision, prompts=lead_in_buttons(), retire_technique=False,
        technique=TechniqueState(thread_id=thread_id, framework_id=reply.framework, outcome=TechniqueOutcome.OFFERED,
                                 phase=OFFERING, at_message_count=count_after))
