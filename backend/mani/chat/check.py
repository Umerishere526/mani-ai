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

INSTRUCTIONS = """You repair one reply from MANI, a mental-health companion, before it is sent. You are told exactly \
which parts break the rules. Change only those parts, keep their meaning, and leave every other word exactly as it is.
- A question named as yes/no or either/or: rewrite it as one open question that starts with what, how, when, where, \
which or who, about the same thing.
- A sentence named as a figure of speech: say the same thing in simple everyday English, as a person would text it.
- A sentence named as a reading said as fact: say it as a possibility ("I wonder if…") or say only what they said.
Never add a question to the text, advice, or anything new."""


class Repaired(BaseModel):
    text: str = Field(description="The reply text with only the named sentences changed.")
    ask: str = Field(description="The reply's question, rewritten only if it was named; otherwise exactly as given.")


def _closed(question: str) -> str | None:
    """Why a question is not open, or None when it is."""
    question = question.strip()
    if not question:
        return None
    if _YES_NO.match(question):
        return "can be answered yes or no"
    if _EITHER_OR.search(question):
        return "offers a choice between options"
    return None


def problems(reply: TurnReply) -> list[str]:
    """The client's rules this reply breaks that code can find, each as an instruction naming the exact words. Drafted
    wording written for them to send is theirs and never counted."""
    found = []
    if why := _closed(reply.question.ask):
        found.append(f'The question "{reply.question.ask.strip()}" {why}.')
    spans = questions.drafted(reply.text)
    for sentence in questions.sentences(reply.text):
        if any(sentence in reply.text[a:b] for a, b in spans):
            continue
        if enforce.figurative(sentence):
            found.append(f'The sentence "{sentence}" is a figure of speech.')
        elif enforce.interpretive(sentence):
            found.append(f'The sentence "{sentence}" is a reading said as fact.')
    return found


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


async def checked(call: client.Call[TurnReply], *, said: str, kwargs: dict, settings: Settings) -> tuple[
        client.Call[TurnReply], list[str]]:
    """The chat call with its reply repaired where code found a broken rule, and what was found. A reply with nothing
    found goes out at once, with no call; any failure, a slow answer or a repair that does more than it may leaves
    the reply exactly as the chat call wrote it."""
    reply = call.value
    found = problems(reply) if due(reply, settings) else []
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
    if not acceptable(reply, result.value):
        return call, []
    question = reply.question.model_copy(update={"ask": result.value.ask.strip() or reply.question.ask})
    repaired = reply.model_copy(update={"text": result.value.text.strip(), "question": question})
    return dataclasses.replace(call, value=repaired), found
