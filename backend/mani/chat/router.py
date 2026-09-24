# ABOUTME: Picks which frameworks are worth offering, from phrase patterns, in process.
# ABOUTME: No model call and no dependency, so routing accuracy is a test rather than a bill.

from __future__ import annotations

from dataclasses import dataclass, field

from mani.chat.safety import normalize

# How far back a signal still counts. A person's most recent message is the strongest evidence
# of what they need now; three messages ago is context, not a request.
RECENCY_WEIGHTS = (1.0, 0.6, 0.3)

# A phrase from the framework's own "central indication" is worth more than a phrase from its
# broader "what MANI may hear" list, because the specification wrote it to be discriminating.
STRONG_WEIGHT = 2.0
SIGNAL_WEIGHT = 1.0

# Below this, the shortlist is a suggestion rather than a finding, and the prompt carries
# several one-line indications instead of one framework's full offer guidance.
CONFIDENT_SCORE = 2.0
CONFIDENT_MARGIN = 1.0

# A single phrase, said once, is not the same as an understood situation - it could be an
# offhand line the person moves past a moment later. Confidence requires the match to be
# corroborated: either it recurs across more than one of their recent messages, or more than
# one distinct phrase backs it within the messages seen. One message, one passing phrase, is
# not clarity yet - it is a first hint, and the model still owes the person a clarifying
# question before it names a framework.
MIN_CORROBORATION = 2

# A framework promoted by a discriminator but with no phrase match of its own still needs a
# score, or it sorts below frameworks that matched one incidental phrase.
PROMOTED_FLOOR = 1.5

DEFAULT_LIMIT = 3


def _says(phrase: str, normalized: str) -> bool:
    """Whether the phrase occurs as whole words. normalize() leaves single spaces between
    words and no punctuation, so padding both sides is a word boundary: "she hates me" is not
    found in "she hates meetings"."""
    return bool(phrase) and f" {phrase} " in f" {normalized} "


@dataclass(frozen=True)
class Signal:
    """One framework's case for being offered."""

    framework_id: str
    score: float
    matched: list[str] = field(default_factory=list)
    promoted_by: str | None = None
    spread: int = 0
    """How many distinct recent messages contributed a match - the corroboration count."""
    time_critical: bool = False
    """Promoted by a rule with no `over` list - the specification's own case for treating an
    imminent, regrettable action as urgent rather than something to wait out for a second
    mention. Corroboration exists to stop a passing phrase being read as clarity; here waiting
    is the wrong failure mode, so it is what the exemption is for, not a gap in it."""


@dataclass(frozen=True)
class Rule:
    """One of the specification's "Important Framework Distinctions", as a check.

    `over` empty means the rule is absolute - the specification treats an imminent regrettable
    action as time-critical, so DBT STOP goes first whatever else scored. Otherwise the rule
    only reorders the pair it names, which is what the document actually claims.
    """

    name: str
    phrases: tuple[str, ...]
    prefer: str
    over: tuple[str, ...] = ()

    @property
    def absolute(self) -> bool:
        return not self.over


# Ordered. Taken from "Important Framework Distinctions" and each framework's own section 9.
# ponytail: five named clinical rules, in code rather than data. A seventh framework needing its
# own distinction is a code change - move these into admin.frameworks.activation if that happens
# more than once.
DISCRIMINATORS: tuple[Rule, ...] = (
    Rule(
        name="an action is imminent",
        phrases=(
            "about to send", "about to post", "about to call", "about to say something",
            "about to quit", "about to make this purchase", "about to lose it",
            "want to send it", "before i send", "have not sent it", "already wrote the email",
            "i am quitting today", "ending the relationship right now",
            "need to confront her right now", "want to call her right now",
            "keep typing and deleting", "help stopping myself",
        ),
        prefer="dbt_stop",
    ),
    Rule(
        name="the outcome cannot be controlled",
        phrases=(
            "cannot control", "can not control", "cannot change what happened",
            "cannot make them", "cannot make my family", "may never receive an apology",
            "cannot make the uncertainty go away", "nothing i can do to change",
            "do not want it deciding how i act", "do not want this fear making my decisions",
        ),
        prefer="act_choice_point",
        over=("thought_reframe", "abcde", "structured_problem_solving"),
    ),
    Rule(
        name="knows what to do but cannot begin",
        phrases=(
            "know what to do but", "know what i need to do but", "cannot make myself",
            "cannot get myself to begin", "cannot start", "cannot begin",
            "difficulty beginning", "no motivation", "when i feel ready",
        ),
        prefer="behavioral_activation",
        over=("structured_problem_solving",),
    ),
    Rule(
        name="does not know what to do",
        phrases=(
            "do not know what to do", "do not know where to begin",
            "do not know which option", "do not even know where to begin",
            "need to make a decision", "keep changing my mind",
        ),
        prefer="structured_problem_solving",
        over=("behavioral_activation",),
    ),
    Rule(
        name="a specific event triggered the belief",
        phrases=(
            # Not "she said" or "my manager": mentioning a person is not an activating
            # event, and those lifted ABCDE in nearly any conversation that had one in it.
            "criticized", "criticised", "in front of the team", "what happened was",
            "after that i", "so i must be", "which proves", "it proved",
        ),
        prefer="abcde",
        over=("thought_reframe",),
    ),
)


def _score_one(activation: dict, messages: list[str]) -> tuple[float, list[str], int]:
    """Recency-weighted score for a single framework against recent user messages.

    Also returns the spread: how many distinct messages contributed at least one match, which
    is what tells a single well-matched line apart from a pattern corroborated over time.
    """
    strong = [normalize(p) for p in activation.get("strong_signals", [])]
    signals = [normalize(p) for p in activation.get("signals", [])]

    total = 0.0
    matched: list[str] = []
    contributing_distances: set[int] = set()
    # messages arrive oldest first, as recent_for_context returns them.
    for distance, text in enumerate(reversed(messages)):
        if distance >= len(RECENCY_WEIGHTS):
            break
        recency = RECENCY_WEIGHTS[distance]
        normalized = normalize(text)
        for phrase, weight in [(p, STRONG_WEIGHT) for p in strong] + [
            (p, SIGNAL_WEIGHT) for p in signals
        ]:
            if not _says(phrase, normalized):
                continue
            # Said again in an older message: no second score, but it is corroboration.
            contributing_distances.add(distance)
            if phrase not in matched:
                total += weight * recency
                matched.append(phrase)

    return total, matched, len(contributing_distances)


def _fired(rule: Rule, messages: list[str]) -> bool:
    """Whether a discriminator's phrases appear in the two most recent user messages."""
    recent = [normalize(t) for t in messages[-2:]]
    return any(_says(normalize(phrase), text) for text in recent for phrase in rule.phrases)


def urgent(messages: list[str]) -> bool:
    """Whether the absolute rule fires - an imminent action, which is not worth waiting on."""
    return any(rule.absolute and _fired(rule, messages) for rule in DISCRIMINATORS)


def _promote(signals: list[Signal], rule: Rule) -> list[Signal]:
    """Move the rule's preferred framework ahead of the ones it outranks."""
    ordered = list(signals)
    index = next((i for i, s in enumerate(ordered) if s.framework_id == rule.prefer), None)

    if rule.absolute:
        target = 0
    else:
        beaten = [i for i, s in enumerate(ordered) if s.framework_id in rule.over]
        if not beaten:
            return ordered
        target = min(beaten)
        if index is not None and index < target:
            return ordered

    if index is None:
        promoted = Signal(
            rule.prefer, PROMOTED_FLOOR, [],
            promoted_by=rule.name, spread=0, time_critical=rule.absolute,
        )
    else:
        existing = ordered.pop(index)
        if index < target:
            target -= 1
        promoted = Signal(
            existing.framework_id,
            existing.score,
            existing.matched,
            promoted_by=rule.name,
            spread=existing.spread,
            time_critical=rule.absolute,
        )

    ordered.insert(target, promoted)
    return ordered


def shortlist(
    messages: list[str],
    activations: dict[str, dict],
    *,
    limit: int = DEFAULT_LIMIT,
) -> list[Signal]:
    """Rank the frameworks worth offering, most likely first.

    This narrows; it does not decide. The model chooses from the shortlist and `repairs.apply`
    checks that choice against the registry, exactly as it already does - so a wrong shortlist
    costs relevance, never a bad identifier in the database.

    `messages` are the person's own messages, oldest first. `activations` maps a framework id to
    its `admin.frameworks.activation` payload, so adding a framework stays a content change.
    """
    if not messages or not activations:
        return []

    scored = [
        Signal(framework_id, score, matched, spread=spread)
        for framework_id, activation in activations.items()
        for score, matched, spread in [_score_one(activation, messages)]
        if score > 0
    ]
    scored.sort(key=lambda s: (-s.score, s.framework_id))

    # DISCRIMINATORS is ordered by priority, so a later rule must not undo an earlier one.
    # Without this, a person who says "I do not know where to begin" and then "I know what to
    # do but cannot make myself start" is routed by whichever rule happens to run last.
    settled: set[str] = set()
    for rule in DISCRIMINATORS:
        if rule.prefer not in activations or not _fired(rule, messages):
            continue
        if any(framework_id in settled for framework_id in rule.over):
            continue
        scored = _promote(scored, rule)
        settled.add(rule.prefer)

    return scored[:limit]


def is_confident(signals: list[Signal]) -> bool:
    """Whether the top candidate is clear enough to carry its full offer guidance.

    When it is not, the prompt ships two or three one-line indications instead and lets the
    model choose. Either way it never ships all six.

    Score and margin say the top candidate is a strong, unambiguous match. They do not say the
    situation has actually been established rather than mentioned once in passing - a single
    strong-signal phrase in one message clears both on its own. Corroboration closes that gap:
    either the same framework's phrases showed up in more than one recent message, or more than
    one distinct phrase backed it, before the offer guidance goes out. Below that, the shortlist
    still reaches the prompt as a suggestion, but the model is left to ask rather than offer.

    A time-critical signal skips all of it - the rule's own phrase is the evidence. Corroboration exists to stop a single passing
    phrase from being read as an established situation - a reasonable thing to want when the
    cost of waiting is one more clarifying question. DBT STOP's imminent-action rule is the one
    case where the cost of waiting is the opposite: the action it exists to pause may already
    be sent by the time a second mention would arrive.
    """
    if not signals:
        return False
    top = signals[0]
    # The imminent-action rule's own phrase is the evidence. Holding it to the score bar left
    # STOP, promoted with no phrase of its own, below it for good.
    if top.time_critical:
        return True
    if top.score < CONFIDENT_SCORE:
        return False
    if top.spread < 2 and len(top.matched) < MIN_CORROBORATION:
        return False
    # A distinction rule already chose between the leaders. Measuring the margin against
    # the framework it outranked would refuse every pick it made.
    if top.promoted_by:
        return True
    runner_up = max((s.score for s in signals[1:]), default=0.0)
    return top.score - runner_up >= CONFIDENT_MARGIN
