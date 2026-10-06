# ABOUTME: Picks the framework that fits from the facts the model reported, by the client's selection table.
# ABOUTME: Also holds the two phrase rules that stay deterministic: an action about to happen, and words that rule one out.

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from mani.chat.safety import normalize


def _says(phrase: str, normalized: str) -> bool:
    """Whether the phrase occurs as whole words. normalize() leaves single spaces between
    words and no punctuation, so padding both sides is a word boundary: "she hates me" is not
    found in "she hates meetings"."""
    return bool(phrase) and f" {phrase} " in f" {normalized} "


# An action about to happen. Waiting a turn to be sure is the wrong failure here: the message may
# be sent by then, so these phrases make DBT STOP the pick without the model's say.
URGENT_PHRASES = (
    "about to send", "about to post", "about to call", "about to say something",
    "about to quit", "about to make this purchase", "about to lose it",
    "want to send it", "before i send", "have not sent it", "already wrote the email",
    "i am quitting today", "ending the relationship right now",
    "need to confront her right now", "want to call her right now",
    "keep typing and deleting", "help stopping myself",
)


def urgent(messages: list[str]) -> bool:
    """Whether one of their two most recent messages says an action is about to happen."""
    recent = [normalize(t) for t in messages[-2:]]
    return any(_says(normalize(phrase), text) for text in recent for phrase in URGENT_PHRASES)


def vetoes(activation: dict, messages: list[str]) -> list[str]:
    """Phrases from a framework's `never_offer_when_said` that the person has used anywhere in the
    conversation. Whole words, so "funeral" is not found in "funeralhome"."""
    texts = [normalize(t) for t in messages]
    return [
        phrase
        for phrase in activation.get("never_offer_when_said") or []
        if any(_says(normalize(phrase), text) for text in texts)
    ]


# The facts the model reports from what the person has said, each with its plain meaning. The
# meaning is the model's definition, the redraft's way of naming what is missing, and the
# Framework Index's description of what each framework needs: one table, so they cannot drift.
# Taken from the client's selection table (six-frameworks-overview.md).
FACTS: dict[str, str] = {
    "event": "a specific thing happened (something someone said or did, a moment, a result)",
    "meaning": "what they took that event to mean about themselves or someone else",
    "painful_thought": 'one specific painful thought, in their words ("nobody cares about me")',
    "low_mood": (
        "low mood, and they have stopped doing things that matter or pulled away from people"
    ),
    "cannot_begin": "they know what they could do but cannot get themselves to begin",
    "practical_problem": (
        "a specific practical problem that a decision or an action could change "
        "(not a general pressure)"
    ),
    "unsure_what_to_do": (
        "they do not know what to do about a situation, or have a decision to make. A bare "
        "\"I don't know\" in answer to your question is not this"
    ),
    "cannot_control": (
        "a specific thing they said they cannot change or control (a loss, someone else's "
        "choice, an outcome still uncertain), and it keeps pulling at them. Pressure from work, "
        "family or life in general is not this"
    ),
    "overwhelmed_now": (
        "right now, in this moment, they are panicked, flooded or too activated to think. "
        "Stress about work or life in general is not this"
    ),
    "about_to_act": (
        "they are about to do something they may regret: send, post, call, confront, quit"
    ),
    "stuck": (
        "they keep saying they do not know, cannot think or are stuck in answer to your "
        "questions (twice or more, in any order), or they answered yes to \"Are you feeling "
        "stuck?\"; after a no to that check, only once they have said it twice more. Quote their "
        "longest stuck words"
    ),
}

# A person stuck while Mani is understanding (spec 0009). It counts only once Mani has asked the
# check, and a set holding it fits only when no other set does, so any full fit wins over it.
STUCK_FACT = "stuck"
STUCK_CHECK = "Are you feeling stuck"

# The two facts about the state they are in now. A panic from eight messages ago is not where
# they are, so these count only when quoted from their latest messages.
CURRENT_FACTS = frozenset({"overwhelmed_now", "about_to_act"})
CURRENT_WINDOW = 2

# One word proves nothing: "me" is in almost every message.
MIN_QUOTE_WORDS = 2

# An id outside FACTS is the model's own text, so the call log keeps no note naming one.
_UNKNOWN_NOTE = "dropped an unknown fact"


@dataclass(frozen=True)
class KeptFacts:
    """The facts that survived the words check, and a note for each one that did not."""

    present: frozenset[str]
    notes: list[str] = field(default_factory=list)
    # Each kept fact's quoted words, as the person typed them.
    words: dict[str, str] = field(default_factory=dict)


def stuck_framework(activations: dict[str, dict]) -> str | None:
    """The framework a person who stays stuck is offered: the one with a fit set holding `stuck`."""
    return next(
        (
            framework_id
            for framework_id, activation in sorted(activations.items())
            if any(STUCK_FACT in fact_set for fact_set in activation.get("fits_when") or [])
        ),
        None,
    )


def asked_the_check(mani_messages: Sequence[str]) -> bool:
    """Whether one of Mani's messages asked "Are you feeling stuck?", in any case or punctuation."""
    check = normalize(STUCK_CHECK)
    return any(_says(check, normalize(text)) for text in mani_messages)


def kept_facts(
    reported: list[tuple[str, str]], messages: list[str], *, mani_messages: Sequence[str] = (),
) -> KeptFacts:
    """The reported facts whose words the person typed, within one of their own messages.

    `reported` is (fact id, quoted words) pairs from the reply; `messages` are the person's own
    messages, oldest first. This proves the words exist, not that they mean the fact. `stuck`
    also needs the check among `mani_messages`, Mani's own messages. Right after the check,
    their whole latest message ("yes") is quote enough for `stuck`, however short.
    """
    normalized = [normalize(text) for text in messages]
    check_asked = asked_the_check(mani_messages)
    check_just_asked = asked_the_check(mani_messages[-1:])
    present: set[str] = set()
    notes: list[str] = []
    kept_words: dict[str, str] = {}
    for fact, words in reported:
        if fact not in FACTS:
            notes.append(f"{_UNKNOWN_NOTE}: {fact}")
            continue
        if fact == STUCK_FACT and not check_asked:
            notes.append(f"dropped {STUCK_FACT} before the check")
            continue
        quote = normalize(words)
        searched = normalized[-CURRENT_WINDOW:] if fact in CURRENT_FACTS else normalized
        answers_check = (
            fact == STUCK_FACT and check_just_asked and bool(quote) and normalized[-1:] == [quote]
        )
        if not answers_check and (
            len(quote.split()) < MIN_QUOTE_WORDS or not any(_says(quote, t) for t in searched)
        ):
            notes.append(f"dropped a fact not in their words: {fact}")
            continue
        present.add(fact)
        kept_words.setdefault(fact, words.strip())
    return KeptFacts(frozenset(present), notes, kept_words)


@dataclass(frozen=True)
class TieRule:
    """One of the client's distinctions between frameworks, as a check on the facts.

    It fires when any of its facts is present, and only reorders frameworks that already fit.
    `over` empty means the rule is absolute: its framework goes first whatever else fits.
    """

    name: str
    facts: tuple[str, ...]
    prefer: str
    over: tuple[str, ...] = ()


# The framework an action about to happen goes to, the phrases or the fact alike.
URGENT_FRAMEWORK = "dbt_stop"

# Ordered: a later rule never undoes an earlier one. Sources are in spec 0005, AC-4.
TIE_RULES: tuple[TieRule, ...] = (
    TieRule("about to act", ("about_to_act",), URGENT_FRAMEWORK),
    TieRule(
        # Not over Structured Problem Solving: someone panicking about a lost wallet can still
        # work through it (ADR 010). Ours, on the client sign off list.
        "overwhelmed right now", ("overwhelmed_now",), "dbt_stop",
        ("behavioral_activation", "act_choice_point", "abcde", "thought_reframe"),
    ),
    TieRule(
        "knows what to do but cannot begin", ("cannot_begin",), "behavioral_activation",
        ("structured_problem_solving", "act_choice_point"),
    ),
    TieRule(
        "cannot be controlled", ("cannot_control",), "act_choice_point",
        ("structured_problem_solving", "abcde", "thought_reframe"),
    ),
    TieRule(
        "does not know what to do", ("unsure_what_to_do",), "structured_problem_solving",
        ("behavioral_activation", "abcde", "thought_reframe"),
    ),
    TieRule("an event is named", ("event",), "abcde", ("thought_reframe",)),
)


def _apply_tie_rules(ordered: list[str], facts: frozenset[str]) -> list[str]:
    """Reorder frameworks by the rules whose facts are present. Never adds one."""
    ordered = list(ordered)
    settled: set[str] = set()
    for rule in TIE_RULES:
        if rule.prefer not in ordered or not any(f in facts for f in rule.facts):
            continue
        if any(framework_id in settled for framework_id in rule.over):
            continue
        index = ordered.index(rule.prefer)
        beaten = [i for i, framework_id in enumerate(ordered) if framework_id in rule.over]
        target = 0 if not rule.over else min(beaten, default=index)
        if target < index:
            ordered.insert(target, ordered.pop(index))
        settled.add(rule.prefer)
    return ordered


@dataclass(frozen=True)
class Fit:
    """Which framework the facts point to.

    `pick` is the framework that fits, after the tie rules. When none fits, `leading` is the one
    with the most of its facts present, and `missing` is the fact it still needs. `stuck_route`
    is true when the pick fits only through a set holding `stuck`.
    """

    facts: frozenset[str]
    pick: str | None = None
    leading: str | None = None
    missing: str | None = None
    stuck_route: bool = False


def choose(
    facts: frozenset[str],
    activations: dict[str, dict],
    order: dict[str, int],
    *,
    excluded: frozenset[str] = frozenset(),
) -> Fit:
    """Apply the client's selection table to the facts.

    `activations` maps a framework id to its activation payload, whose `fits_when` lists the
    fact sets that make it fit. `order` is each framework's display order, the base order before
    the tie rules. `excluded` is what may not be offered now: vetoed, or declined and cooling down.
    """
    offerable = {
        framework_id: [list(s) for s in activation.get("fits_when") or []]
        for framework_id, activation in activations.items()
        if framework_id not in excluded
    }
    sets = {i: [s for s in found if STUCK_FACT not in s] for i, found in offerable.items()}
    stuck_sets = {i: [s for s in found if STUCK_FACT in s] for i, found in offerable.items()}
    by_order = sorted(sets, key=lambda framework_id: (order.get(framework_id, 0), framework_id))

    fitting = [i for i in by_order if any(set(s) <= facts for s in sets[i])]
    if fitting:
        return Fit(facts, pick=_apply_tie_rules(fitting, facts)[0])
    stuck_fitting = [i for i in by_order if any(set(s) <= facts for s in stuck_sets[i])]
    if stuck_fitting:
        return Fit(facts, pick=stuck_fitting[0], stuck_route=True)

    def present(framework_id: str) -> int:
        return max((len(set(s) & facts) for s in sets[framework_id]), default=0)

    most = max((present(i) for i in by_order), default=0)
    if not most:
        return Fit(facts)
    leading = _apply_tie_rules([i for i in by_order if present(i) == most], facts)[0]
    nearest = next(s for s in sets[leading] if len(set(s) & facts) == most)
    missing = next(fact for fact in nearest if fact not in facts)
    return Fit(facts, leading=leading, missing=missing)


def call_log_record(reported: Sequence[str], kept: KeptFacts, fit: Fit) -> dict:
    """What the call log keeps of one draft's facts: ids, the drop notes and what they pointed
    to. Never the quoted words, and never an id outside FACTS, which is the model's own text."""
    return {
        "reported": [fact for fact in reported if fact in FACTS],
        "unknown": sum(fact not in FACTS for fact in reported),
        # What the fit was chosen from: the kept facts, plus about_to_act when it was urgent.
        "facts": sorted(fit.facts),
        "dropped": [note for note in kept.notes if not note.startswith(_UNKNOWN_NOTE)],
        "pick": fit.pick,
        "leading": fit.leading,
        "missing": fit.missing,
        "stuck_route": fit.stuck_route,
    }
