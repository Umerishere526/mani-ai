# ABOUTME: When a chat pauses on danger (it continues with nothing in place; a symptom in the body needs a refusal), and
# ABOUTME: when a turn after a pause asks whether they are all right. Pure: the turn asks with its read and context.

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Literal

from mani.chat import context
from mani.chat.safety import State
from mani.db.threads import TurnContext
from mani.errors import ErrorCategory, ServiceError
from mani.models.rows import Pause


def pauses_now(
    before: State, after: State, *, help_in_place: bool, declined: bool, about: str | None, danger: str | None,
    symptom_now: str | None, after_return_check: bool, is_return_check: bool,
) -> bool:
    """Danger now pauses the chat when nothing is in place and it was already danger before this reply or is what
    remains after a return check; the return check itself never does. Danger to themselves, to someone else or from
    someone pauses without a refusal (2026-11-14: a person about to act, alone, who answered every question honestly
    never paused). A danger `about` a symptom in the body pauses only when this turn's own read (`danger`,
    `symptom_now`) has the symptom happening now and they refuse the help for it (`declined`): pushing back or doubting
    there is never a refusal (2026-11-13). A danger of no known kind needs `declined` too, so a read without `about`
    never pauses a body chat."""
    if about == "body":
        kind_pauses = declined and danger == "now" and symptom_now == "yes"
    else:
        kind_pauses = declined or about is not None
    return (
        not is_return_check and after is State.DANGER and kind_pauses and not help_in_place
        and (before is State.DANGER or after_return_check)
    )


@dataclass(frozen=True)
class ReturnCheck:
    """The question whether they are all right now, owed by this turn for pause `pause_id`: in a conversation that was
    paused, which says its own pause's reason, or in any other, which carries nothing from the paused one."""

    pause_id: uuid.UUID
    kind: Literal["paused_thread", "other_thread"]
    reason: str | None = None


def return_check(ctx: TurnContext) -> ReturnCheck | None:
    """The return check this turn owes for the person's latest pause that has run out, or None. Each conversation asks
    once per pause (muhammad, 2026-11-13). One whose own pause is the latest, or that has asked about none yet, asks
    with its own pause's reason; any other asks with nothing from the paused one, until they have said, in any
    conversation, that they are all right (checked_at)."""
    held, own = ctx.pause, ctx.own_pause
    asked = (ctx.thread.understanding.get(context.RETURN_CHECK) or {}).get("pause")
    if held is None or asked == str(held.id):
        return None
    if own is not None and (own.id == held.id or asked is None):
        return ReturnCheck(held.id, "paused_thread", own.reason)
    if held.checked_at is None:
        return ReturnCheck(held.id, "other_thread")
    return None


def answering(ctx: TurnContext) -> str | None:
    """The pause whose return check Mani's last reply asked, so this message answers it; None otherwise."""
    asked = ctx.thread.understanding.get(context.RETURN_CHECK) or {}
    return asked.get("pause") if asked.get("state") == "asked" else None


def paused_error(pause: Pause) -> ServiceError:
    """The refusal every chat route gives while a person is paused; the client shows the pause from `paused_from` to
    `paused_until`."""
    return ServiceError(
        f"chat for user {pause.user_id} is paused until {pause.ends_at.isoformat()}",
        ErrorCategory.CHAT_PAUSED,
        user_message="Your chat with Mani is paused for now. Please reach out for support.",
        details={"paused_from": pause.started_at.isoformat(), "paused_until": pause.ends_at.isoformat()},
    )
