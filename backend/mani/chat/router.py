# ABOUTME: Picks which frameworks are worth offering, from phrase patterns, in process.
# ABOUTME: No model call and no dependency, so routing accuracy is a test rather than a bill.

from __future__ import annotations

from dataclasses import dataclass, field

from mani.chat.safety import normalize
from mani.prompts.tuning import RouterTuning


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


@dataclass(frozen=True)
class Rule:
    """One of the specification's "Important Framework Distinctions", as a check.

    `over` empty means the rule is absolute - the specification treats an imminent regrettable
    action as time-critical, so DBT STOP goes first whatever else scored. Otherwise the rule
    only reorders the pair it names, which is what the document actually claims; when neither
    side scored it still offers its preferred framework as a candidate.
    """

    name: str
    phrases: tuple[str, ...]
    prefer: str
    over: tuple[str, ...] = ()
    standalone: bool = False
    """Whether the rule's own phrase is specific enough to put its framework on the shortlist
    when nothing else scored. Most are not: "cannot begin" is also "cannot begin to tell you",
    so those only reorder frameworks that already scored."""

    @property
    def absolute(self) -> bool:
        return not self.over


# The fields of one distinction in a framework file's `activation.distinctions`. The framework
# that holds it is the one the rule prefers.
DISTINCTION_KEYS = frozenset({"name", "priority", "phrases", "over", "standalone"})


def distinction_problem(entry: object) -> str | None:
    """Why one distinction entry, on its own, cannot be a rule, or None when it can."""
    if not isinstance(entry, dict):
        return "a distinction is not a map"
    if extra := sorted(set(entry) - DISTINCTION_KEYS):
        return f"distinction keys not allowed: {', '.join(map(str, extra))}"
    name = entry.get("name")
    if not isinstance(name, str) or not name.strip():
        return "a distinction has no name"
    phrases = entry.get("phrases")
    if not isinstance(phrases, list) or not phrases or not all(
        isinstance(p, str) and p.strip() for p in phrases
    ):
        return f"{name}: phrases must be a non empty list of non empty strings"
    priority = entry.get("priority")
    if isinstance(priority, bool) or not isinstance(priority, int) or priority < 1:
        return f"{name}: priority must be a positive whole number"
    over = entry.get("over", [])
    if not isinstance(over, list) or not all(isinstance(fid, str) for fid in over):
        return f"{name}: over must be a list of framework ids"
    if not isinstance(entry.get("standalone", False), bool):
        return f"{name}: standalone must be true or false"
    return None


def distinction_rules(distinctions: dict[str, list]) -> tuple[list[Rule], list[str]]:
    """The rules every framework's distinctions make, ordered by priority, and why any were left out.

    `distinctions` maps a framework id to its `activation.distinctions` list. A rule is left out
    when it is malformed, names an unknown framework or its own in `over`, reuses a priority
    already taken, or is a second rule with an empty `over`. The seed refuses on any reason; the
    registry logs them and keeps the rest, so a portal edit that skipped the seed still routes.
    """
    problems: list[str] = []
    entries: list[tuple[int, Rule]] = []
    for framework_id, listed in distinctions.items():
        if not isinstance(listed, list):
            problems.append(f"{framework_id}: distinctions is not a list")
            continue
        for entry in listed:
            if problem := distinction_problem(entry):
                problems.append(f"{framework_id}: {problem}")
                continue
            over = tuple(entry.get("over", []))
            if bad := [fid for fid in over if fid == framework_id or fid not in distinctions]:
                problems.append(
                    f"{framework_id}: {entry['name']}: over names {', '.join(bad)}, "
                    "which is unknown or its own"
                )
                continue
            entries.append((entry["priority"], Rule(
                name=entry["name"],
                phrases=tuple(entry["phrases"]),
                prefer=framework_id,
                over=over,
                standalone=entry.get("standalone", False),
            )))

    rules: list[Rule] = []
    taken: set[int] = set()
    for priority, rule in sorted(entries, key=lambda e: e[0]):
        if priority in taken:
            problems.append(f"{rule.prefer}: {rule.name}: priority {priority} is used twice")
            continue
        if rule.absolute and any(r.absolute for r in rules):
            problems.append(f"{rule.prefer}: {rule.name}: a second rule with an empty over")
            continue
        taken.add(priority)
        rules.append(rule)
    return rules, problems


def _score_one(
    activation: dict, messages: list[str], weights: RouterTuning
) -> tuple[float, list[str]]:
    """Recency-weighted score for a single framework against the person's messages."""
    strong = [normalize(p) for p in activation.get("strong_signals", [])]
    signals = [normalize(p) for p in activation.get("signals", [])]

    total = 0.0
    matched: list[str] = []
    # messages arrive oldest first, as recent_for_context returns them.
    for distance, text in enumerate(reversed(messages)):
        recency = weights.recency_weights[min(distance, len(weights.recency_weights) - 1)]
        normalized = normalize(text)
        for phrase, weight in [(p, weights.strong_weight) for p in strong] + [
            (p, weights.signal_weight) for p in signals
        ]:
            # Said again in an older message: no second score.
            if _says(phrase, normalized) and phrase not in matched:
                total += weight * recency
                matched.append(phrase)

    return total, matched


def vetoes(activation: dict, messages: list[str]) -> list[str]:
    """Phrases from a framework's `never_offer_when_said` that the person has used anywhere in the
    conversation. Whole words, as the signals are, so "funeral" is not found in "funeralhome"."""
    texts = [normalize(t) for t in messages]
    return [
        phrase
        for phrase in activation.get("never_offer_when_said") or []
        if any(_says(normalize(phrase), text) for text in texts)
    ]


def _fired(rule: Rule, messages: list[str]) -> bool:
    """Whether a distinction's phrases appear in the two most recent user messages."""
    recent = [normalize(t) for t in messages[-2:]]
    return any(_says(normalize(phrase), text) for text in recent for phrase in rule.phrases)


def urgent(messages: list[str], rules: list[Rule]) -> bool:
    """Whether the absolute rule fires - an imminent action, which is not worth waiting on."""
    return any(rule.absolute and _fired(rule, messages) for rule in rules)


def _promote(signals: list[Signal], rule: Rule, floor: float) -> list[Signal]:
    """Move the rule's preferred framework ahead of the ones it outranks."""
    ordered = list(signals)
    index = next((i for i, s in enumerate(ordered) if s.framework_id == rule.prefer), None)

    if rule.absolute:
        target = 0
    else:
        beaten = [i for i, s in enumerate(ordered) if s.framework_id in rule.over]
        if not beaten and index is None and rule.standalone:
            # Nothing it outranks and nothing scored for it, but the rule's own phrase is
            # evidence enough to put it on the shortlist.
            candidate = Signal(rule.prefer, floor, [], promoted_by=rule.name)
            position = next(
                (i for i, s in enumerate(ordered) if s.score < floor), len(ordered)
            )
            ordered.insert(position, candidate)
            return ordered
        if not beaten:
            return ordered
        target = min(beaten)
        if index is not None and index < target:
            return ordered

    if index is None:
        promoted = Signal(rule.prefer, floor, [], promoted_by=rule.name)
    else:
        existing = ordered.pop(index)
        if index < target:
            target -= 1
        promoted = Signal(
            existing.framework_id, existing.score, existing.matched, promoted_by=rule.name
        )

    ordered.insert(target, promoted)
    return ordered


def shortlist(
    messages: list[str],
    activations: dict[str, dict],
    rules: list[Rule],
    weights: RouterTuning,
) -> list[Signal]:
    """Rank every framework the person's words show signs of, most likely first, uncut.

    This narrows; it does not decide. The model may offer only a set on the shortlist, and only
    when it judges it fits; `guards.check` checks the id against the registry - so a wrong
    shortlist costs relevance, never a bad identifier in the database.

    `messages` are the person's own messages, oldest first. `activations` maps a framework id to
    its `admin.frameworks.activation` payload, and `rules` are the distinctions those payloads
    carry, ordered by priority, so adding a framework stays a content change.
    """
    if not messages or not activations:
        return []

    scored = [
        Signal(framework_id, score, matched)
        for framework_id, activation in activations.items()
        for score, matched in [_score_one(activation, messages, weights)]
        if score > 0
    ]
    scored.sort(key=lambda s: (-s.score, s.framework_id))

    # The rules are ordered by priority, so a later rule must not undo an earlier one.
    # Without this, a person who says "I do not know where to begin" and then "I know what to
    # do but cannot make myself start" is routed by whichever rule happens to run last.
    settled: set[str] = set()
    for rule in rules:
        if rule.prefer not in activations or not _fired(rule, messages):
            continue
        if any(framework_id in settled for framework_id in rule.over):
            continue
        scored = _promote(scored, rule, weights.promoted_floor)
        settled.add(rule.prefer)

    return scored

