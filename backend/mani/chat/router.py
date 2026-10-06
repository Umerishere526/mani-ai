# ABOUTME: The few phrase rules about offers that stay in code: an action about to happen, words that rule a framework out, and the stuck check.
# ABOUTME: Which framework fits is the model's judgment (spec 0010); nothing here chooses one.

from __future__ import annotations

from collections.abc import Sequence

from mani.chat.safety import normalize


def _says(phrase: str, normalized: str) -> bool:
    """Whether the phrase occurs as whole words. normalize() leaves single spaces between
    words and no punctuation, so padding both sides is a word boundary: "she hates me" is not
    found in "she hates meetings"."""
    return bool(phrase) and f" {phrase} " in f" {normalized} "


# An action about to happen. Waiting a turn to be sure is the wrong failure here: the message may
# be sent by then, so these phrases put DBT STOP's offer lines in front of the model at once.
URGENT_PHRASES = (
    "about to send", "about to post", "about to call", "about to say something",
    "about to quit", "about to make this purchase", "about to lose it",
    "want to send it", "before i send", "have not sent it", "already wrote the email",
    "i am quitting today", "ending the relationship right now",
    "need to confront her right now", "want to call her right now",
    "keep typing and deleting", "help stopping myself",
)

URGENT_FRAMEWORK = "dbt_stop"


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


# The client's check for a person who keeps saying they do not know or cannot think (the October
# 2026 meeting): a yes to it may bring the stuck framework's offer.
STUCK_CHECK = "Are you feeling stuck"


def stuck_framework(activations: dict[str, dict]) -> str | None:
    """The framework a person who says yes to the stuck check is offered: the one whose file sets
    `stuck_offer: true`."""
    return next(
        (fid for fid, activation in sorted(activations.items()) if activation.get("stuck_offer")),
        None,
    )


def asked_the_check(mani_messages: Sequence[str]) -> bool:
    """Whether one of Mani's messages asked "Are you feeling stuck?", in any case or punctuation."""
    check = normalize(STUCK_CHECK)
    return any(_says(check, normalize(text)) for text in mani_messages)
