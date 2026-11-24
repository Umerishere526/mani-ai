# ABOUTME: Picks the sentences and the questions out of a reply's text, so the next reply can be told what Mani
# ABOUTME: already asked, and holds an open-chat reply to one question. No model, no judgment of the words.

from __future__ import annotations

import re

# A sentence ends at . ? or ! (with any closing quote) when a capital letter or the end of the text follows, so a
# question quoted inside a sentence ('He said "why me?" and left') does not end it.
SENTENCE_END = re.compile(r"[.?!]+[\"'”’)]*(?=\s+[\"“‘(]?[A-Z]|\s*$)")
_CLOSING = "\"'”’)"


def sentences(text: str) -> list[str]:
    """The text's sentences in order, each with its line breaks and runs of spaces folded to one space."""
    found, start = [], 0
    for end in SENTENCE_END.finditer(text):
        found.append(text[start:end.end()])
        start = end.end()
    found.append(text[start:])
    return [folded for piece in found if (folded := " ".join(piece.split()))]


def _asks(sentence: str) -> bool:
    return sentence.rstrip(_CLOSING).endswith("?")


def asked_in(text: str) -> list[str]:
    """The questions a reply asks: its sentences that end on a question mark."""
    return [sentence for sentence in sentences(text) if _asks(sentence)]


def ends_on_one(text: str) -> bool:
    """Whether the reply's last sentence is a question."""
    found = sentences(text)
    return bool(found) and _asks(found[-1])


# What an open-chat question can be for (TurnReply.question.intent): what happened, what it does to them, what they
# tell themselves about it, what they want, or a step on toward the core and the set of questions.
INTENTS = ("situation", "feeling", "belief", "wants", "step")
# What their latest message is, as the reply reads it (TurnReply.question.latest), when it gets no question at all.
FRUSTRATED = "frustrated"


def in_open_chat(*, in_play: bool, guarded: bool, action: str) -> bool:
    """Whether a reply is in the open chat, where it is held to one question: no set or offer is in play before or
    after it, no safety worry guards the turn, and the reply offers, finishes or stops nothing."""
    return not in_play and not guarded and action in ("none", "library")


def held_to_one(text: str, latest: str) -> tuple[str, str | None]:
    """The reply with the questions the rule refuses taken out, and why: every question when their message is frustrated
    with Mani, otherwise every question but the last. The rest of the text stays exactly as written."""
    pieces, start = [], 0
    for end in SENTENCE_END.finditer(text):
        pieces.append(text[start:end.end()])
        start = end.end()
    pieces.append(text[start:])
    asking = [i for i, piece in enumerate(pieces) if piece.strip() and _asks(piece.strip())]
    frustrated = latest.strip().lower() == FRUSTRATED
    cut = asking if frustrated else asking[:-1]
    if not cut:
        return text, None
    kept = "".join(piece for i, piece in enumerate(pieces) if i not in cut)
    # ponytail: a short "I'd like to understand..." line before a cut question can be left standing; drop it too if
    # muhammad sees it in chats.
    kept = re.sub(r"\n{3,}", "\n\n", "\n".join(line.rstrip() for line in kept.split("\n"))).strip()
    return kept, "question after frustration" if frustrated else "more than one question"
