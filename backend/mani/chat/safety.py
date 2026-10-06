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


# Explicit intent, a plan, a method or a completed act. These lock the thread.
#
# Each entry is a phrase matched as whole words against the normalized text, so "want to die"
# is not found in "want to diet". A few are short regular expressions, for a quantity or a
# choice of words; normalize() leaves only lowercase words and single spaces for them to match.
_CRISIS: list[tuple[Category, str]] = [
    (Category.SUICIDE, "kill myself"),
    (Category.SUICIDE, "killing myself"),
    (Category.SUICIDE, "end my life"),
    (Category.SUICIDE, "ending my life"),
    (Category.SUICIDE, "take my own life"),
    (Category.SUICIDE, "taking my own life"),
    (Category.SUICIDE, "commit suicide"),
    (Category.SUICIDE, "want to die"),
    (Category.SUICIDE, "hang myself"),
    (Category.SUICIDE, "hanging myself"),
    # First person and present. "I was suicidal" or "my friend is suicidal" asks instead.
    (
        Category.SUICIDE,
        r"i (am|feel|am feeling|have been|have been feeling)( so| really| very)? suicidal",
    ),
    (Category.SUICIDE, r"rope (is )?ready"),
    (
        Category.SUICIDE,
        r"(wrote|written|writing|left|finished) (my|a|the) (goodbye|suicide) (letter|letters|note|notes)",
    ),
    (Category.OVERDOSE, "taken the pills"),
    (Category.OVERDOSE, "took the pills"),
    (Category.OVERDOSE, "taken an overdose"),
    (Category.OVERDOSE, "overdosed"),
    # A quantity, not a dose: "took 30 tablets", never "took my tablets" or "took 2 tablets".
    (
        Category.OVERDOSE,
        r"(took|taken|swallowed) ([1-9][0-9]+|all (of )?(the|those|these)"
        r"|(a|the) (whole )?(handful|bunch|bottle|box|packet|pack) of)( \w+)? (pills|tablets|painkillers)",
    ),
    (Category.OVERDOSE, r"swallowed (a|the|half a|a whole|the whole) (bottle|box|packet|pack|strip) of"),
    (Category.SELF_HARM, r"(going|about) to (hurt|cut|harm) myself"),
    (Category.HARM_TO_OTHER, "going to hurt him"),
    (Category.HARM_TO_OTHER, "going to hurt her"),
    (Category.HARM_TO_OTHER, "going to hurt them"),
    (Category.HARM_TO_OTHER, "going to hurt someone"),
    (Category.HARM_TO_OTHER, "going to kill him"),
    (Category.HARM_TO_OTHER, "going to kill her"),
    (
        Category.HARM_TO_OTHER,
        r"(confront|attack|stab|threaten|go after|hurt|kill)\w* (him|her|them)"
        r" with (a|my|the) (knife|gun|weapon|blade)",
    ),
    (Category.CANNOT_STAY_SAFE, "cannot keep myself safe"),
    (Category.CANNOT_STAY_SAFE, "can not keep myself safe"),
    (Category.CANNOT_STAY_SAFE, "i have a weapon"),
    (Category.CANNOT_STAY_SAFE, "i have a gun"),
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
    # Its own entry, because a denied phrase is not counted and here the "not" is the statement.
    (Category.SUICIDE, "not be here tomorrow"),
    (Category.SUICIDE, "no point in living"),
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
    (Category.SUICIDE, "to disappear from"),
    (Category.SUICIDE, "wish i did not exist"),
    (Category.SUICIDE, "if i did not exist"),
    (Category.SUICIDE, "never been born"),
    (Category.SELF_HARM, "hurt myself"),
    (Category.SELF_HARM, "harm myself"),
    # Self-harm said without intent asks. An accident is not self-harm.
    (
        Category.SELF_HARM,
        r"(?<!accidentally )cut(ting)? myself(?! (shaving|cooking|chopping|by accident|accidentally|on|while))",
    ),
    # Hyperbole said in exasperation, which asks rather than locks. Only bare, or after a
    # word that makes it a plea - "she will kill me" is an idiom and passes.
    (Category.SUICIDE, r"(^|just |please |fucking |someone |somebody )kill me"),
    # Someone else's safety: Mani asks, and the thread stays the person's own.
    (Category.SUICIDE, r"kill (himself|herself|themselves|themself)"),
    (Category.SUICIDE, r"end (his|her|their) life"),
    (Category.SUICIDE, "suicidal"),
    (Category.ABUSE_OR_VIOLENCE, "going to hurt me"),
    (Category.ABUSE_OR_VIOLENCE, "he is outside"),
    (Category.ABUSE_OR_VIOLENCE, "threatened me"),
    (Category.ABUSE_OR_VIOLENCE, "hits me"),
    (Category.ABUSE_OR_VIOLENCE, "hit me"),
    (Category.ABUSE_OR_VIOLENCE, r"(strangled|strangles|strangling|choked|chokes|choking) me"),
    (Category.ABUSE_OR_VIOLENCE, "afraid of him"),
    (Category.ABUSE_OR_VIOLENCE, "afraid of her"),
    (Category.ABUSE_OR_VIOLENCE, "not safe at home"),
    (
        Category.HARM_TO_OTHER,
        r"kill my (husband|wife|partner|boyfriend|girlfriend|ex|mum|mom|mother|dad|father"
        r"|brother|sister|son|daughter|boss|neighbour|neighbor|flatmate|roommate|baby|child|kids)",
    ),
    (Category.HARM_TO_OTHER, r"want(ed|ing)? to (kill|hurt) (him|her|them|someone|somebody)"),
    (Category.MEDICAL_EMERGENCY, "cannot breathe"),
    (Category.MEDICAL_EMERGENCY, "chest pain"),
    (Category.MEDICAL_EMERGENCY, "bleeding badly"),
    (Category.LOSS_OF_CONTACT, "hearing voices"),
    (Category.LOSS_OF_CONTACT, "they are watching me"),
]

# What kind of concern the model's own flag names: the screen's kinds, and `other` for something it
# thought about that is not danger. Only `other` leaves a running framework going.
OTHER_KIND = "other"
UNSPECIFIED_KIND = "unspecified"
FLAG_KINDS = frozenset(category.value for category in Category) | {OTHER_KIND}


def flag_kind(category: object) -> str:
    """The kind a model flag names, read as text ignoring case, surrounding spaces and trailing
    punctuation, with spaces and hyphens as underscores. A kind that is missing, empty, not text
    or not one of the nine is `unspecified`, never the word the model wrote."""
    if not isinstance(category, str):
        return UNSPECIFIED_KIND
    kind = category.strip().lower().rstrip(".,;:!?").strip().replace(" ", "_").replace("-", "_")
    return kind if kind in FLAG_KINDS else UNSPECIFIED_KIND


def flag_pauses(category: object) -> bool:
    """Whether a model flag pauses a running framework. Everything it cannot read as `other`
    does, so a lost or garbled field can only keep the pause, never remove it."""
    return flag_kind(category) != OTHER_KIND


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


# Spellings used to get past a filter. Digits are read as letters only inside a word that also
# has letters, so "k1ll" is "kill" while "30 tablets" keeps its number. Kept out of normalize(),
# which the framework router shares and which has no reason to read either.
_LEET = str.maketrans("013457", "oieast")
_LEET_WORD = re.compile(r"\b(?=\w*[a-z])\w*\d\w*\b")
_SLANG = {"kms": "kill myself", "unalive": "kill", "unaliving": "killing"}

# A denial reads "I would never ...", "I do not want to ...", "I am not going to ...". Only
# "never", or "not" after one of these, denies: "I could not even kill myself properly" is not
# a denial, and "I do not know, I want to die" stops at "know" before it reaches the "not".
_DENYING_NOT_AFTER = {"do", "does", "did", "will", "would", "am", "is", "are"}
_BETWEEN_DENIAL_AND_PHRASE = {"i", "to", "going", "want", "ever", "really", "even", "actually"}
_DENIAL_REACH = 3

# Said in exasperation rather than as intent. A crisis phrase read this way asks rather than
# locks - "this exam makes me want to kill myself", "I want to die of embarrassment". A
# person who means it is still asked, never ignored.
_HYPERBOLE_BEFORE = (
    "makes me want to", "made me want to", "make me want to", "making me want to", "wanting to",
)
_HYPERBOLE_AFTER = ("of embarrassment", "of shame", "of boredom", "of laughter", "laughing")


def _whole_words(pattern: str) -> re.Pattern[str]:
    return re.compile(rf"(?<!\S)(?:{pattern})(?!\S)")


_CRISIS_RE = [(category, phrase, _whole_words(phrase)) for category, phrase in _CRISIS]
_CONCERN_RE = [(category, phrase, _whole_words(phrase)) for category, phrase in _CONCERN]


def _respell(normalized: str) -> str:
    unleet = _LEET_WORD.sub(lambda m: m.group(0).translate(_LEET), normalized)
    return " ".join(_SLANG.get(word, word) for word in unleet.split())


def _denied(before: list[str]) -> bool:
    for i in range(len(before) - 1, max(len(before) - 1 - _DENIAL_REACH, -1), -1):
        word = before[i]
        if word == "never" or (word == "not" and i > 0 and before[i - 1] in _DENYING_NOT_AFTER):
            return True
        if word not in _BETWEEN_DENIAL_AND_PHRASE:
            return False
    return False


def _hyperbole(before: str, after: str) -> bool:
    # "I have been wanting to…" is a wish held over time, not a word said in exasperation.
    if f" {before}".endswith(" been wanting to"):
        return False
    return any(f" {before}".endswith(f" {lead}") for lead in _HYPERBOLE_BEFORE) or any(
        f"{after} ".startswith(f"{tail} ") for tail in _HYPERBOLE_AFTER
    )


def screen(text: str) -> Assessment:
    """Assess one message. Crisis wins over concern; the first category matched is reported.

    A phrase the person denies is not counted, and a crisis phrase said as hyperbole counts
    as a concern. One undenied, literal occurrence anywhere in the message is enough.
    """
    normalized = _respell(normalize(text))
    hits: dict[Level, list[tuple[Category, str]]] = {Level.CRISIS: [], Level.CONCERN: []}

    for level, patterns in ((Level.CRISIS, _CRISIS_RE), (Level.CONCERN, _CONCERN_RE)):
        for category, phrase, pattern in patterns:
            readings = set()
            for match in pattern.finditer(normalized):
                before = normalized[: match.start()].rstrip()
                if _denied(before.split()):
                    continue
                after = normalized[match.end() :].lstrip()
                hyperbole = level is Level.CRISIS and _hyperbole(before, after)
                readings.add(Level.CONCERN if hyperbole else level)
            for reading in (Level.CRISIS, Level.CONCERN):
                if reading in readings:
                    hits[reading].append((category, phrase))
                    break

    for level in (Level.CRISIS, Level.CONCERN):
        if hits[level]:
            return Assessment(
                level=level,
                category=hits[level][0][0],
                matched=[phrase for _, phrase in hits[level]],
            )

    return Assessment(level=Level.NONE)


# ---------------------------------------------------------------------------
# What Mani says
# ---------------------------------------------------------------------------

# Every word Mani says on the safety path is clinical wording and needs the client's and a
# clinician's sign-off before it ships. Engineering decides when the path fires, never what it
# says: anything beyond crisis.CRISIS_REPLY and crisis.RESOURCES waits for that sign-off.

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
