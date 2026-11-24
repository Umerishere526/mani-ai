# ABOUTME: Holds a reply to one question, the one it chose, sent after its text, and says which it asked so the next
# ABOUTME: reply can be told; picks a text's sentences. No model, no judgment of the words.

from __future__ import annotations

import re

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


def _asks(sentence: str) -> bool:
    return sentence.rstrip(_CLOSING).endswith("?")


def last_question(text: str) -> str:
    """The text's last sentence that ends on a question mark, folded to one line, or empty when it asks nothing."""
    return next((sentence for sentence in reversed(sentences(text)) if _asks(sentence)), "")


# What an open-chat question can be for (TurnReply.question.intent): what happened, what it does to them, what they
# tell themselves about it, what they want, or a step on toward the core and the set of questions.
INTENTS = ("situation", "feeling", "belief", "wants", "step")
# What their latest message is, as the reply reads it (TurnReply.question.latest), when it gets no question at all.
FRUSTRATED = "frustrated"


def in_open_chat(*, in_play: bool, guarded: bool, action: str) -> bool:
    """Whether a reply is in the open chat, where it asks nothing after frustration and the question it asked is kept:
    no set or offer is in play before or after it, no safety worry guards the turn, and the reply offers, finishes or
    stops nothing."""
    return not in_play and not guarded and action in ("none", "library")


def held_to_one(text: str, ask: str, *, frustrated: bool) -> tuple[str, str, str | None]:
    """The reply as sent, the one question it asks, and why a question was left out (None when none was). The question
    the reply chose (`ask`) goes after the text, on its own line. A question the text asks as well is taken out, and
    with no `ask` the text keeps its last one where it stands. After frustration with Mani (`frustrated`) it asks
    nothing. Text that asks nothing goes out exactly as written."""
    ask = ask.strip()
    pieces = _pieces(text)
    asking = [i for i, piece in enumerate(pieces) if piece.strip() and _asks(piece.strip())]
    if frustrated:
        cut, ask, why = asking, "", "question after frustration" if asking or ask else None
    elif ask:
        cut, why = asking, "question in the text" if asking else None
    else:
        cut, why = asking[:-1], "more than one question" if len(asking) > 1 else None
    if cut:
        text = "".join(piece for i, piece in enumerate(pieces) if i not in cut)
        # ponytail: a short "I'd like to understand..." line before a cut question can be left standing; drop it too
        # if muhammad sees it in chats.
        text = re.sub(r"\n{3,}", "\n\n", "\n".join(line.rstrip() for line in text.split("\n"))).strip()
    if ask:
        return "\n\n".join(part for part in (text.strip(), ask) if part), ask, why
    return text, "" if frustrated else last_question(text), why
