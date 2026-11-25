# ABOUTME: Holds a reply to one question, the one it chose, sent after its text, and says which it asked so the next
# ABOUTME: reply can be told; picks a text's sentences. No model, no judgment of the words.

from __future__ import annotations

import re
from collections.abc import Callable

# A sentence ends at . ? or ! (with any closing quote) when a capital letter or the end of the text follows, so a
# question quoted inside a sentence ('He said "why me?" and left') does not end it.
SENTENCE_END = re.compile(r"[.?!]+[\"'”’)]*(?=\s+[\"“‘(]?[A-Z]|\s*$)")
_CLOSING = "\"'”’)"


def _pieces(text: str) -> list[str]:
    """The text cut at each sentence end, with everything between kept, so joining the pieces gives the text back."""
    pieces, start = [], 0
    for end in SENTENCE_END.finditer(text):
        pieces.append(text[start:end.end()])
        start = end.end()
    pieces.append(text[start:])
    return pieces


def sentences(text: str) -> list[str]:
    """The text's sentences in order, each with its line breaks and runs of spaces folded to one space."""
    return [folded for piece in _pieces(text) if (folded := " ".join(piece.split()))]


# Wording written for them to send, whose questions are theirs to ask, never Mani's: a passage in double quotes, or a
# message laid out as one, from a greeting line ("Hi Sam,", "Dear Ms Lee,", "Subject: …") to its sign-off line.
_GREETING = re.compile(r"^(?:subject:.*|(?:hi|hello|hey|dear)\b[^\n]{0,40},?)\s*$", re.IGNORECASE | re.MULTILINE)
_SIGN_OFF = re.compile(r"^(?:thanks|thank you|best|regards|kind regards|best regards|cheers|sincerely|warmly)\b[^\n]{0,20},?\s*$",
                       re.IGNORECASE | re.MULTILINE)


def drafted(text: str) -> list[tuple[int, int]]:
    """Where the text holds wording written for them to send: each quoted passage and each laid-out message."""
    spans, start = [], None
    for i, ch in enumerate(text):
        if ch == "“" or (ch == '"' and start is None):
            start = i if start is None else start
        elif ch in "”\"" and start is not None:
            spans.append((start, i + 1))
            start = None
    if start is not None:
        spans.append((start, len(text)))
    for greeting in _GREETING.finditer(text):
        sign_off = _SIGN_OFF.search(text, greeting.end())
        spans.append((greeting.start(), sign_off.end() if sign_off else len(text)))
    return spans


def asks(sentence: str) -> bool:
    """Whether a sentence ends on a question mark, past any closing quote."""
    return sentence.rstrip(_CLOSING).endswith("?")


def own_asking(text: str) -> list[int]:
    """The places (in `_pieces(text)`) of the sentences that ask a question of their own: a question inside wording
    written for them to send is part of that wording, not one Mani asks (muhammad's Directive run, 2026-11-25:
    "Could you confirm a repair date?" was cut out of the text to the landlord)."""
    pieces, spans, at, own = _pieces(text), drafted(text), 0, []
    for i, piece in enumerate(pieces):
        end = at + len(piece.rstrip()) - 1
        if piece.strip() and asks(piece.strip()) and not any(a <= end < b for a, b in spans):
            own.append(i)
        at += len(piece)
    return own


def own_questions(text: str) -> list[str]:
    """The text's own questions, folded, in order (see `own_asking`)."""
    pieces = _pieces(text)
    return [" ".join(pieces[i].split()) for i in own_asking(text)]


def kept(text: str, keep: Callable[[int, str], bool]) -> str:
    """The text with only the sentences `keep` accepts, given each sentence's place among them and its folded words;
    a kept sentence stays exactly as written, and the blank lines left behind are tidied."""
    out, place = [], 0
    for piece in _pieces(text):
        folded = " ".join(piece.split())
        if not folded or keep(place, folded):
            out.append(piece)
        place += bool(folded)
    return _tidied("".join(out))


def _tidied(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", "\n".join(line.rstrip() for line in text.split("\n"))).strip()


def last_question(text: str) -> str:
    """The text's last question of its own (see `own_asking`), folded to one line, or empty when it asks nothing."""
    return next(reversed(own_questions(text)), "")


# What an open-chat question can be for (TurnReply.question.intent): what happened, what it does to them, what they
# tell themselves about it, what they want, or a step on toward the core and the set of questions.
INTENTS = ("situation", "feeling", "belief", "wants", "step")
# What their latest message is, as the reply reads it (TurnReply.question.latest), when it gets no question at all:
# frustration with Mani in the open chat, or a wish to stop wherever no safety worry guards the turn (R95).
FRUSTRATED = "frustrated"
WANTS_TO_STOP = "wants_to_stop"
# Why a reply's questions were left out, by what their message was.
_SILENCED_WHY = {FRUSTRATED: "question after frustration", WANTS_TO_STOP: "question after a wish to stop"}


def in_open_chat(*, in_play: bool, guarded: bool, action: str) -> bool:
    """Whether a reply is in the open chat, where it asks nothing after frustration and the question it asked is kept:
    no set or offer is in play before or after it, no safety worry guards the turn, and the reply offers, finishes or
    stops nothing."""
    return not in_play and not guarded and action in ("none", "library")


def silenced_by(latest: str, *, open_chat: bool) -> str | None:
    """What their message was (`latest`, as the reply reads it) when the reply asks nothing at all: a wish to stop on
    any turn this is asked of, frustration with Mani only in the open chat. Otherwise None."""
    latest = latest.strip().lower()
    if latest == WANTS_TO_STOP or (open_chat and latest == FRUSTRATED):
        return latest
    return None


def held_to_one(text: str, ask: str, *, silenced: str | None) -> tuple[str, str, str | None]:
    """The reply as sent, the one question it asks, and why a question was left out (None when none was). The question
    the reply chose (`ask`) goes after the text, on its own line. A question the text asks as well is taken out, and
    with no `ask` the text keeps its last one where it stands. After frustration with Mani or a wish to stop
    (`silenced`, from `silenced_by`) it asks nothing. Text that asks nothing goes out exactly as written."""
    ask = ask.strip()
    pieces = _pieces(text)
    asking = own_asking(text)
    if silenced:
        cut, ask, why = asking, "", _SILENCED_WHY[silenced] if asking or ask else None
    elif ask:
        cut, why = asking, "question in the text" if asking else None
    else:
        cut, why = asking[:-1], "more than one question" if len(asking) > 1 else None
    if cut:
        # ponytail: a short "I'd like to understand..." line before a cut question can be left standing; drop it too
        # if muhammad sees it in chats.
        text = _tidied("".join(piece for i, piece in enumerate(pieces) if i not in cut))
    if ask:
        return "\n\n".join(part for part in (text.strip(), ask) if part), ask, why
    return text, "" if silenced else last_question(text), why
