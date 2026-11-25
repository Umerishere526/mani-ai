# ABOUTME: When a turn in the conversation a pause began in asks whether they are all right, and the refusal every chat
# ABOUTME: route gives while a person is paused. Pure: the turn asks with its context.

from __future__ import annotations

import uuid
from dataclasses import dataclass

from mani.chat import crisis, record
from mani.db.threads import TurnContext
from mani.errors import ErrorCategory, ServiceError
from mani.models.rows import Pause


@dataclass(frozen=True)
class ReturnCheck:
    """The question how things are now, owed by this turn for pause `pause_id`, with what that pause rested on."""

    pause_id: uuid.UUID
    reason: str | None = None


def return_check(ctx: TurnContext) -> ReturnCheck | None:
    """The return check this turn owes for this conversation's latest pause that has run out, or None. Only the
    conversation the pause began in asks, once per pause, with what that pause rested on; a new conversation opens
    normally and never raises it (Lolly, 2026-11-25: "I do not want my chat's to start this way. Get rid of it.")."""
    held = ctx.pause
    if held is None or record.return_check_pause(ctx.thread.understanding) == str(held.id):
        return None
    return ReturnCheck(held.id, held.reason)


def answering(ctx: TurnContext) -> str | None:
    """The pause whose return check Mani's last reply asked, so this message answers it; None otherwise."""
    return record.return_check_pause(ctx.thread.understanding, state="asked")


def paused_error(pause: Pause) -> ServiceError:
    """The refusal every chat route gives while a person is paused, naming where to get help (S9; PROVISIONAL:
    clinician sign-off required before deploy); the client shows the pause from `paused_from` to `paused_until`, and
    leads with 911 when `paused_for` is overdose."""
    return ServiceError(
        f"chat for user {pause.user_id} is paused until {pause.ends_at.isoformat()}",
        ErrorCategory.CHAT_PAUSED,
        user_message=f"Your chat with Mani is paused for now. {crisis.IN_DANGER}",
        details={"paused_from": pause.started_at.isoformat(), "paused_until": pause.ends_at.isoformat(),
                 "paused_for": pause.paused_for},
    )
