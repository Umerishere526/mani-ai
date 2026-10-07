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
#   Direct      3-5 exchanges
#   Supportive  5-7
#   Reflective  6-8
#
# `soonest` is the earliest a clear fit may be offered. Only a clear fit is ever offered:
# a conversation that does not point at one keeps going, because a framework nobody needs
# is worse than no framework (muhammad, 2026-10-06).
#
# These are muhammad's numbers (2026-10-06) and they deviate from the client's styles
# document, which says "approximately two to four exchanges" for every style. Kept as a
# deliberate deviation, recorded in PORT-STATUS: the styles differ in how much room they
# give before structure, which one number for all three cannot express.
CADENCE: dict[str, tuple[int, int]] = {
    "direct": (3, 5),
    "supportive": (5, 7),
    "reflective": (6, 8),
}
DEFAULT_CADENCE = CADENCE["supportive"]


class Action(StrEnum):
    CONTINUE = "continue"
    """Stay with them. No offer."""
    ASK = "ask"
    """One question that follows what they said."""
    ASSESS = "assess"
    """They have said something real but it does not point anywhere yet ("I am in pain", "I am
    depressed"). Ask the one thing that would tell these possibilities apart, from what the
    nearest sets of questions still need to know."""
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
    to_find_out: tuple[str, ...] = ()
    """On an ASSESS turn, what the nearest sets of questions still need to know, in the
    frameworks' own words. The model picks the one worth asking; code never scripts it."""
    shortlist: tuple[str, ...] = ()
    """The framework ids `to_find_out` was drawn from. Logged, never sent to the model."""
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
    clarified_already: bool = False,
    fallback: str | None = None,
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
        # so the decision and the offer can never disagree. What is left of the shortlist is
        # still worth asking from, so this becomes an assessment rather than a bare question.
        left = tuple(c.framework_id for c in routing.nearest if c.framework_id not in set(vetoed))
        if left:
            return Decision(
                Action.ASSESS, shortlist=left,
                why=f"{top.framework_id} ruled out by what they said",
            )
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
        # Two real fits, both above the bar. The question that tells them apart is asked once;
        # after it their answer is the evidence for the leader, since asking again loops - the
        # answer says which set fits, not what happened, so it barely moves the vectors.
        #
        if clarified_already:
            if cooldown_passed and their_messages >= soonest:
                return Decision(
                    Action.OFFER_FRAMEWORK, top.framework_id, why="they answered the clarify"
                )
            return Decision(Action.ASK, top.framework_id, why="clarify already asked")
        return Decision(
            Action.CLARIFY,
            top.framework_id,
            separates=(routing.candidates[0].framework_id, routing.candidates[1].framework_id),
            why="two plausible fits",
        )

    # Nothing the conversation points at: the "I am in pain", "I'm depressed" turn. They have
    # said something real that does not name a situation yet, so it is assessed - the nearest
    # sets say what it might be about, and what they still need to know is what is worth
    # asking. Never an offer from here: a shortlist is not a fit.
    if routing.nearest and their_messages < cadence_for(style)[1]:
        return Decision(
            Action.ASSESS,
            shortlist=tuple(c.framework_id for c in routing.nearest),
            why=f"nothing clear yet, nearest {routing.nearest[0].framework_id}",
        )

    # Assessed to the top of the style's window and it still will not resolve to a framework.
    # These go to the fallback rather than to the closest of a shortlist that never separated
    # (muhammad, 2026-10-06): examining what happened and what they made it mean is the one
    # set that fits a situation nothing else named. `fallback` is the framework whose file
    # sets `stuck_offer`, so the choice stays in the content.
    if fallback is not None and cooldown_passed and fallback not in set(vetoed):
        return Decision(Action.OFFER_FRAMEWORK, fallback, why="undeterminable, fallback")

    # Nothing to go on and no fallback to reach for. Follow them; a framework is not owed.
    return Decision(Action.ASK, why="no fit")
