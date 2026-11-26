# ABOUTME: A model-played person chats with Mani through the real stack (runner.send and the database), tapping buttons
# ABOUTME: it is shown. Usage: python evals/drive.py <style> <turns> "<persona>" ["first message"]; costs real calls.

from __future__ import annotations

import asyncio
import pathlib
import sys
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from urllib.parse import urlparse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from evals.run_eval import structured  # noqa: E402
from mani.auth.jwt import Claims  # noqa: E402
from mani.chat import runner, turn as chat_turn  # noqa: E402
from mani.config import get_settings  # noqa: E402
from mani.db import pool  # noqa: E402

PERSON_MODEL = "openai/gpt-6-luna"
LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")
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
    # What the app was told: the conversation holds a danger after this turn.
    crisis: bool = False

    @property
    def safety(self) -> dict:
        return self.trace.get("safety") or {}


@dataclass
class Conversation:
    style: str
    exchanges: list[Exchange] = field(default_factory=list)
    error: str | None = None
    claims: Claims | None = None
    thread_id: uuid.UUID | None = None


def remote_database_refusal(allow_remote: bool) -> str | None:
    """Why a run that creates test people must not start against this DATABASE_URL, or None when it may."""
    host = urlparse(get_settings().database_url).hostname
    if host in LOCAL_HOSTS or allow_remote:
        return None
    return (f"Refusing to run against database host {host!r}: the run creates test people and conversations. "
            "Use a local or dedicated test database, or pass --allow-remote-db for a test project.")


async def new_person(tag: str) -> tuple[Claims, uuid.UUID]:
    """A fresh person acting as themselves, with a conversation opened for them."""
    user = uuid.uuid4()
    claims = Claims.acting_as(user)
    async with pool.as_admin() as conn:
        await conn.execute("insert into auth.users (id, email) values ($1, $2)", user, f"{tag}.{user}@evals.check")
    async with pool.as_user(claims) as conn:
        thread_id = (await chat_turn.start_thread(conn, claims)).id
    return claims, thread_id


async def converse(style: str, turns: int, persona: str, script: list[str] | None = None,
                   person: tuple[Claims, uuid.UUID] | None = None,
                   until: Callable[[Exchange], bool] | None = None) -> Conversation:
    """A whole conversation, as a new person unless `person` names one and its open conversation. The style is tapped
    first. The person sends `script` in order (a button's exact label taps it), then the model-played persona writes
    the rest; with no persona the conversation ends with the script. It also ends after an exchange `until` accepts."""
    claims, thread_id = person or await new_person("drive")
    script = script or []
    opened = await runner.send(claims, thread_id, style.capitalize())
    shown = [("MANI", opened.content, [])]
    record = Conversation(style=style, claims=claims, thread_id=thread_id)
    buttons: list[str] = []
    for n in range(turns):
        if n < len(script):
            nxt = Next(message=script[n])
        elif persona:
            nxt = await _next(persona, shown)
        else:
            break
        if nxt.done and not nxt.tap and not nxt.message:
            break
        said = nxt.tap or nxt.message
        tapped = bool(nxt.tap) or said in buttons
        started = time.monotonic()
        try:
            got = await runner.send(claims, thread_id, said, uuid.uuid4())
        except Exception as error:  # noqa: BLE001
            record.error = f"{type(error).__name__}: {error}"
            break
        buttons = [p.label for p in got.prompts]
        record.exchanges.append(Exchange(said=said, tapped=tapped, reply=got.content, buttons=buttons,
                                         trace=got.trace or {}, seconds=time.monotonic() - started,
                                         paused=got.paused_until is not None, crisis=got.crisis_detected))
        shown += [("YOU", said, []), ("MANI", got.content, buttons)]
        if got.paused_until is not None or nxt.done or (until is not None and until(record.exchanges[-1])):
            break
    return record


async def _next(persona: str, shown: list[tuple[str, str, list[str]]]) -> Next:
    transcript = "\n".join(f"{who}: {text}" + (f"\n  [buttons: {' | '.join(b)}]" if b else "") for who, text, b in shown)
    async with httpx.AsyncClient() as http:
        return Next.model_validate(await structured(http, get_settings(), PERSON_MODEL, [
            {"role": "system", "content": PERSON.format(brief=persona)},
            {"role": "user", "content": f"The chat so far:\n\n{transcript}\n\nWhat do you do next?"},
        ], Next))


def printed(conversation: Conversation) -> str:
    lines = [f"[style {conversation.style}]"]
    for e in conversation.exchanges:
        safety = e.safety.get("level")
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
        print(printed(await converse(style, int(turns), persona, first[:1])))
    finally:
        await pool.close_pool()


if __name__ == "__main__":
    asyncio.run(_main())
