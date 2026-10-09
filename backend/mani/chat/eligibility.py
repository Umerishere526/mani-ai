# ABOUTME: The two checks on a person's words that code owns: an imminent action, and what rules a framework out.
# ABOUTME: Which framework fits is the model's call, so nothing here scores or ranks; no model call, no dependency.

from __future__ import annotations

from mani.chat.safety import normalize

# The framework for pausing before an action that cannot be taken back.
IMMINENT_ACTION_FRAMEWORK = "dbt_stop"

# The specification treats an imminent, regrettable action as time-critical: waiting for the
# model to be sure, or for a second mention, is the wrong failure mode, so this one distinction
# is decided in code. Whole phrases, matched on the two most recent messages.
IMMINENT_ACTION_PHRASES: tuple[str, ...] = (
    "about to send", "about to post", "about to call", "about to say something",
    "about to quit", "about to make this purchase", "about to lose it",
    "want to send it", "before i send", "have not sent it", "already wrote the email",
    "i am quitting today", "ending the relationship right now",
    "need to confront her right now", "want to call her right now",
    "keep typing and deleting", "help stopping myself",
)


def _says(phrase: str, normalized: str) -> bool:
    """Whether the phrase occurs as whole words. normalize() leaves single spaces between
    words and no punctuation, so padding both sides is a word boundary: "she hates me" is not
    found in "she hates meetings"."""
    return bool(phrase) and f" {phrase} " in f" {normalized} "


def vetoes(activation: dict, messages: list[str]) -> list[str]:
    """Phrases from a framework's `never_offer_when_said` that the person has used anywhere in the
    conversation. Whole words, so "funeral" is not found in "funeralhome"."""
    texts = [normalize(t) for t in messages]
    return [
        phrase
        for phrase in activation.get("never_offer_when_said") or []
        if any(_says(normalize(phrase), text) for text in texts)
    ]


def urgent(messages: list[str]) -> bool:
    """Whether an imminent action appears in the two most recent user messages."""
    recent = [normalize(t) for t in messages[-2:]]
    return any(_says(normalize(phrase), text) for text in recent for phrase in IMMINENT_ACTION_PHRASES)
