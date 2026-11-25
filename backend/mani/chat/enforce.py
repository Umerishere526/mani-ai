# ABOUTME: Checks the reply the person is about to receive against the client's rules that code can read, after the
# ABOUTME: model writes and before the text is sent; names every enforcement so the turn trace can count it.

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from mani.chat import questions
from mani.chat.repairs import sent_text

# Behavioral Framework: "The following words must never appear in any Mani response."
FORBIDDEN_WORDS = ("heaviest", "weakness", "fixing", "fixed", "space", "broken", "flawed", "stable", "stability",
                   "damaged", "problematic", "baggage", "trauma", "unhealthy", "land", "weak", "toxic", "negative",
                   "struggling", "journey", "landscape")
# Safety Guardrails, section 6: lines Mani never says.
BANNED_PHRASES = ("i am here for you", "i'm here for you", "you are not alone", "you're not alone", "i care about you")
# A plain word for each forbidden one, used when the model still writes it. Each keeps the sentence's grammar in the
# uses seen in the eval and suite runs ("they land hard", "you were struggling", "room to think").
PLAIN_WORDS = {
    "heaviest": "hardest", "weakness": "limit", "fixing": "sorting out", "fixed": "settled", "space": "room",
    "broken": "hurt", "flawed": "imperfect", "stable": "steady", "stability": "steadiness", "damaged": "hurt",
    "problematic": "hard", "baggage": "history", "trauma": "pain", "unhealthy": "unhelpful", "land": "hit",
    "weak": "fragile", "toxic": "hurtful", "negative": "harsh", "struggling": "finding it hard", "journey": "path",
    "landscape": "picture",
}
_FORBIDDEN = re.compile(rf"\b(?:(a|an)(\s+))?({'|'.join(FORBIDDEN_WORDS)})\b", re.IGNORECASE)

# Enforcement events, as the turn trace records them under `enforced`. A word swap is recorded with its word.
REPEATED_QUESTION = "repeated_question"
FORBIDDEN_WORD = "forbidden_word"
BANNED_LINE_REMOVED = "banned_line_removed"
BANNED_LINE_KEPT = "banned_line_kept"

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


def forbidden_words(text: str) -> list[str]:
    """The forbidden words the text uses, each only as a whole word."""
    return sorted({word.lower() for *_, word in _FORBIDDEN.findall(text)})


def banned_phrases(text: str) -> list[str]:
    """The banned lines the text says, with a typographic apostrophe read as a plain one."""
    plain = text.lower().replace("’", "'")
    return [p for p in BANNED_PHRASES if p in plain]


def _swapped(match: re.Match) -> str:
    article, space, word = match.groups()
    plain = PLAIN_WORDS[word.lower()]
    if word[0].isupper():
        plain = plain[0].upper() + plain[1:]
    if not article:
        return plain
    fitting = "an" if plain[0].lower() in "aeiou" else "a"
    return f"{fitting.capitalize() if article[0].isupper() else fitting}{space}{plain}"


def in_plain_words(text: str) -> tuple[str, list[str]]:
    """The text with each forbidden word swapped for its plain word (an article before it kept fitting), and the
    events: one per forbidden word it used."""
    found = forbidden_words(text)
    return _FORBIDDEN.sub(_swapped, text), [f"{FORBIDDEN_WORD}:{word}" for word in found]


def without_banned_lines(text: str, ask: str, *, guarded: bool) -> tuple[str, list[str]]:
    """The text without the sentences that say a banned line, and the events. A question that says one stays, as does
    every sentence of a guarded turn and the text's only words when no question (`ask`) follows; each is recorded as
    kept."""
    if not banned_phrases(f"{text} {ask}"):
        return text, []
    cut = text if guarded else questions.kept(
        text, lambda _, sentence: questions.asks(sentence) or not banned_phrases(sentence))
    if not cut and not ask.strip():
        cut = text
    events = [BANNED_LINE_REMOVED] if cut != text else []
    return cut, [*events, *([BANNED_LINE_KEPT] if banned_phrases(f"{cut} {ask}") else [])]


def _plain(sentence: str) -> str:
    return " ".join(_WORDS.findall(sentence.lower().replace("’", "'")))


def repeats(text: str, ask: str) -> bool:
    """Whether the question the reply chose (`ask`) is one its text already asks, word for word or nearly."""
    asked = _plain(questions.last_question(ask) or ask)
    if not asked:
        return False
    return any(SequenceMatcher(None, asked, _plain(sentence)).ratio() >= SAME_QUESTION_RATIO
               for sentence in questions.sentences(text) if questions.asks(sentence))


def sent(text: str, ask: str, *, fixed: bool, guarded: bool, open_chat: bool, latest: str) -> Sent:
    """The model's words as the person receives them (repairs.sent_text), with the client's rules enforced: each
    forbidden word swapped for a plain one and each banned line taken out. A guarded turn keeps every sentence and
    every question its text asks, so a question it chose that the text already asks is not asked twice. Text that
    carries code's fixed safety words (`fixed`) goes out with no rule applied to it."""
    enforced: list[str] = []
    if fixed:
        return Sent(*sent_text(text, ask, guarded=guarded, open_chat=open_chat, latest=latest))
    text, swapped = in_plain_words(text)
    ask, swapped_in_ask = in_plain_words(ask)
    enforced += sorted({*swapped, *swapped_in_ask})
    text, banned = without_banned_lines(text, ask, guarded=guarded)
    enforced += banned
    if guarded and repeats(text, ask):
        ask = ""
        enforced.append(REPEATED_QUESTION)
    text, asked, cut = sent_text(text, ask, guarded=guarded, open_chat=open_chat, latest=latest)
    return Sent(text, asked, cut, enforced)
