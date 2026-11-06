# ABOUTME: The deterministic safety screen, and the conversation's safety state that it and the model's reading move.
# ABOUTME: The screen is free phrase matching, a backstop under the model's reading; code owns the state.

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum

from mani.text import clean_message

# The specification asks for "a safety assessment before framework selection", and separates
# two things the previous implementation collapsed into one. Explicit intent locks the thread.
# Everything else asks the approved safety clarification, because the specification is direct
# about the cost of over-firing:
#
#   "Emotional distress does not automatically mean the user is in immediate danger. Words such
#    as 'depressed,' 'hopeless,' 'panicked,' 'furious,' or 'I cannot do this' require attention
#    and context. They should not automatically produce a crisis response."
#
# Neither level locks the conversation any more (muhammad, 2026-11-06): both open the safety state below, CRISIS at
# unsafe. The model reads every message for safety first (schema.SafetyRead); this screen is the free backstop under it.


class Level(StrEnum):
    NONE = "none"
    CONCERN = "concern"
    CRISIS = "crisis"


class Category(StrEnum):
    SUICIDE = "suicide"
    SELF_HARM = "self_harm"
    HARM_TO_OTHER = "harm_to_other"
    CANNOT_STAY_SAFE = "cannot_stay_safe"
    ABUSE_OR_VIOLENCE = "abuse_or_violence"
    OVERDOSE = "overdose"
    MEDICAL_EMERGENCY = "medical_emergency"
    LOSS_OF_CONTACT = "loss_of_contact_with_reality"


@dataclass(frozen=True)
class Assessment:
    level: Level
    category: Category | None = None
    matched: list[str] = field(default_factory=list)

    @property
    def blocks_framework(self) -> bool:
        """Whether a framework may be offered or continued on this turn.

        The specification: "Avoid continuing the framework until the safety concern has been
        addressed." That applies to a concern as much as to a crisis - the difference is
        whether the thread locks, not whether Mani carries on as though nothing was said.
        """
        return self.level is not Level.NONE


# Explicit intent or a completed act. These lock the thread.
_CRISIS: list[tuple[Category, str]] = [
    (Category.SUICIDE, "kill myself"),
    (Category.SUICIDE, "killing myself"),
    (Category.SUICIDE, "end my life"),
    (Category.SUICIDE, "ending my life"),
    (Category.SUICIDE, "take my own life"),
    (Category.SUICIDE, "taking my own life"),
    (Category.SUICIDE, "commit suicide"),
    (Category.SUICIDE, "want to die"),
    (Category.OVERDOSE, "taken the pills"),
    (Category.OVERDOSE, "took the pills"),
    (Category.OVERDOSE, "taken an overdose"),
    (Category.OVERDOSE, "overdosed"),
    (Category.SELF_HARM, "going to hurt myself"),
    (Category.SELF_HARM, "about to hurt myself"),
    (Category.SELF_HARM, "cut myself"),
    (Category.HARM_TO_OTHER, "going to hurt him"),
    (Category.HARM_TO_OTHER, "going to hurt her"),
    (Category.HARM_TO_OTHER, "going to hurt them"),
    (Category.HARM_TO_OTHER, "going to hurt someone"),
    (Category.HARM_TO_OTHER, "going to kill him"),
    (Category.HARM_TO_OTHER, "going to kill her"),
    (Category.CANNOT_STAY_SAFE, "cannot keep myself safe"),
    (Category.CANNOT_STAY_SAFE, "can not keep myself safe"),
    (Category.CANNOT_STAY_SAFE, "i have a weapon"),
]

# Indirect. The specification lists these verbatim as things a concern "may also be expressed"
# as. They ask for clarification; they do not lock.
_CONCERN: list[tuple[Category, str]] = [
    (Category.SUICIDE, "better off without me"),
    # The specification's sentence is "I do not think I will be here tomorrow", where the
    # negation attaches to "think" rather than to being here. Matching the tail catches both
    # that and "I will not be here tomorrow", at the cost of also catching an ordinary question
    # about tomorrow - which asks one clarifying question and locks nothing.
    (Category.SUICIDE, "be here tomorrow"),
    (Category.SUICIDE, "no point in living"),
    # manasa's chat, 2026-11-05: "I don't want to keep living like this" passed the screen, so the stage moved and the
    # model's safety question came after "D is for Dispute". Ambiguous on purpose: it asks, and locks nothing.
    (Category.SUICIDE, "do not want to keep living"),
    (Category.SUICIDE, "cannot keep living"),
    (Category.SUICIDE, "do not want to go on"),
    (Category.SUICIDE, "do not want to be here"),
    (Category.SUICIDE, "do not want to wake up"),
    (Category.SUICIDE, "i have everything ready"),
    # The specification lists this as needing the safety protocol rather than STOP. Concern
    # level: pills in a hand can be ordinary, and a false crisis locks someone out.
    (Category.OVERDOSE, "pills in my hand"),
    # Passive ideation: a wish not to exist, with no plan or method. Concern, not crisis - it
    # pauses any framework and keeps Mani close without locking the conversation. Whole
    # phrases, so "my keys keep disappearing" or "I did not exist on social media" pass.
    # Added on muhammad's decision (2026-09-23), pending the client's clinical wording.
    (Category.SUICIDE, "want to disappear"),
    # manasa's safety test, 2026-11-06: each of these passed the screen.
    (Category.SUICIDE, "could disappear"),
    (Category.SUICIDE, "not alive anymore"),
    (Category.SUICIDE, "was not alive"),
    (Category.SUICIDE, "were not alive"),
    (Category.SUICIDE, "better off dead"),
    (Category.SUICIDE, "rather be dead"),
    (Category.SUICIDE, "do not care what happens to me"),
    (Category.SELF_HARM, "scared of what i might do"),
    (Category.SELF_HARM, "afraid of what i might do"),
    (Category.SUICIDE, "to disappear from"),
    (Category.SUICIDE, "wish i did not exist"),
    (Category.SUICIDE, "if i did not exist"),
    (Category.SUICIDE, "never been born"),
    (Category.SELF_HARM, "hurt myself"),
    (Category.SELF_HARM, "harm myself"),
    (Category.ABUSE_OR_VIOLENCE, "going to hurt me"),
    (Category.ABUSE_OR_VIOLENCE, "he is outside"),
    (Category.ABUSE_OR_VIOLENCE, "threatened me"),
    (Category.ABUSE_OR_VIOLENCE, "hits me"),
    (Category.ABUSE_OR_VIOLENCE, "hit me"),
    (Category.ABUSE_OR_VIOLENCE, "afraid of him"),
    (Category.ABUSE_OR_VIOLENCE, "afraid of her"),
    (Category.ABUSE_OR_VIOLENCE, "not safe at home"),
    (Category.MEDICAL_EMERGENCY, "cannot breathe"),
    (Category.MEDICAL_EMERGENCY, "chest pain"),
    (Category.MEDICAL_EMERGENCY, "bleeding badly"),
    (Category.LOSS_OF_CONTACT, "hearing voices"),
    (Category.LOSS_OF_CONTACT, "they are watching me"),
]

# Contractions and spacing only. No stemming, no synonyms: a safety screen that guesses is
# worse than one that is narrow and honest about it.
_CONTRACTIONS = {
    "can't": "cannot", "won't": "will not", "don't": "do not", "doesn't": "does not",
    "didn't": "did not", "i'm": "i am", "i've": "i have", "it's": "it is",
    "that's": "that is", "there's": "there is", "isn't": "is not", "aren't": "are not",
    "wasn't": "was not", "couldn't": "could not", "shouldn't": "should not",
    "wouldn't": "would not", "haven't": "have not", "hasn't": "has not", "i'll": "i will",
    "he's": "he is", "she's": "she is", "they're": "they are", "you're": "you are",
}
# Phones type contractions two more ways: iOS turns the apostrophe into a curly one by
# default, and plenty of people leave it out. Both forms must match exactly what the straight
# form matches. "its" and "ill" are left out because they are ordinary words ("its colour",
# "feeling ill") that expanding would corrupt.
_CONTRACTIONS |= {
    key.replace("'", ""): value
    for key, value in _CONTRACTIONS.items()
    if key.replace("'", "") not in {"its", "ill"}
}
_APOSTROPHES = str.maketrans({"\u2019": "'", "\u2018": "'", "\u02bc": "'"})
_CONTRACTION_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _CONTRACTIONS) + r")\b", re.IGNORECASE
)
_PUNCTUATION = re.compile(r"[^\w\s]+")
_WHITESPACE = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Lowercase, expand contractions, drop punctuation, collapse whitespace, so a phrase written
    one way in the specification matches the same sentence typed either way by a person."""
    lowered = clean_message(text).lower().translate(_APOSTROPHES)
    expanded = _CONTRACTION_RE.sub(lambda m: _CONTRACTIONS[m.group(0).lower()], lowered)
    return _WHITESPACE.sub(" ", _PUNCTUATION.sub(" ", expanded)).strip()


# "It hit me so hard" is a figure of speech, and it is the client's own sign that ABCDE fits.
# Only "hit me" with a thing as its subject is set aside; a person hitting them still asks.
_FIGURATIVE_HIT = re.compile(r"\b(it|that|this|what) (really |just |suddenly )?hits? me\b")


# A crisis phrase with a negation just before it ("I'm not going to hurt myself", "I would never kill myself") is not
# the statement it contains: it asks, as a concern, and never counts as a crisis (manasa's test, 2026-11-06, locked on
# "I'm safe. I'm not going to hurt myself").
_NEGATION = re.compile(r"\b(not|never|no)( \w+){0,2} $")


def _negated(normalized: str, phrase: str) -> bool:
    """Whether every place the phrase appears has a negation in the two words before it."""
    at = [i for i in range(len(normalized)) if normalized.startswith(phrase, i)]
    return bool(at) and all(_NEGATION.search(normalized[:i]) for i in at)


def screen(text: str) -> Assessment:
    """Assess one message. Crisis wins over concern; the first category matched is reported."""
    normalized = _FIGURATIVE_HIT.sub(" ", normalize(text))

    crisis_hits = [(c, p) for c, p in _CRISIS if p in normalized and not _negated(normalized, p)]
    if crisis_hits:
        return Assessment(level=Level.CRISIS, category=crisis_hits[0][0], matched=[p for _, p in crisis_hits])
    concern_hits = [(c, p) for c, p in _CRISIS + _CONCERN if p in normalized]
    if concern_hits:
        return Assessment(level=Level.CONCERN, category=concern_hits[0][0], matched=[p for _, p in concern_hits])
    return Assessment(level=Level.NONE)


# ---------------------------------------------------------------------------
# The conversation's safety state (muhammad, 2026-11-06)
# ---------------------------------------------------------------------------
#
# Held on the thread (threads.safety), so a concern outlives the reply that raised it: in manasa's test it was gone
# after one reply, and Mani went back to ordinary conversation each time she pushed back. Code owns it; the screen and
# the model's reading move it. Nothing here locks the conversation.


class State(StrEnum):
    CLEAR = "clear"
    OPEN = "open"
    UNSAFE = "unsafe"


_RANK = {State.CLEAR: 0, State.OPEN: 1, State.UNSAFE: 2}

# Signs that mean danger now, on their own.
DANGER = frozenset({"intent", "plan", "acted", "cannot_stay_safe", "harm_to_others", "medical_emergency"})


def higher(a: State, b: State) -> State:
    return a if _RANK[a] >= _RANK[b] else b


def opened_by(level: Level) -> State:
    """Where the screen alone puts the conversation."""
    return {Level.NONE: State.CLEAR, Level.CONCERN: State.OPEN, Level.CRISIS: State.UNSAFE}[level]


def after(state: State, signals: set[str], answer: str | None) -> State:
    """The state once the model has read this message: `signals` are the signs in it, `answer` how it stands on a
    safety question while one is open. Leaving is slow on purpose: a safe answer closes an open concern, and only
    steps an unsafe one down to open, so "I'm safe" right after plans or means is asked about once more. A refusal,
    a change of subject or an unclear answer keeps it where it is."""
    if answer == "unsafe" or signals & DANGER or (state is not State.CLEAR and "means" in signals):
        return State.UNSAFE
    if signals:
        return higher(state, State.OPEN)
    if answer == "safe":
        return State.OPEN if state is State.UNSAFE else State.CLEAR
    return state
