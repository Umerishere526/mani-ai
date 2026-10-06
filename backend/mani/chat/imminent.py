# ABOUTME: Whether the person is about to do something they may regret, from their own words.
# ABOUTME: Lexical on purpose: "about to send it" and "I sent it" are near-identical to an embedder.

from __future__ import annotations

from mani.chat.safety import normalize

# The specification's own case for treating an imminent, regrettable action as urgent rather
# than something to wait out for a second message. Taken from the "an action is imminent"
# distinction, which routes to DBT STOP.
#
# This stays phrase matching while framework routing moves to embeddings, for three reasons:
# tense is the whole signal here and cosine similarity cannot see it ("I am about to send it"
# and "I sent it" sit next to each other in embedding space and mean opposite things); it is
# latency-sensitive, so an embedding call that times out must not lose it; and it is one
# function over seventeen phrases.
PHRASES: tuple[str, ...] = (
    "about to send", "about to post", "about to call", "about to say something",
    "about to quit", "about to make this purchase", "about to lose it",
    "want to send it", "before i send", "have not sent it", "already wrote the email",
    "i am quitting today", "ending the relationship right now",
    "need to confront her right now", "want to call her right now",
    "keep typing and deleting", "help stopping myself",
)

# The framework an imminent action routes to.
FRAMEWORK_ID = "dbt_stop"

# How far back the phrase still counts. Further back than their last two messages, an action
# they were about to take has usually either happened or passed.
WINDOW = 2


def _says(phrase: str, normalized: str) -> bool:
    """Whether the phrase occurs as whole words. normalize() leaves single spaces between words
    and no punctuation, so padding both sides is a word boundary."""
    return bool(phrase) and f" {phrase} " in f" {normalized} "


def imminent(messages: list[str]) -> bool:
    """Whether their last two messages say an action is about to be taken."""
    recent = [normalize(text) for text in messages[-WINDOW:]]
    return any(_says(normalize(phrase), text) for text in recent for phrase in PHRASES)
