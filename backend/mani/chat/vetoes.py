# ABOUTME: Rules a framework out when the person's own words say it does not fit, in process.
# ABOUTME: No model call, and it only rules out: which set fits is the model's judgment.

from __future__ import annotations

from mani.chat.safety import normalize


def _says(phrase: str, normalized: str) -> bool:
    """Whether the phrase occurs as whole words. normalize() leaves single spaces between
    words and no punctuation, so padding both sides is a word boundary: "she hates me" is not
    found in "she hates meetings"."""
    return bool(phrase) and f" {phrase} " in f" {normalized} "


def ruled_out(phrases_by_framework: dict[str, list[str]], messages: list[str]) -> list[str]:
    """The ids, in the order given, of every framework with a phrase the person has said as whole
    words in any of `messages`, so "funeral" is not found in "funeralhome".

    `phrases_by_framework` maps a framework id to its `never_offer_when_said`.
    """
    texts = [normalize(message) for message in messages]
    return [
        framework_id
        for framework_id, phrases in phrases_by_framework.items()
        if any(_says(normalize(phrase), text) for phrase in phrases for text in texts)
    ]
