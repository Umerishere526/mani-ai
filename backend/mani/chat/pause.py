# ABOUTME: When a chat pauses on danger (it continues with nothing in place; a symptom in the body needs a refusal), and
# ABOUTME: when a turn after a pause asks whether they are all right. Pure: the turn asks with its read and context.

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Literal

from mani.chat import record
from mani.chat.safety import State
from mani.db.threads import TurnContext
from mani.errors import ErrorCategory, ServiceError
from mani.models.rows import Pause


def pauses_now(
    before: State, after: State, *, help_in_place: bool, declined: bool, about: str | None, danger: str | None,
    symptom_now: str | None, after_return_check: bool, is_return_check: bool, asked: bool, still_there: bool = False,
) -> bool:
    """Danger pauses the chat when nothing is in place and their message did not go toward safety after Mani had
    already answered the danger. After Mani told them what keeps them safe (`before` is danger), any message that
    leaves the danger standing pauses. After Mani only asked what they meant about this kind of worry (`before` is
    unsure and `asked`, safety.asked_about_this), an answer that says it again pauses at once (muhammad, 2026-11-16:
    asked, they say "I just want to die", and the help screen must
    come, every time, with no further question); one that stays unclear is held as danger (safety.after) and gets
    Mani's reply with how to reach help first. After a pause, the first message back never pauses: it always gets
    Mani's reply, which asks how things are (muhammad, 2026-11-16, after the held-back run: "nobody knows where i am"
    and "my dad would pick up" were read as still there and paused again with no word from Mani, three pauses in a
    row). Their answer to that pauses only when it itself says the danger is still there (`still_there`, the read's
    own report of it), and any other answer never pauses. A first
    danger message out of a clear conversation gets Mani's own reply first. Danger to themselves, to someone else or
    from someone pauses without a refusal (2026-11-14: a person about to act, alone, who answered every question
    honestly never paused). A danger `about` a symptom in the body pauses only when this turn's own read (`danger`,
    `symptom_now`) has the symptom happening now and they refuse the help for it (`declined`): pushing back or doubting
    there is never a refusal (2026-11-13). A danger of no known kind needs `declined` too, so a read without `about`
    never pauses a body chat."""
    if about == "body":
        kind_pauses = declined and danger == "now" and symptom_now == "yes"
    else:
        kind_pauses = declined or about is not None
    if is_return_check:
        return False
    if after_return_check:
        # After a pause what was said before it is past: only an answer that itself says the danger is still there
        # pauses again (muhammad's local chat, 2026-11-16: "fine", in answer to how things were, paused the chat,
        # because the read held the words from before the pause against it).
        goes_on = still_there
    elif before is State.UNSURE:
        goes_on = asked and danger == "now"
    else:
        goes_on = before is State.DANGER
    return after is State.DANGER and kind_pauses and not help_in_place and goes_on


@dataclass(frozen=True)
class ReturnCheck:
    """The question how things are now, owed by this turn for pause `pause_id`, with what that pause rested on: in a
    conversation that was paused, or in any other."""

    pause_id: uuid.UUID
    kind: Literal["paused_thread", "other_thread"]
    reason: str | None = None


def return_check(ctx: TurnContext) -> ReturnCheck | None:
    """The return check this turn owes for the person's latest pause that has run out, or None. Each conversation asks
    once per pause (muhammad, 2026-11-13). One whose own pause is the latest, or that has asked about none yet, asks
    with its own pause's reason; any other asks with the latest pause's reason (muhammad, 2026-11-16: what they faced
    is known wherever they come back), until they have said, in any conversation, that they are all right
    (checked_at)."""
    held, own = ctx.pause, ctx.own_pause
    asked = record.return_check_pause(ctx.thread.understanding)
    if held is None or asked == str(held.id):
        return None
    if own is not None and (own.id == held.id or asked is None):
        return ReturnCheck(held.id, "paused_thread", own.reason)
    if held.checked_at is None:
        return ReturnCheck(held.id, "other_thread", held.reason)
    return None


def answering(ctx: TurnContext) -> str | None:
    """The pause whose return check Mani's last reply asked, so this message answers it; None otherwise."""
    return record.return_check_pause(ctx.thread.understanding, state="asked")


def paused_error(pause: Pause) -> ServiceError:
    """The refusal every chat route gives while a person is paused; the client shows the pause from `paused_from` to
    `paused_until`."""
    return ServiceError(
        f"chat for user {pause.user_id} is paused until {pause.ends_at.isoformat()}",
        ErrorCategory.CHAT_PAUSED,
        user_message="Your chat with Mani is paused for now. Please reach out for support.",
        details={"paused_from": pause.started_at.isoformat(), "paused_until": pause.ends_at.isoformat()},
    )
