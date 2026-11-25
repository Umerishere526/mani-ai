# ABOUTME: Where a conversation stands on safety, how the model's judgment of each message moves it, and the client's
# ABOUTME: high-risk phrases that raise a lower judgment to danger. The turn's rule (chat/worry.py) reads the state.

from __future__ import annotations

import re
from enum import StrEnum


class State(StrEnum):
    CLEAR = "clear"
    UNSURE = "unsure"
    DANGER = "danger"


_JUDGED = {"none": State.CLEAR, "unsure": State.UNSURE, "now": State.DANGER}
_RANK = {State.CLEAR: 0, State.UNSURE: 1, State.DANGER: 2}


def danger_of(danger: str | None, about: str | None, symptom_now: str | None, *, reopening: bool = False) -> str | None:
    """The model's judgment, except for a symptom in the body. One judged above none that they have not said stopped is
    danger now: a possible medical emergency gets "call emergency services now" every time (muhammad, 2026-11-18, after
    MiniMax held chest pain with a strange left arm at unsure in 7 of 30 runs); over-triggering is accepted. Their word
    that it stopped holds it at unsure. A concern that already settled is reopened only by their newest message saying
    it is happening: the stroke chat, replayed 2026-11-11, flipped back to danger on "I am afraid of losing him", read
    from the father's symptoms earlier."""
    if about != "body" or danger not in ("now", "unsure"):
        return danger
    if reopening:
        return "now" if symptom_now == "yes" else "none"
    return "unsure" if symptom_now == "no" else "now"


# Whose danger, once the model judged it, a later unsure read of the same worry does not lower. A symptom in the body is
# not one: it is asked whether it is happening now, and going on or pushing back settles it.
HELD = ("themselves", "someone_else", "from_someone")


def after(
    state: State, danger: str | None, declined: bool, *, about: str | None = None, danger_about: str | None = None,
) -> State:
    """The state once the model has judged their message: its judgment, except that a refusal never lowers a concern
    (manasa's test, 2026-11-06: Mani agreed to drop the question each time she pushed back), not to unsure from
    danger either, and that danger about a person is lowered only by a judgment of none of that same worry
    (`danger_about`, the kind the danger was about; unknown counts as the same). Only the model raises a concern to
    danger: an answer it judged unsure stays unsure, however often Mani asked (production, 2026-11-20: loneliness and
    crying after "unsafe with my family" paused the chat), and an unsure read of another kind is not held by danger of
    one (chest pain, then "I wish I weren't here"). No judgment, or one code does not know, leaves it where it is."""
    judged = _JUDGED.get(danger or "")
    if judged is None:
        return state
    if declined and _RANK[judged] < _RANK[state]:
        return state
    if judged is State.UNSURE and about in HELD and state is State.DANGER and danger_about in (None, about):
        return State.DANGER
    return judged


# The client's Risk Classification, section 2 (HIGH_RISK: "ANY = HIGH_RISK"), as exact phrases: a message holding one
# that the model judged below danger is danger about themselves (S3, S4). Short and exact on purpose; it only raises,
# and apostrophes are dropped on both sides so "don't" and "dont" match. PROVISIONAL: clinician sign-off required
# before deploy.
HIGH_RISK_PHRASES = (
    "i want to die", "i dont want to live", "i wish i were dead", "i want to hurt myself", "i feel like ending it",
    "i might kill myself", "i have a plan", "this is my last message", "everyone is better off without me",
    "i gave my things away", "i wrote letters",
)


def _plain(text: str) -> str:
    return " ".join(re.sub(r"['\u2018\u2019]", "", text.lower()).split())


def high_risk(message: str) -> bool:
    """Whether their message holds one of the client's high-risk phrases."""
    plain = _plain(message)
    return any(phrase in plain for phrase in HIGH_RISK_PHRASES)
