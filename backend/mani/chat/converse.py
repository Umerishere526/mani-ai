# ABOUTME: Mani's turn whenever no framework, offer or check is open: the note sent with their message, and
# ABOUTME: what the reply decides about the heart of it and the check. Pure functions the orchestrator applies.

from __future__ import annotations

from mani.chat import context, understanding
from mani.db.threads import TurnContext
from mani.llm.schema import ConversationReply, UnderstandingUpdate

STYLE_NAMES = {"directive": "Directive", "supportive": "Supportive", "reflective": "Reflective"}
# The heart of it said back and not corrected. A check may only follow a reply that judged one of these, so the
# conflict is confirmed in its own exchange before Mani pulls the whole thing together.
NAMED = ("conflict_named", understanding.READY)


def check_allowed(ctx: TurnContext) -> bool:
    """Whether this reply may check Mani's understanding: the floor and cooldowns of context.may_check, and an
    earlier reply that said the heart of it back and was not corrected."""
    return context.may_check(ctx) and ctx.thread.understanding.get("heart") in NAMED


def note(
    style: str,
    *,
    allowed: bool,
    due: bool,
    wants_title: bool,
    understood: dict[str, str] | None = None,
    recent_crisis: bool = False,
) -> str:
    """What this reply needs to know that the conversation does not show. Sent after their message as a
    system message, never stored."""
    lines = [f"Their style: {STYLE_NAMES.get(style, style)}."]
    if recent_crisis:
        lines.append(
            "Another conversation of theirs was flagged recently. You know only that. Go gently, and never "
            "mention it unless they do."
        )
    if so_far := understanding.render(understood or {}):
        lines.append(f"What you understood before their message: {so_far}.")
    if allowed and due:
        lines.append(
            "Your last reply judged the heart of it ready. Unless their message changes it, this reply checks "
            "your understanding."
        )
    elif allowed:
        lines.append("You may check your understanding this turn, only if heart is ready after their message.")
    else:
        lines.append("Do not check your understanding this turn. Keep following their story.")
    if wants_title:
        lines.append("Give this conversation a title.")
    return "Note for this reply only. Never mention it.\n" + "\n".join(lines)


def _sentence(value: str | None) -> str:
    cleaned = " ".join((value or "").split())
    return cleaned if not cleaned or cleaned[-1] in ".!?" else cleaned + "."


def checked(reply: ConversationReply, *, allowed: bool) -> bool:
    """Whether this reply is Mani's check, stored so their next message answers it: allowed this turn,
    flagged by the reply, and saying the conflict, what they want and what is stopping them."""
    return allowed and bool(reply.checking) and all(
        (part or "").strip() for part in (reply.conflict, reply.want, reply.in_the_way)
    )


def case(reply: ConversationReply) -> str:
    """The check's understanding as the case a framework works on: conflict, want, what is in the way."""
    return " ".join(s for part in (reply.conflict, reply.want, reply.in_the_way) if (s := _sentence(part)))


def understood_after(stored: dict[str, str], reply: ConversationReply, *, check_written: bool) -> dict[str, str]:
    """The record after this turn: new feeling words added, where the reply judged the heart of it, and on a
    stored check its case. A check is always ready."""
    heart = understanding.READY if check_written else reply.heart
    merged = understanding.merge(stored, UnderstandingUpdate(feeling=reply.feelings), heart)
    return understanding.merge_check(merged, case(reply)) if check_written else merged
