# ABOUTME: The deterministic safety screen that runs before framework selection.
# ABOUTME: Free - phrase matching in process, no model call, so it cannot be skipped for cost.

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum

from mani.chat import crisis

# The specification asks for "a safety assessment before framework selection", and separates
# two things the previous implementation collapsed into one. Explicit intent locks the thread.
# Everything else asks the approved safety clarification, because the specification is direct
# about the cost of over-firing:
#
#   "Emotional distress does not automatically mean the user is in immediate danger. Words such
#    as 'depressed,' 'hopeless,' 'panicked,' 'furious,' or 'I cannot do this' require attention
#    and context. They should not automatically produce a crisis response."
#
# The asymmetry is deliberate. A false CONCERN costs a clarifying question. A false CRISIS locks
# someone out of the conversation they came for.


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
    (Category.SUICIDE, "do not want to be here"),
    (Category.SUICIDE, "do not want to wake up"),
    (Category.SUICIDE, "want to die"),
    (Category.SUICIDE, "i have everything ready"),
    # Passive ideation: a wish not to exist, with no plan or method. Concern, not crisis - it
    # pauses any framework and keeps Mani close without locking the conversation. Whole
    # phrases, so "my keys keep disappearing" or "I did not exist on social media" pass.
    # Added on muhammad's decision (2026-09-23), pending the client's clinical wording.
    (Category.SUICIDE, "want to disappear"),
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
    """Lowercase, expand contractions, drop punctuation, collapse whitespace.

    Shared with the framework router so a phrase written one way in the specification matches
    the same sentence typed either way by a person.
    """
    lowered = text.lower().translate(_APOSTROPHES)
    expanded = _CONTRACTION_RE.sub(lambda m: _CONTRACTIONS[m.group(0).lower()], lowered)
    return _WHITESPACE.sub(" ", _PUNCTUATION.sub(" ", expanded)).strip()


def screen(text: str) -> Assessment:
    """Assess one message. Crisis wins over concern; the first category matched is reported."""
    normalized = normalize(text)

    for level, patterns in ((Level.CRISIS, _CRISIS), (Level.CONCERN, _CONCERN)):
        hits = [(category, phrase) for category, phrase in patterns if phrase in normalized]
        if hits:
            return Assessment(
                level=level,
                category=hits[0][0],
                matched=[phrase for _, phrase in hits],
            )

    return Assessment(level=Level.NONE)


# ---------------------------------------------------------------------------
# What Mani says
# ---------------------------------------------------------------------------

# Deliberately empty, exactly as crisis.RESOURCES is. The specifications say precisely when the
# safety path fires and what Mani must and must not do, and refer throughout to "MANI's approved
# safety protocol" and "the approved safety clarification" - neither of which they contain.
# Writing that wording is a clinical decision, not an engineering one.
PROTOCOLS: dict[Category, str] = {}

# Likewise: the question Mani asks when the level of danger is uncertain. Until it exists, a
# concern changes routing only - it suppresses the framework and is recorded - and Mani answers
# in its own words rather than reciting something nobody approved.
CLARIFICATION: str | None = None


def protocol_for(category: Category | None) -> str:
    """What to say for a category, falling back so the screen is never blank.

    The implementation this replaces returned an empty string at the moment it mattered most.
    """
    if category is not None and category in PROTOCOLS:
        return PROTOCOLS[category]
    return crisis.CRISIS_REPLY
