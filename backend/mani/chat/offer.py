# ABOUTME: What this turn should do: keep talking, ask, clarify, or offer a framework.
# ABOUTME: Code decides, the model words it - so an offer is never the model's own idea.

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from mani.chat import semantic_router as sr

# How many of the person's own messages pass before a framework may be offered, and when
# the window has gone on too long (muhammad, 2026-10-05). Direct reaches a framework
# soonest; Supportive and Reflective earn the room to explore first.
#
#   Direct      3-5 exchanges, never past 5
#   Supportive  7-9, never past 9
#   Reflective  7-10
#
# `soonest` is the earliest a clear fit may be offered. Only a clear fit is ever offered:
# a conversation that does not point at one keeps going, because a framework nobody needs
# is worse than no framework (muhammad, 2026-10-06).
CADENCE: dict[str, tuple[int, int]] = {
    "direct": (3, 5),
    "supportive": (7, 9),
    "reflective": (7, 10),
}
DEFAULT_CADENCE = CADENCE["supportive"]


class Action(StrEnum):
    CONTINUE = "continue"
    """Stay with them. No offer."""
    ASK = "ask"
    """One question that follows what they said."""
    CLARIFY = "clarify"
    """Two frameworks are plausible; ask the one thing that separates them."""
    OFFER_FRAMEWORK = "offer_framework"
    """Code has decided. The buttons are added whether the model asked for them or not."""
    START_FRAMEWORK = "start_framework"
    """They accepted this turn."""
    CONTINUE_STAGE = "continue_stage"
    """A framework is running; the stage owns the turn."""
    CLOSE = "close"
    """The framework is finishing."""


@dataclass(frozen=True)
class Decision:
    action: Action
    framework_id: str | None = None
    separates: tuple[str, str] | None = None
    """The two framework ids a CLARIFY question should tell apart. Never shown to the person."""
    separates_as_text: str | None = None
    """What those two frameworks are each for, in plain words, so the model can ask the one
    question that separates them without ever seeing a framework id it could echo."""
    why: str = ""
    """One line, logged. Never sent to the model, never shown."""

    @property
    def offers(self) -> bool:
        return self.action is Action.OFFER_FRAMEWORK


def cadence_for(style: str | None) -> tuple[int, int]:
    return CADENCE.get((style or "").lower(), DEFAULT_CADENCE)


def decide(
    routing: sr.Routing,
    *,
    style: str | None,
    their_messages: int,
    cooldown_passed: bool,
    safety_concern: bool = False,
    their_last: str | None = None,
    framework_running: bool = False,
    accepted_this_turn: bool = False,
    finishing: bool = False,
    vetoed: frozenset[str] | tuple[str, ...] = (),
) -> Decision:
    """What this turn should do. Deterministic: the same inputs always give the same action.

    The order is the priority. The person comes before the process, so everything they said
    about themselves or about Mani is answered before any framework question is reached.
    """
    # 1. Safety. Nothing is offered and nothing is asked while they may not be safe.
    if safety_concern:
        return Decision(Action.CONTINUE, why="safety concern")

    # 2. They accepted. Begin, whatever else the routing says.
    if accepted_this_turn:
        return Decision(Action.START_FRAMEWORK, routing.top.framework_id if routing.top else None,
                        why="accepted this turn")

    # 3. A framework is running. Its stage owns the turn; routing is not even consulted.
    if framework_running:
        if finishing:
            return Decision(Action.CLOSE, why="final stage")
        return Decision(Action.CONTINUE_STAGE, why="stage in progress")

    # 4. They asked only to be heard. No question, no offer, until they turn to it themselves.
    if their_last == "heard":
        return Decision(Action.CONTINUE, why="asked only to be heard")

    # 5. They said Mani missed something, or spoke about how Mani is talking to them. That is
    #    answered first, and nothing is offered on the same turn.
    if their_last in ("correction", "about_mani"):
        return Decision(Action.ASK, why=f"their_last: {their_last}")

    top = routing.top
    if top is not None and top.framework_id in set(vetoed):
        # What they have said rules this one out. Demoted here rather than caught downstream,
        # so the decision and the offer can never disagree.
        return Decision(Action.ASK, why=f"{top.framework_id} ruled out by what they said")

    # 6. An action about to be taken does not wait for the cadence.
    if top is not None and top.time_critical:
        return Decision(Action.OFFER_FRAMEWORK, top.framework_id, why="imminent action")

    # 7. What they are talking about has changed. The evidence predates the new topic, so
    #    follow them for a turn rather than offering against what they have moved on from.
    if routing.topic_changed:
        return Decision(Action.ASK, why="topic changed")

    soonest, _ = cadence_for(style)

    if routing.status is sr.RouteStatus.MATCH and top is not None:
        if not cooldown_passed:
            return Decision(Action.ASK, top.framework_id, why="cooldown")
        if their_messages < soonest:
            return Decision(Action.ASK, top.framework_id, why=f"before {soonest} messages")
        return Decision(Action.OFFER_FRAMEWORK, top.framework_id, why="clear fit")

    if routing.status is sr.RouteStatus.AMBIGUOUS and len(routing.candidates) >= 2:
        return Decision(
            Action.CLARIFY,
            top.framework_id,
            separates=(routing.candidates[0].framework_id, routing.candidates[1].framework_id),
            why="two plausible fits",
        )

    if routing.status is sr.RouteStatus.WEAK_MATCH and top is not None:
        return Decision(Action.ASK, top.framework_id, why="weak fit")

    # Nothing fits. Follow them; a framework is not owed.
    return Decision(Action.ASK, why="no fit")
