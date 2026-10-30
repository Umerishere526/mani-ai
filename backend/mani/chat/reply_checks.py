# ABOUTME: Checks on the model's reply that cost no model call: what it missed that code cannot fix.
# ABOUTME: Pure functions, so each check is a unit test; the orchestrator logs the misses.

from __future__ import annotations

import re

from mani.llm.schema import Reply

_QUESTION = re.compile(r"[^.!?\n]*\?")
REPEAT_OVERLAP = 0.7
# Figures of speech people have named as artificial (2026-10), counted in the log, never fixed. Matched as whole
# phrases in a reply.
FIGURES = re.compile(
    r"\b(?:hold(?:ing)? (?:onto|on to|space|you|this|that)|carry(?:ing)? (?:this|that)|sit(?:ting)? with"
    r"|weigh(?:s|ing)? on you)\b",
    re.IGNORECASE,
)
# Words that say nothing about a case, so sharing them is no sign a question carries it.
_COMMON = frozenset({
    "that", "this", "with", "they", "them", "what", "your", "have", "from", "been", "about", "feel", "feels",
    "want", "wants", "means", "mean", "like", "when", "does", "were", "would", "there", "their", "because",
})


def _last_question_words(text: str) -> set[str]:
    questions = _QUESTION.findall(text)
    return set(re.findall(r"[a-z']{4,}", questions[-1].lower())) if questions else set()


def repeats(text: str, last_mani_text: str | None) -> bool:
    """Whether a reply's closing question is, by its words, the question Mani asked last turn.
    A person who answers a question and gets it back unchanged is stuck, however it is reworded."""
    now, before = _last_question_words(text), _last_question_words(last_mani_text or "")
    return bool(now and before and len(now & before) / min(len(now), len(before)) >= REPEAT_OVERLAP)


def figures(text: str) -> list[str]:
    """The figures of speech in a reply, lower-cased, in the order they appear."""
    return [match.group(0).lower() for match in FIGURES.finditer(text)]


def lacks_case(text: str, case: str | None) -> bool:
    """Whether a reply that should carry the case shares no word of substance with it. With no case
    stored there is nothing to carry."""
    wanted = set(re.findall(r"[a-z']{4,}", (case or "").lower())) - _COMMON
    return bool(wanted) and not wanted & set(re.findall(r"[a-z']{4,}", text.lower()))


def misses(
    reply: Reply,
    *,
    offered: str | None,
    offer_dropped: str | None,
    needs_question: bool,
    last_mani_text: str | None,
    reach_unjudged: bool = False,
    case: str | None = None,
) -> list[str]:
    """What the draft got wrong that code cannot fix, named for the log. Empty when it stands.
    None of these costs a second call: they are counted, so how often each happens is known.
    `offered` is the set the sent reply offers, as code rendered it. `reach_unjudged` is a stage the walk reached that the reply left without a
    next_stage judgement. `case` is what they feel and the case they confirmed, given only where the
    stage the reply asks carries the case."""
    notes: list[str] = []
    technique = offered
    if offer_dropped:
        notes.append(f"offer unusable: {offer_dropped}")
    if not technique and repeats(reply.text, last_mani_text):
        notes.append("repeats the last question")
    if needs_question and not technique and "?" not in reply.text:
        notes.append("asks no question")
    if reach_unjudged:
        notes.append("reach unjudged")
    if case is not None and lacks_case(reply.text, case):
        notes.append("case missing")
    if found := figures(reply.text):
        notes.append(f"figure of speech: {', '.join(found)}")
    return notes


# Wording that fixes their situation instead of moving the conversation (the client's test, 2026-10-29: the framework
# is the solution). Moves that clarify, choose where to look, or stay with one thing are allowed, so "could we stay
# with", "it might help to look at" and questions about what they tried are not matched.
SOLUTION = re.compile(
    r"\byou (?:could|might|may want to|can) (?!be\b|feel\b|tell me\b|say\b|share\b|see\b|have\b|also\b|still\b|already\b|notice\b|both\b|love\b|want\b|miss\b)\w+"
    r"|\b(?:try|consider|start) (?:to \w+|\w+ing)\b"
    r"|\bone (?:option|idea|thing you could do) (?:is|would be|might be)\b"
    r"|\b(?:a|the|your) (?:first|next|small) step\b"
    r"|\bwhat if you (?:tried|asked|told|talked|scheduled|planned|set|started)\b"
    r"|\bit (?:might|may|could) help to (?!look\b|think\b|stay\b|talk about\b|understand\b|notice\b)\w+",
    re.IGNORECASE,
)


def solutions(text: str) -> list[str]:
    """The phrases in a chat reply that offer a fix, lower-cased, in order."""
    return [match.group(0).lower() for match in SOLUTION.finditer(text)]


INSIGHT_OVERLAP = 0.5


def _gist(text: str) -> set[str]:
    return set(re.findall(r"[a-z']{4,}", text.lower())) - _COMMON


def repeats_insight(insight: str | None, earlier: list[str] | None) -> bool:
    """Whether an insight says, by its words, what one of the earlier ones said (the client's review, 2026-10-29)."""
    now = _gist(insight or "")
    return bool(now) and any(
        (before := _gist(e)) and len(now & before) / min(len(now), len(before)) >= INSIGHT_OVERLAP for e in earlier or []
    )


def chat_misses(
    text: str, *, shape: str | None, window, insight: str | None, move: str | None, asked_for_help: bool,
    earlier_insights: list[str] | None = None, last_shape: str | None = None,
) -> list[str]:
    """What a chat reply got wrong about the three shapes and the line between moving the conversation and solving
    it, named for the log and the scenario check. Counted, never fixed. One small idea is allowed when they asked."""
    notes: list[str] = []
    fixes = solutions(text)
    if fixes and not (move == "small_idea" and asked_for_help):
        notes.append(f"solution in chat: {', '.join(fixes)}")
    if move == "small_idea" and not asked_for_help:
        notes.append("small idea they did not ask for")
    if shape is None:
        notes.append("no shape")
    tied = [t for t in (getattr(window, "tied_to", None) or []) if t and t.strip()]
    if shape in ("window", "insight") and not tied:
        notes.append(f"{shape} reply ties the feeling to nothing")
    if shape == "insight" and not (insight or "").strip():
        notes.append("insight shape without an insight")
    if insight and solutions(insight):
        notes.append("insight is a solution")
    if shape == "insight" and repeats_insight(insight, earlier_insights):
        notes.append("insight repeats an earlier one")
    if shape == "reflect" and last_shape == "reflect":
        notes.append("reflect two in a row")
    return notes
