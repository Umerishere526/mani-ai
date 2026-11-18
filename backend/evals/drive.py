# ABOUTME: A model-played person chats with Mani through the real stack (runner.send and the database), tapping buttons
# ABOUTME: it is shown. Usage: python evals/drive.py <style> <turns> "<persona>" ["first message"]; costs real calls.

from __future__ import annotations

import asyncio
import pathlib
import sys
import time
import uuid
from dataclasses import dataclass, field

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from pydantic import BaseModel, Field  # noqa: E402

from mani.auth.jwt import Claims  # noqa: E402
from mani.chat import runner, turn as chat_turn  # noqa: E402
from mani.db import llm_calls, pool  # noqa: E402
from mani.llm import client  # noqa: E402

PERSON_MODEL = "openai/gpt-6-luna"
PERSON = (
    "You are role-playing a real person using a support chat app called MANI on your phone. {brief}\n"
    "Write like a real person texting: short, casual, sometimes vague, sometimes a typo. Answer what MANI asks only "
    "if you would. If MANI gets you wrong, say so plainly. If MANI repeats itself or asks too much, get a bit "
    "impatient. If buttons are shown, you may tap one by its exact label. Never mention you are role-playing."
)


class Next(BaseModel):
    message: str = Field(description="What you type next, in your own casual words. Empty only when you tap.")
    tap: str | None = Field(default=None, description="The exact label of one shown button you tap instead, or null.")
    done: bool = Field(default=False, description="True when you would close the app now.")


@dataclass
class Exchange:
    said: str
    tapped: bool
    reply: str
    buttons: list[str]
    trace: dict
    seconds: float
    paused: bool


@dataclass
class Conversation:
    style: str
    exchanges: list[Exchange] = field(default_factory=list)
    error: str | None = None


async def converse(style: str, turns: int, persona: str, first: str | None = None, *, claims: Claims | None = None,
                   thread_id: uuid.UUID | None = None) -> Conversation:
    """A whole conversation as a new person, or on `thread_id` for `claims` when given. The style is tapped first."""
    if claims is None:
        user = uuid.uuid4()
        claims = Claims.acting_as(user)
        async with pool.as_admin() as conn:
            await conn.execute("insert into auth.users (id, email) values ($1, $2)", user, f"drive.{user}@evals.check")
    if thread_id is None:
        async with pool.as_user(claims) as conn:
            thread_id = (await chat_turn.start_thread(conn, claims)).id
    opened = await runner.send(claims, thread_id, style.capitalize())
    shown = [("MANI", opened.content, [])]
    record = Conversation(style=style)
    for n in range(turns):
        nxt = Next(message=first) if n == 0 and first else await _next(persona, shown)
        if nxt.done and not nxt.tap and not nxt.message:
            break
        said = nxt.tap or nxt.message
        started = time.monotonic()
        try:
            got = await runner.send(claims, thread_id, said, uuid.uuid4())
        except Exception as error:  # noqa: BLE001
            record.error = f"{type(error).__name__}: {error}"
            break
        buttons = [p.label for p in got.prompts]
        record.exchanges.append(Exchange(said=said, tapped=bool(nxt.tap), reply=got.content, buttons=buttons,
                                         trace=got.trace or {}, seconds=time.monotonic() - started,
                                         paused=got.paused_until is not None))
        shown += [("YOU", said, []), ("MANI", got.content, buttons)]
        if got.paused_until is not None or nxt.done:
            break
    return record


async def _next(persona: str, shown: list[tuple[str, str, list[str]]]) -> Next:
    transcript = "\n".join(f"{who}: {text}" + (f"\n  [buttons: {' | '.join(b)}]" if b else "") for who, text, b in shown)
    call = await client.complete(
        [{"role": "system", "content": PERSON.format(brief=persona)},
         {"role": "user", "content": f"The chat so far:\n\n{transcript}\n\nWhat do you do next?"}],
        Next, model=PERSON_MODEL, purpose=llm_calls.Purpose.CHAT, reasoning_effort="low",
    )
    return call.value


def printed(conversation: Conversation) -> str:
    lines = [f"[style {conversation.style}]"]
    for e in conversation.exchanges:
        safety = (e.trace.get("safety") or {}).get("level")
        lines += [f"YOU{' (tap)' if e.tapped else ''}: {e.said}", f"MANI: {e.reply}"]
        if e.buttons:
            lines.append(f"  [buttons: {' | '.join(e.buttons)}]")
        lines.append(f"  ({e.seconds:.1f}s · action {e.trace.get('action')} · stage {e.trace.get('stage')} · "
                     f"safety {safety}{' · PAUSED' if e.paused else ''})")
    if conversation.error:
        lines.append(f"!! {conversation.error}")
    return "\n".join(lines)


async def _main() -> None:
    style, turns, persona, *first = sys.argv[1:]
    await pool.open_pool()
    try:
        print(printed(await converse(style, int(turns), persona, first[0] if first else None)))
    finally:
        await pool.close_pool()


if __name__ == "__main__":
    asyncio.run(_main())
