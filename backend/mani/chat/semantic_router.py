# ABOUTME: Which framework the conversation points at, from meaning rather than exact words.
# ABOUTME: No match is an answer, never the nearest neighbour - a wrong offer costs more than a question.

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum

from mani.chat import embed, imminent, vectors

logger = logging.getLogger(__name__)

# Measured against the real framework files and nineteen real messages from
# scripts/eval_conversations.yaml. True matches scored 0.471-0.818 with a margin of
# 0.153-0.484 over the runner-up; non-matches scored 0.249-0.422 with a margin of
# 0.001-0.121. The score bands nearly touch (0.049 apart) and the margin bands do not, so
# the margin is what separates a real match from "everything looks a bit like therapy".
BAR = 0.35
MARGIN = 0.13
FLOOR = 0.30

# Below this, what they are talking about now has little to do with what came before.
TOPIC_CHANGE = 0.55

# Coverage was tried and removed. to_find_out items are instructions to Mani ("the exact
# thought going round, in their words"), not things a person says, so they score 0.12-0.35
# against real messages whether the person has answered them or not - a four-message
# conversation and a one-message one were indistinguishable. Offer timing is the cadence in
# offer.py instead, which is what the client specified anyway.

# How many of their recent messages are read for routing. Not four, and not recency-weighted:
# the old router's weights were a lexical trick, and averaging unrelated messages in embedding
# space blurs both. Two keeps the previous message's context without the drift.
WINDOW = 2


class RouteStatus(StrEnum):
    MATCH = "match"
    """One framework is meaningfully ahead of the others."""
    AMBIGUOUS = "ambiguous"
    """Two or more are plausible and the conversation does not yet separate them."""
    WEAK_MATCH = "weak_match"
    """A direction, but not enough to act on."""
    NO_MATCH = "no_match"
    """Nothing fits. Not a low score to be rounded up - an answer."""


@dataclass(frozen=True)
class Candidate:
    framework_id: str
    score: float
    margin: float
    time_critical: bool = False


# How many frameworks the shortlist names. Three is what a person's opening line can plausibly
# be about; past that the things they have in common are too general to ask a question from.
SHORTLIST = 3


@dataclass(frozen=True)
class Routing:
    status: RouteStatus
    candidates: tuple[Candidate, ...]
    topic_changed: bool = False
    query_text: str = ""
    # The nearest few, whatever the status, ranked. `candidates` is what may be acted on;
    # this is what the conversation looks like it might be about, which is a different
    # question and the one that decides what is worth asking next.
    nearest: tuple[Candidate, ...] = ()

    @property
    def top(self) -> Candidate | None:
        return self.candidates[0] if self.candidates else None


NO_MATCH = Routing(status=RouteStatus.NO_MATCH, candidates=())


def _query(messages: list[str]) -> str:
    """Their opening line and their most recent messages, in the order they said them.

    The opening is what names the situation, and a window of the last two alone dropped it by
    the third turn: a conversation that opened "I am depressed" routed to behavioral
    activation twice and then wandered as soon as those words scrolled out, which is how a
    conversation reached its end without ever being offered anything (muhammad, 2026-10-06).
    Deduplicated, so the first two turns are not the opening twice.
    """
    said = [t.strip() for t in messages if t.strip()]
    if not said:
        return ""
    return "\n".join(dict.fromkeys([said[0], *said[-WINDOW:]]))


def route(
    messages: list[str],
    *,
    index: vectors.FacetIndex | None = None,
    embedder=None,
) -> Routing:
    """Which framework their recent messages point at.

    Never raises: a provider failure returns NO_MATCH, which degrades to "keep talking".
    """
    index = index if index is not None else vectors.load()
    if index is None or not messages:
        return NO_MATCH

    # An imminent action is a tense distinction, which cosine similarity cannot see. It is
    # answered before anything is embedded, and it outranks whatever else is being discussed.
    if imminent.imminent(messages):
        return Routing(
            status=RouteStatus.MATCH,
            candidates=(
                Candidate(imminent.FRAMEWORK_ID, 1.0, 1.0, time_critical=True),
            ),
            query_text=_query(messages),
        )

    query = _query(messages)
    if not query:
        return NO_MATCH

    try:
        embed_fn = embedder or embed.cached
        query_vector = embed_fn([query])[0]
    except AssertionError:
        # A test's own expectation, never a provider failure. Letting this through would
        # turn a broken test into a silent no match.
        raise
    except Exception:
        logger.warning("embedding failed; routing as no match", exc_info=True)
        return NO_MATCH

    scores: dict[str, float] = {}
    for facet in index.of_kind("exemplar"):
        similarity = embed.cosine(query_vector, facet.vector)
        if similarity > scores.get(facet.framework_id, -1.0):
            scores[facet.framework_id] = similarity
    if not scores:
        return NO_MATCH

    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    best_id, best = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0.0
    margin = best - second

    def candidate(framework_id: str, score: float, gap: float) -> Candidate:
        return Candidate(framework_id, score, gap)

    # Carried whatever the status, including no match: "I am in pain" names no framework but
    # the nearest few are what it might be about, which is what decides the next question.
    nearest = tuple(candidate(fid, score, best - score) for fid, score in ranked[:SHORTLIST])

    if best < FLOOR:
        return Routing(RouteStatus.NO_MATCH, (), query_text=query, nearest=nearest)

    if best >= BAR and margin >= MARGIN:
        return Routing(
            RouteStatus.MATCH, (candidate(best_id, best, margin),),
            query_text=query, nearest=nearest,
        )

    if best >= BAR:
        tied = tuple(
            candidate(fid, score, best - score)
            for fid, score in ranked
            if best - score < MARGIN
        )
        return Routing(RouteStatus.AMBIGUOUS, tied, query_text=query, nearest=nearest)

    return Routing(
        RouteStatus.WEAK_MATCH, (candidate(best_id, best, margin),),
        query_text=query, nearest=nearest,
    )
