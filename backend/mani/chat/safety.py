# ABOUTME: Where a conversation stands on safety, and how the model's judgment of each message moves it. The pause
# ABOUTME: rules (chat/pause.py) read the state; code owns it, the model only judges each message.

from __future__ import annotations

from enum import StrEnum


class State(StrEnum):
    CLEAR = "clear"
    UNSURE = "unsure"
    DANGER = "danger"


_JUDGED = {"none": State.CLEAR, "unsure": State.UNSURE, "now": State.DANGER}
_RANK = {State.CLEAR: 0, State.UNSURE: 1, State.DANGER: 2}


def danger_of(danger: str | None, about: str | None, symptom_now: str | None, *, reopening: bool = False) -> str | None:
    """The model's judgment, except for a symptom in the body: it is danger now only when they said it is happening
    now; until they say so it is unsure, which asks (Lolly's chest chat, replayed 2026-11-11: a tightening in the chest
    was read as now and the emergency number went into four replies). A concern that already settled is reopened only by
    their newest message saying so: the stroke chat, replayed 2026-11-11, flipped back to danger on "I am afraid of
    losing him", read from the father's symptoms earlier."""
    if about == "body" and danger in ("now", "unsure") and symptom_now != "yes" and reopening:
        return "none"
    if danger == "now" and about == "body" and symptom_now != "yes":
        return "unsure"
    return danger


# Whose danger a person is asked about once and then held to. A symptom in the body is not one: it is asked whether it
# is happening now, and going on or pushing back settles it.
HELD = ("themselves", "someone_else", "from_someone")


def asked_about_this(state: State, asked_about: str | None, about: str | None) -> bool:
    """Whether Mani had already asked what they meant about this worry before their message. A question about one
    kind of danger is not a question about another (the held-back run, 2026-11-16: asked whether their parents might
    hurt them, a student said "sometimes I just want to disappear for good" and was paused with no word from Mani).
    `asked_about`: the kind the open question was about; `about`: the kind this message's read names. A kind unknown
    on either side counts as asked."""
    return state is State.UNSURE and (asked_about is None or about is None or asked_about == about)


def after(
    state: State, danger: str | None, declined: bool, *, about: str | None = None, asked: bool = False,
) -> State:
    """The state once the model has judged their message: its judgment, except that a refusal never lowers a concern
    (manasa's test, 2026-11-06: Mani agreed to drop the question each time she pushed back), not to unsure from
    danger either, and that a concern about a person is asked about once (muhammad, 2026-11-16: no safety question
    after safety question). `asked`: Mani had already asked what they meant, and an answer that still leaves it unsure
    is held as danger, so the reply says how to reach help and asks nothing more about it; from danger only a judgment
    of none lowers it. No judgment, or one code does not know, leaves it where it is."""
    judged = _JUDGED.get(danger or "")
    if judged is None:
        return state
    if declined and _RANK[judged] < _RANK[state]:
        return state
    if judged is State.UNSURE and about in HELD and (asked or state is State.DANGER):
        return State.DANGER
    return judged
