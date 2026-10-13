# ABOUTME: Checks on the model's reply that cost no model call: the stage its own ledger says to ask, and what it missed.
# ABOUTME: Pure functions, so each check is a unit test; the orchestrator corrects the step and logs the misses.

from __future__ import annotations

import re
from dataclasses import dataclass

from mani.llm.schema import NO_QUESTION_SHAPES, Reply
from mani.models.rows import ENDING_STAGES, Framework

_QUESTION = re.compile(r"[^.!?\n]*\?")
REPEAT_OVERLAP = 0.7


def _last_question_words(text: str) -> set[str]:
    questions = _QUESTION.findall(text)
    return set(re.findall(r"[a-z']{4,}", questions[-1].lower())) if questions else set()


def repeats(reply: Reply, last_mani_text: str | None) -> bool:
    """Whether the draft's closing question is, by its words, the question Mani asked last turn.
    A person who answers a question and gets it back unchanged is stuck, however it is reworded."""
    now, before = _last_question_words(reply.text), _last_question_words(last_mani_text or "")
    return bool(now and before and len(now & before) / min(len(now), len(before)) >= REPEAT_OVERLAP)


@dataclass(frozen=True)
class StageInForce:
    """Where the questions stand as this reply is written. `asked` is whether that stage's question
    was already put to them: a stage they have been asked may be left once answered, even the
    closing; one never asked is skipped only if it may be."""

    framework_id: str
    stage: str
    asked: bool


def ledger_stage(reply: Reply, framework: Framework, start: StageInForce) -> str | None:
    """The stage the draft's own stages_known says to ask: walking from the stage in force, the first
    it does not mark met, or the first that may not be skipped. None when it has no ledger, or when
    the walk reaches the body route, which code runs."""
    if not reply.stages_known or framework.phase_index(start.stage) < 0:
        return None
    met = {entry.stage for entry in reply.stages_known if entry.met}
    for phase in framework.phases[framework.phase_index(start.stage) :]:
        if phase in ENDING_STAGES:
            return None
        passable = framework.may_skip(phase) or (phase == start.stage and start.asked)
        if phase not in met or not passable:
            return phase
    return None


# What the reply does with a stage, for the debug view. `known` is shown as bypassed: it is not asked.
_ACTIONS = {
    "known": "bypassed, not asked",
    "partial": "partly known, ask only the gap",
    "confirm": "confirm it with them",
    "missing": "missing, ask it",
    "done": "answered in an earlier reply",
    "not_reached": "not reached yet",
}


def ledger_view(reply: Reply, framework: Framework | None) -> list[dict]:
    """Every content stage of the framework as the draft's own ledger reads it, for a person
    watching the conversation: how much of it is known, and what the reply does about it. A stage
    before the ledger starts was answered earlier, and one after it has not been reached."""
    if not reply.stages_known:
        return []
    entries = {entry.stage: entry for entry in reply.stages_known}
    order = (
        [p for p in framework.phases if p != "offering" and p not in ENDING_STAGES]
        if framework else list(entries)
    )
    first = next((i for i, stage in enumerate(order) if stage in entries), 0)
    asking = reply.state.step if reply.state else None
    rows = []
    for index, stage in enumerate(order):
        entry = entries.get(stage)
        known = entry.known if entry else None
        if entry:
            status = entry.status
        else:
            status = "done" if index < first else "not_reached"
        rows.append({
            "stage": stage,
            "title": (((framework.stages or {}).get(stage) or {}).get("title") if framework else None),
            "status": status,
            "known": known,
            "action": _ACTIONS[status],
            "asking": stage == asking,
        })
    return rows


def with_ledger_step(reply: Reply, framework: Framework, start: StageInForce) -> Reply:
    """The reply with `state.step` set to the stage its own `stages_known` says to ask. The step
    is written after the text, so a disagreement is a label the code can fix, not a question to
    ask the model again. Unchanged when the reply has no ledger or reports no state."""
    expected = ledger_stage(reply, framework, start)
    state = reply.state
    if not expected or state is None or state.technique != framework.id or state.step == expected:
        return reply
    return reply.model_copy(update={"state": state.model_copy(update={"step": expected})})


def misses(
    reply: Reply,
    *,
    offered: str | None,
    offer_dropped: str | None,
    offer_due: bool,
    needs_question: bool,
    last_mani_text: str | None,
) -> list[str]:
    """What the draft got wrong that code cannot fix, named for the log. Empty when it stands.
    None of these costs a second call: they are counted, so how often each happens is known.
    `offered` is the set the sent reply offers, as code rendered it."""
    notes: list[str] = []
    technique = offered
    if offer_dropped:
        notes.append(f"offer unusable: {offer_dropped}")
    if not technique and repeats(reply, last_mani_text):
        notes.append("repeats the last question")
    chose_to_ask_nothing = bool(
        reply.style and reply.style.shape.strip().lower() in NO_QUESTION_SHAPES
    )
    if needs_question and not technique and "?" not in reply.text and not chose_to_ask_nothing:
        notes.append("asks no question")
    if not technique and offer_due and reply.heading_toward:
        notes.append("offer due and not made")
    return notes
