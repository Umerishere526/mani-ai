# ABOUTME: When a turn after a pause asks whether they are all right, and the refusal every chat route gives while a
# ABOUTME: person is paused. Pure: the turn asks with its context.

from __future__ import annotations

import uuid
from dataclasses import dataclass

from mani.chat import record
from mani.db.threads import TurnContext
from mani.errors import ErrorCategory, ServiceError
from mani.models.rows import Pause


@dataclass(frozen=True)
class ReturnCheck:
    """The question how things are now, owed by this turn for pause `pause_id`, with what that pause rested on."""

    pause_id: uuid.UUID
    reason: str | None = None


def return_check(ctx: TurnContext) -> ReturnCheck | None:
    """The return check this turn owes for the person's latest pause that has run out, or None. Every conversation
    asks once per pause, with what that pause rested on, until they have said, in any conversation, that they are all
    right (muhammad, 2026-11-13 and 2026-11-16; 2026-11-19 for the paused conversation too)."""
    held = ctx.pause
    if held is None or held.checked_at is not None or record.return_check_pause(ctx.thread.understanding) == str(held.id):
        return None
    return ReturnCheck(held.id, held.reason)


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
