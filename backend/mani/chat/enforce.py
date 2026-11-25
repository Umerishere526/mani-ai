# ABOUTME: Checks the reply the person is about to receive against the client's rules that code can read, after the
# ABOUTME: model writes and before the text is sent; names every enforcement so the turn trace can count it.

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from mani.chat import questions
from mani.chat.repairs import sent_text

# Enforcement events, as the turn trace records them under `enforced`.
REPEATED_QUESTION = "repeated_question"

# How alike two questions may be, word for word, before the second is the first asked again.
SAME_QUESTION_RATIO = 0.85
_WORDS = re.compile(r"[a-z0-9']+")


@dataclass(frozen=True)
class Sent:
    """The reply as it goes out: its text, the one question it asks, why a question was left out (or None), and what
    code enforced on it."""

    text: str
    asked: str
    cut: str | None
    enforced: list[str] = field(default_factory=list)


def _plain(sentence: str) -> str:
    return " ".join(_WORDS.findall(sentence.lower().replace("’", "'")))


def repeats(text: str, ask: str) -> bool:
    """Whether the question the reply chose (`ask`) is one its text already asks, word for word or nearly."""
    asked = _plain(questions.last_question(ask) or ask)
    if not asked:
        return False
    return any(SequenceMatcher(None, asked, _plain(sentence)).ratio() >= SAME_QUESTION_RATIO
               for sentence in questions.sentences(text) if sentence.rstrip("\"'”’)").endswith("?"))


def sent(text: str, ask: str, *, guarded: bool, open_chat: bool, latest: str) -> Sent:
    """The model's words as the person receives them (repairs.sent_text), with the client's rules enforced. A guarded
    turn keeps every question its text asks, so a question it chose that the text already asks is not asked twice."""
    enforced: list[str] = []
    if guarded and repeats(text, ask):
        ask = ""
        enforced.append(REPEATED_QUESTION)
    text, asked, cut = sent_text(text, ask, guarded=guarded, open_chat=open_chat, latest=latest)
    return Sent(text, asked, cut, enforced)
