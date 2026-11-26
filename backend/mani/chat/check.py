# ABOUTME: The reply repair: code finds the client's rules a reply breaks (a yes/no or either/or question, a figure of
# ABOUTME: speech, a reading said as fact) and only then one short model call rewrites exactly those parts.
from __future__ import annotations

import asyncio
import dataclasses
import logging
import re

from pydantic import BaseModel, Field

from mani.chat import enforce, questions
from mani.chat.reply import TurnReply
from mani.config import Settings
from mani.db import llm_calls
from mani.llm import client

logger = logging.getLogger(__name__)

# A question that can be answered yes or no starts with a helping verb; one that offers a choice joins two options
# with "or" (the client: every question is open, what/how/when/where, never "is it X or Y", 2026-11-20).
_YES_NO = re.compile(r"^[\"'“‘(]?(?:is|are|was|were|am|do|does|did|have|has|had|can|could|would|will|should|shall)\b",
                     re.IGNORECASE)
_EITHER_OR = re.compile(r"\bor\b", re.IGNORECASE)
# Two questions joined into one ("When did it last happen, and how did you find out?"; Directive, 2026-11-25).
_TWO_IN_ONE = re.compile(r"\b(?:and|also)\s+(?:what|how|when|where|who|which|why)\b", re.IGNORECASE)
# A sentence that hands them their own message back: most of its meaningful words are theirs (testers, 2026-11-25:
# "You feel betrayed because she has known you longer and didn't take your side").
_WORD = re.compile(r"[a-z']+")
_SMALL = frozenset("the a an and or but so to of in on at for with you your i me my is are was were be been it its "
                   "that this they them she he her him we our just not do does did have has had".split())
ECHO_SHARE, ECHO_WORDS = 0.6, 4


def _meaningful(text: str) -> list[str]:
    return [w.strip("'") for w in _WORD.findall(text.lower().replace("’", "'")) if w.strip("'") not in _SMALL and len(w) > 2]


def echoes(sentence: str, said: str) -> bool:
    """Whether a sentence is mostly their own message given back to them."""
    words, theirs = _meaningful(sentence), set(_meaningful(said))
    return len(words) >= ECHO_WORDS and sum(w in theirs for w in words) / len(words) >= ECHO_SHARE

INSTRUCTIONS = """You repair one reply from MANI, a mental-health companion, before it is sent. You are told exactly \
which parts break the rules. Change only those parts, keep their meaning, and leave every other word exactly as it is.
- A question named as yes/no or either/or, or as odd or figurative: rewrite it as one plain open question that starts \
with what, how, when, where, which or who, about the same thing.
- A sentence named as a figure of speech: say the same thing in simple everyday English, as a person would text it.
- A reply named as saying he or she: change only those words to "they" (and the verb with it) or their own words for \
the person.
- A sentence named as repeating what they said: replace it as told, never with a question.
- A sentence named as a reading said as fact: say it as a possibility ("I wonder if…") or say only what they said.
Never add a question to the text, advice, or anything new. The text never contains the question: the question goes \
only in `ask`."""


class Repaired(BaseModel):
    text: str = Field(description="The reply text with only the named sentences changed.")
    ask: str = Field(description="The reply's question, rewritten only if it was named; otherwise exactly as given.")


# A reading said as a possibility ("I wonder if…", "maybe", "it might be"): what the client asks for, never repaired.
_TENTATIVE = re.compile(r"\b(?:wonder|maybe|perhaps|might|may|could|possibly|seems?|sounds? like|i guess|i'm guessing|"
                        r"i imagine|if i'm reading|or not|i'm not sure)\b", re.IGNORECASE)


def _closed(question: str) -> str | None:
    """Why a question is not open, or None when it is."""
    question = question.strip()
    if not question:
        return None
    if _YES_NO.match(question):
        return "can be answered yes or no"
    if _EITHER_OR.search(question):
        return "offers a choice between options"
    if _TWO_IN_ONE.search(question):
        return "asks two questions in one: keep only the one that matters most"
    return None


# He or she for someone whose gender they never gave (the 2026-11-25 run: "he" for a boss and a landlord in four
# scenarios). A word for a person that carries it ("my sister") counts as given.
_PRONOUNS = {"he": re.compile(r"\b(he|him|his|himself)\b", re.IGNORECASE),
             "she": re.compile(r"\b(she|her|hers|herself)\b", re.IGNORECASE)}
_GENDERED = {"he": re.compile(r"\b(brother|father|dad|husband|boyfriend|son|uncle|grand(?:father|pa)|nephew|stepdad|"
                               r"stepfather|man|guy|fiance)s?\b", re.IGNORECASE),
             "she": re.compile(r"\b(sister|mother|mom|mum|wife|girlfriend|daughter|aunt|grand(?:mother|ma)|niece|stepmom|"
                               r"stepmother|woman|girl|fiancee)s?\b", re.IGNORECASE)}


def _genders_given(everything: str) -> set[str]:
    return {g for g in _PRONOUNS if _PRONOUNS[g].search(everything) or _GENDERED[g].search(everything)}


def problems(reply: TurnReply, said: str = "", everything: str | None = None) -> list[str]:
    """The client's rules this reply breaks that code can find, each as an instruction naming the exact words. Drafted
    wording written for them to send is theirs and never counted."""
    found, ask = [], reply.question.ask.strip()
    if why := _closed(ask):
        found.append(f'The question "{ask}" {why}.')
    elif ask and enforce.figurative(ask):
        found.append(f'The question "{ask}" uses odd or figurative words: ask it in plain everyday words.')
    if everything is not None:
        given = _genders_given(everything)
        used = {g for g, pattern in _PRONOUNS.items() if pattern.search(f"{reply.text} {ask}")} - given
        for gender in sorted(used):
            found.append(f'The reply says "{gender}" for someone whose gender they have not given: say "they", or their '
                         'own words for the person ("your boss").')
    for reading in reply.readings:
        reading = " ".join(reading.split())
        in_text = reading and reading in " ".join(reply.text.split())
        if in_text and not _TENTATIVE.search(reading):
            found.append(f'The sentence "{reading}" says something they did not say as if it were fact: say it as a '
                         'possibility ("I wonder if…", "It might be that…") or say only what they said.')
    spans = questions.drafted(reply.text)
    for sentence in questions.sentences(reply.text):
        if any(sentence in reply.text[a:b] for a, b in spans):
            continue
        if said and not reply.stage and echoes(sentence, said):
            found.append(f'The sentence "{sentence}" mostly repeats what they just said: replace it with a short line '
                         'that adds something (a link between things they said, or plain warmth), or remove it.')
        elif enforce.figurative(sentence):
            found.append(f'The sentence "{sentence}" is a figure of speech.')
        elif enforce.interpretive(sentence) and sentence not in " ".join(" ".join(r.split()) for r in reply.readings):
            found.append(f'The sentence "{sentence}" is a reading said as fact.')
    return found


def _without_question(text: str, ask: str) -> str:
    """The repaired text without the question when the repair also wrote it there (2026-11-25: a correct repair was
    discarded because the open question it wrote was in the text as well as in `ask`)."""
    folded = " ".join(ask.split())
    if not folded:
        return text
    return questions.kept(text, lambda _, sentence: sentence != folded)


def due(reply: TurnReply, settings: Settings) -> bool:
    """Whether the reply may be repaired: never a safety turn, whose wording is not to be touched (its fixed safety
    question is either/or on purpose)."""
    return settings.reply_check_enabled and reply.safety.level == "none" and bool(reply.text.strip() or reply.question.ask)


def acceptable(before: TurnReply, after: Repaired) -> bool:
    """Whether a repair only changed what it was asked to: the text asks nothing and is not longer, every drafted
    passage and number is kept, and the question, when there is one, is open."""
    text = after.text.strip()
    if not text and before.text.strip():
        return False
    if len(text) > len(before.text) * 1.15 + 20 or questions.own_questions(text):
        return False
    if not all(before.text[a:b] in text for a, b in questions.drafted(before.text)):
        return False
    if not all(n in text for n in ("911", "988", "findahelpline") if n in before.text):
        return False
    return not (before.question.ask.strip() and (not after.ask.strip() or _closed(after.ask)))


async def checked(call: client.Call[TurnReply], *, said: str, kwargs: dict, settings: Settings,
                  everything: str | None = None) -> tuple[
        client.Call[TurnReply], list[str]]:
    """The chat call with its reply repaired where code found a broken rule, and what was found. A reply with nothing
    found goes out at once, with no call; any failure, a slow answer or a repair that does more than it may leaves
    the reply exactly as the chat call wrote it."""
    reply = call.value
    found = problems(reply, said, everything) if due(reply, settings) else []
    if not found:
        return call, []
    named = "\n".join(f"- {problem}" for problem in found)
    try:
        result = await asyncio.wait_for(client.complete(
            [{"role": "system", "content": INSTRUCTIONS},
             {"role": "user", "content": f"What the person just said:\n{said}\n\nMANI's reply text:\n{reply.text}\n\n"
                                         f"MANI's question:\n{reply.question.ask}\n\nWhat to repair:\n{named}"}],
            Repaired, model=kwargs["model"], purpose=llm_calls.Purpose.REPLY_CHECK, temperature=0, max_tokens=800,
            reasoning_effort="low", routing=kwargs.get("routing"), user_id=kwargs.get("user_id"),
            thread_id=kwargs.get("thread_id"), settings=settings), timeout=settings.reply_check_seconds)
    except Exception:
        logger.warning("reply repair failed; the reply goes out as written", exc_info=True)
        return call, []
    repaired_text = _without_question(result.value.text, result.value.ask)
    result = dataclasses.replace(result, value=result.value.model_copy(update={"text": repaired_text}))
    if not acceptable(reply, result.value):
        return call, []
    question = reply.question.model_copy(update={"ask": result.value.ask.strip() or reply.question.ask})
    repaired = reply.model_copy(update={"text": result.value.text.strip(), "question": question})
    return dataclasses.replace(call, value=repaired), found
