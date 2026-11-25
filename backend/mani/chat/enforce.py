# ABOUTME: Checks the reply the person is about to receive against the client's rules that code can read, after the
# ABOUTME: model writes and before the text is sent; names every enforcement so the turn trace can count it.

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from mani.chat import questions, record as rec
from mani.chat.repairs import sent_text
from mani.chat.reply import TurnReply

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

# A message that is only a wish to stop (R95; Lolly 2026-11-17: respect a clear request to stop without asking another
# question), with apostrophes left out. It only lets someone leave: it never judges safety and never holds on a
# guarded turn.
STOP_PHRASES = frozenset({
    "im done", "i am done", "thats all", "that is all", "bye", "bye bye", "goodbye", "good bye", "good night",
    "goodnight", "enough for today", "i have to go", "i need to go", "i gotta go", "gotta go", "lets stop",
    "lets stop here", "im good for now", "i am good for now",
})
# What may come with a stop in the same message and leave it a stop: "ok, I'm done for now. thanks!"
_STOP_ENDINGS = (" for now", " for today", " now", " here", " then")
_COURTESIES = frozenset({"ok", "okay", "alright", "all right", "yes", "yeah", "yep", "no", "nope", "thanks",
                         "thank you", "thanks mani", "thank you mani", "cheers", "take care", "see you", "cool"})
_CLAUSE = re.compile(r"[.,!?;:\n]+")

# Directive is two or three short sentences, its question included (mani.md, "Your style").
DIRECTIVE_SENTENCES = 3
_LIST_LINE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s", re.MULTILINE)
# Words that open a sentence leaning on the one before it, so it cannot follow a cut: "So what would you try?"
_LEANS_BACK = ("and", "but", "so", "because", "which", "then", "or", "also", "that's why", "this is why")

# A first sentence this short that repeats an opener is a stock opening ("That makes sense."), which can go when what
# follows it still stands.
STOCK_OPENING_WORDS = 6

# Figurative phrases the client flagged as constructed rather than conversational (Manasa, 2026-11-25). Only recorded
# with the phrase, never rewritten: a phrase can be literal ("the loop" of a running track), and the prompt is the fix.
FIGURATIVE_PHRASES = ("its own kind of", "a strange shape", "nice shape", "holding the thread", "cast in", "the loop")
_FIGURATIVE = re.compile(rf"\b(?:{'|'.join(re.escape(phrase) for phrase in FIGURATIVE_PHRASES)})\b", re.IGNORECASE)

# Enforcement events, as the turn trace records them under `enforced`. A word swap is recorded with its word.
REPEATED_QUESTION = "repeated_question"
TYPED_STOP = "typed_stop"
DIRECTIVE_TRIMMED = "directive_trimmed"
DIRECTIVE_LONG_KEPT = "directive_long_kept"
OPENER_DROPPED = "opener_dropped"
SECOND_QUESTION_REMOVED = "second_question_removed"
SECOND_QUESTION_KEPT = "second_question_kept"
OPENER_REPEATED_KEPT = "opener_repeated_kept"
FORBIDDEN_WORD = "forbidden_word"
BANNED_LINE_REMOVED = "banned_line_removed"
BANNED_LINE_KEPT = "banned_line_kept"
FIGURATIVE = "figurative"

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


def figurative(text: str) -> list[str]:
    """The events for the figurative phrases the text uses, one per phrase, recorded with it; the text is unchanged."""
    return [f"{FIGURATIVE}:{phrase}" for phrase in sorted({match.lower() for match in _FIGURATIVE.findall(text)})]


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


def _stop_clause(clause: str) -> bool:
    """Whether one clause is a stop phrase, with a courtesy before it ("ok bye") or an ending after it allowed."""
    first, _, rest = clause.partition(" ")
    if first in _COURTESIES and rest and _stop_clause(rest):
        return True
    for ending in ("", *_STOP_ENDINGS):
        if clause.endswith(ending) and clause[: len(clause) - len(ending)].strip() in STOP_PHRASES:
            return True
    return False


def typed_stop(message: str) -> bool:
    """Whether their message is only a wish to stop: a stop phrase, with nothing beside it but a courtesy ("ok",
    "thanks"). "I'm done with my job" and "bye, she said" are not one."""
    plain = message.lower().replace("’", "'").replace("'", "")
    clauses = [" ".join(re.sub(r"[^a-z ]", " ", clause).split()) for clause in _CLAUSE.split(plain)]
    clauses = [clause for clause in clauses if clause]
    return (any(_stop_clause(clause) for clause in clauses)
            and all(_stop_clause(clause) or clause in _COURTESIES for clause in clauses))


def read_stop(reply: TurnReply, message: str, *, guarded: bool) -> tuple[TurnReply, list[str]]:
    """The reply read as a wish to stop when their message typed one and the model did not read it so, and the event.
    A guarded turn is never read this way: a stop phrase only lets someone leave, and never settles a worry."""
    if guarded or reply.question.latest.strip().lower() == questions.WANTS_TO_STOP or not typed_stop(message):
        return reply, []
    question = reply.question.model_copy(update={"latest": questions.WANTS_TO_STOP})
    return reply.model_copy(update={"question": question}), [TYPED_STOP]


def _leans_back(sentence: str) -> bool:
    plain = sentence.lower().replace("’", "'")
    return any(plain == word or plain.startswith(f"{word} ") or plain.startswith(f"{word},") for word in _LEANS_BACK)


def _split_question(text: str, asked: str) -> tuple[str, str]:
    """The text before its question and the question with what joins it, or the whole text and "" when the question
    does not end it."""
    if asked and text.endswith(asked):
        body = text[: len(text) - len(asked)].rstrip()
        return body, text[len(body):]
    return text, ""


def directive_trimmed(text: str, asked: str) -> tuple[str, list[str]]:
    """A Directive reply cut to its first sentences so that, with its question, it says DIRECTIVE_SENTENCES at most,
    and the event. It is cut only where it still reads whole: the cut ends on a full sentence, no list is broken, and
    the question does not lean on a sentence cut away. Otherwise it goes out as written, recorded as kept long."""
    sentences = questions.sentences(text)
    if len(sentences) <= DIRECTIVE_SENTENCES:
        return text, []
    body, question = _split_question(text, asked)
    room = DIRECTIVE_SENTENCES - len(questions.sentences(question))
    trimmed = questions.kept(body, lambda place, _: place < room)
    whole = (room >= 1 and (not asked or question) and not _LIST_LINE.search(body)
             and trimmed.rstrip("\"'”’)").endswith((".", "!")) and not _leans_back(question.strip()))
    if not whole:
        return text, [DIRECTIVE_LONG_KEPT]
    return f"{trimmed}{question}", [DIRECTIVE_TRIMMED]


def _opener(text: str) -> str:
    """A reply's first rec.OPENING_WORDS words, lowercased without punctuation, or "" when it has fewer."""
    words = _WORDS.findall(text.lower().replace("’", "'"))
    return " ".join(words[: rec.OPENING_WORDS]) if len(words) >= rec.OPENING_WORDS else ""


def fresh_opener(text: str, openers: list[str], *, guarded: bool) -> tuple[str, list[str]]:
    """The reply without a short stock first sentence when it opens as an earlier reply in this conversation opened
    (`openers`, the replies ledger's "opens"), and the event. The sentence goes only when it asks nothing, the next one
    is a statement that does not lean on it, and the reply then opens afresh; a guarded turn keeps every word. A repeat
    that stays is recorded as kept."""
    used = {_opener(opens) for opens in openers} - {""}
    if _opener(text) not in used:
        return text, []
    sentences = questions.sentences(text)
    first, after = sentences[0], sentences[1] if len(sentences) > 1 else ""
    droppable = (not guarded and after and len(_WORDS.findall(first.lower())) <= STOCK_OPENING_WORDS
                 and not questions.asks(first) and not questions.asks(after) and not _leans_back(after))
    dropped = questions.kept(text, lambda place, _: place > 0) if droppable else ""
    if not dropped or _opener(dropped) in used:
        return text, [OPENER_REPEATED_KEPT]
    return dropped[0].upper() + dropped[1:], [OPENER_DROPPED]


def one_question(text: str, asked: str, *, guarded: bool) -> tuple[str, str, list[str]]:
    """The reply held to its first question, the question it asks, and the event, when it still asks more than one:
    the question it chose may itself ask two, and the second usually follows on from the first ("What do you mean? Do
    you mean X or Y?"). A guarded turn keeps every question, recorded as kept."""
    asking = [sentence for sentence in questions.sentences(text) if questions.asks(sentence)]
    if len(asking) < 2:
        return text, asked, []
    if guarded:
        return text, asked, [SECOND_QUESTION_KEPT]
    first = asking[0]
    return (questions.kept(text, lambda _, sentence: sentence == first or not questions.asks(sentence)), first,
            [SECOND_QUESTION_REMOVED])


def _plain(sentence: str) -> str:
    return " ".join(_WORDS.findall(sentence.lower().replace("’", "'")))


def repeats(text: str, ask: str) -> bool:
    """Whether the question the reply chose (`ask`) is one its text already asks, word for word or nearly."""
    asked = _plain(questions.last_question(ask) or ask)
    if not asked:
        return False
    return any(SequenceMatcher(None, asked, _plain(sentence)).ratio() >= SAME_QUESTION_RATIO
               for sentence in questions.sentences(text) if questions.asks(sentence))


def sent(text: str, ask: str, *, fixed: bool, guarded: bool, open_chat: bool, latest: str, directive: bool,
         helping: bool, openers: list[str]) -> Sent:
    """The model's words as the person receives them (repairs.sent_text), with the client's rules enforced: each
    forbidden word swapped for a plain one, each banned line taken out, and a Directive reply in the open chat that
    gives no help (`helping`) held to DIRECTIVE_SENTENCES, and a stock opening that repeats one of the conversation's
    `openers` dropped; a second question left in it is taken out; a figurative phrase is recorded. A guarded turn keeps every sentence and
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
    text, asked, extra = one_question(text, asked, guarded=guarded)
    enforced += extra
    if directive and open_chat and not guarded and not helping:
        text, trimmed = directive_trimmed(text, asked)
        enforced += trimmed
    text, opened = fresh_opener(text, openers, guarded=guarded)
    enforced += opened
    enforced += figurative(text)
    return Sent(text, asked, cut, enforced)
