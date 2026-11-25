# ABOUTME: The reply check: one short model call after the chat call that rewrites, in Mani's reply text, readings said
# ABOUTME: as fact, verdicts on other people and figures of speech, and leaves everything else exactly as it was.
from __future__ import annotations

import asyncio
import dataclasses
import logging

from pydantic import BaseModel, Field

from mani.chat import questions
from mani.chat.reply import TurnReply
from mani.config import Settings
from mani.db import llm_calls
from mani.llm import client

logger = logging.getLogger(__name__)

# The prompt rules against readings said as fact held only some of the time across a day of tests (CQ-13 to DIR-6,
# 2026-11-25), so a second, narrow pass makes the change itself. Wording is ours.
INSTRUCTIONS = """You edit one reply from MANI, a mental-health companion, before it is sent. Change only these, and \
leave every other word exactly as it is:
1. A sentence that states as fact what the person feels, wants, means, why they do something, what their situation \
"really" is, what will happen, or whether a belief of theirs holds, when they did not say it themselves. Rewrite it to \
say only what they said, or remove it. Never turn it into a question.
2. A verdict on someone else in their story ("That's not much to ask of a friend", "she was wrong"). Rewrite it to take \
the person's feeling as real without judging the other person, or remove it.
3. A figure of speech or flowery phrase ("sit with", "stings", "a hard pair", "handing her the win", "the weight in \
it"). Say it in plain everyday words.
Keep anything in quotation marks, any drafted message or email, any phone number, and any line about getting help, \
word for word. Never add a question, advice, or anything new. If nothing needs changing, return the text unchanged \
and an empty list."""


class Checked(BaseModel):
    text: str = Field(description="The reply text with only the changes the instructions allow.")
    changed: list[str] = Field(description="Each original sentence you rewrote or removed, word for word.")


def due(reply: TurnReply, settings: Settings) -> bool:
    """Whether the reply goes through the check: never on a safety turn, whose words are not to be touched."""
    return (settings.reply_check_enabled and reply.safety.level == "none" and bool(reply.text.strip()))


def acceptable(before: str, after: str) -> bool:
    """Whether a rewrite only took things out or reworded them: it asks nothing new, keeps every drafted passage and
    every number, and is not longer than the original."""
    if not after.strip() or len(after) > len(before) * 1.1 + 20 or questions.own_questions(after):
        return False
    kept = all(before[a:b] in after for a, b in questions.drafted(before))
    numbers = all(n in after for n in ("911", "988", "findahelpline") if n in before)
    return kept and numbers


async def checked(call: client.Call[TurnReply], *, said: str, kwargs: dict, settings: Settings) -> tuple[
        client.Call[TurnReply], list[str]]:
    """The chat call with its reply text checked, and the sentences the check changed. Any failure, a slow answer or
    a rewrite that does more than it may leaves the reply exactly as the chat call wrote it."""
    reply = call.value
    if not due(reply, settings):
        return call, []
    try:
        result = await asyncio.wait_for(client.complete(
            [{"role": "system", "content": INSTRUCTIONS},
             {"role": "user", "content": f"What the person just said:\n{said}\n\nMANI's reply:\n{reply.text}"}],
            Checked, model=kwargs["model"], purpose=llm_calls.Purpose.REPLY_CHECK, temperature=0, max_tokens=800,
            reasoning_effort="low", routing=kwargs.get("routing"), user_id=kwargs.get("user_id"),
            thread_id=kwargs.get("thread_id"), settings=settings), timeout=settings.reply_check_seconds)
    except Exception:
        logger.warning("reply check failed; the reply goes out as written", exc_info=True)
        return call, []
    after = result.value.text.strip()
    if after == reply.text.strip() or not acceptable(reply.text, after):
        return call, []
    return dataclasses.replace(call, value=reply.model_copy(update={"text": after})), result.value.changed
