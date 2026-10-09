# ABOUTME: Why a drafted reply is asked for again once: an offer not allowed, an offer ruled out, no question, a question asked again.
# ABOUTME: Pure checks on the draft, so each reason is a unit test; the orchestrator makes the one extra call.

from __future__ import annotations

import re
from dataclasses import dataclass

from mani.chat import eligibility, repairs
from mani.chat.techniques import Registry
from mani.llm.schema import NO_QUESTION_SHAPES, Reply
from mani.models.rows import ENDING_STAGES, Framework


def offered(reply: Reply, registry: Registry) -> str | None:
    """The framework a draft offers, if it carries an offer button for one that exists. An id the
    registry does not know is repairs.apply's to remove, not worth another call."""
    return next(
        (p.technique for p in reply.prompts or [] if p.technique and registry.get(p.technique)),
        None,
    )


def ruled_out(reply: Reply, user_texts: list[str], registry: Registry) -> str | None:
    """The framework a draft offers when what the person has said rules it out: the phrases a
    framework file lists under `never_offer_when_said` (early grief for Behavioral Activation).
    A prompt rule alone did not hold, so this is checked in code."""
    technique = offered(reply, registry)
    activation = registry.activations.get(technique) if technique else None
    if activation and eligibility.vetoes(activation, user_texts):
        return technique
    return None


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


def reasons(
    reply: Reply,
    user_texts: list[str],
    registry: Registry,
    *,
    offer_not_allowed: bool,
    closest_fit_due: bool = False,
    needs_question: bool = False,
    stage_in_force: StageInForce | None = None,
    last_mani_text: str | None = None,
) -> list[str]:
    """What is wrong with the draft that only the model can fix, as lines for the model to read.
    Empty when the draft stands."""
    notes: list[str] = []

    framework = registry.get(stage_in_force.framework_id) if stage_in_force else None
    expected = ledger_stage(reply, framework, stage_in_force) if framework else None
    step = (
        reply.state.step
        if expected and reply.state and reply.state.technique == framework.id
        else None
    )
    if expected and step != expected:
        notes.append(
            f"your stages_known says {expected} is the first stage not yet answered, but "
            f"state.step is {step or 'missing'}; ask {expected}, only for what its known does not "
            "already hold, and report it in state.step"
        )

    technique = offered(reply, registry)
    if not technique and repeats(reply, last_mani_text):
        notes.append(
            "your draft asks the question you asked last turn, with the same choices; answer "
            "what they just said first (a yes or a question of theirs counts), then move on: "
            "if they asked you to choose, offer one small step as a draft they can accept or change"
        )
    chose_to_ask_nothing = bool(
        reply.style and reply.style.shape.strip().lower() in NO_QUESTION_SHAPES
    )
    if needs_question and not technique and "?" not in reply.text and not chose_to_ask_nothing:
        notes.append(
            "your draft asks no question; end with one short, plain question about one part of what "
            "they just said, in their words"
        )
    if technique and offer_not_allowed:
        notes.append(
            "your draft offered a set of questions, which is not allowed yet for a fit that is "
            "not clear; if you are confident which set fits, set offer_fit to clear, otherwise "
            "offer nothing and ask one short, plain question about one part of what they just "
            "said, in their words"
        )
    elif not technique and closest_fit_due and reply.heading_toward:
        notes.append(
            "you have talked for several replies and not offered: offer the set of questions "
            "that fits best now, by its name and plainly, the way you would one that fits "
            "exactly, with offer_fit set as it really is"
        )
    elif technique and ruled_out(reply, user_texts, registry):
        framework = registry.get(technique)
        name = framework.name if framework else technique
        notes.append(
            f"your draft offered {name}, which does not fit what they have told you (see "
            "'Never offer one when'); offer nothing and ask one question instead"
        )
    return notes
