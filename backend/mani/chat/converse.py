# ABOUTME: Mani's turn whenever no framework, offer or check is open: the note sent with their message, and
# ABOUTME: what the reply decides about the heart of it and the check. Pure functions the orchestrator applies.

from __future__ import annotations

import re

from mani.chat import context, picture, understanding
from mani.db.threads import TurnContext
from mani.llm.schema import ConversationReply
from mani.models.rows import Message, MessageRole

STYLE_NAMES = {"directive": "Directive", "supportive": "Supportive", "reflective": "Reflective"}
# The heart of it said back and not corrected. A check may only follow a reply that judged one of these, so the
# conflict is confirmed in its own exchange before Mani pulls the whole thing together.
NAMED = ("conflict_named", understanding.READY)


# Where understanding turns into helping, kept on the thread's understanding record until a new issue or a
# finished framework clears it (muhammad, 2026-10-27).
HELPING = "helping"
# Messages this short, SHORT_IN_A_ROW of them, are someone disengaging, whatever the model judged. Two were too
# few: "yes" then "I don't know" are often plain answers to Mani's questions.
SHORT_WORDS = 3
SHORT_IN_A_ROW = 3
# How many of Mani's own questions the note lists, so none is asked again.
ASKED_LIMIT = 6
_QUESTION = re.compile(r"[^.!?\n]*\?")

# What helping looks like, by the kind of problem and the style they chose (muhammad, 2026-10-27). Code picks the
# move and the model writes it. Only ABCDE and Thought Reframe are offered, and only for what they tell themselves;
# a real situation is helped in the conversation itself.
HELP_MOVES: dict[str, dict[str, str]] = {
    "belief": {
        "directive": (
            "What hurts is what they tell themselves. Say plainly what you see in that thought, then offer to look at "
            "it together through a short set of questions, and let them choose."
        ),
        "supportive": (
            "What hurts is what they tell themselves. Acknowledge how heavy that thought is, then ask gently whether "
            "they would like to look at it together."
        ),
        "reflective": (
            "What hurts is what they tell themselves. Name the pattern you notice in that thought, in their words, as "
            "an invitation, then ask whether they would like to look at it more closely together."
        ),
    },
    "situation": {
        "directive": (
            "This is something really happening that needs dealing with. Offer two or three concrete, sensible next "
            "steps that fit what they told you, as ideas they choose from, and ask which fits them."
        ),
        "supportive": (
            "This is something really happening that needs dealing with. Acknowledge how hard it is and what they "
            "are already carrying, then ask whether they would like to keep talking it through or look at what "
            "might help; ideas come gently, as theirs to take or leave."
        ),
        "reflective": (
            "This is something really happening that needs dealing with. Name one thing that stands out to you, a "
            "pattern or a connection in what they said, as an insight they can check, then ask what they want to do "
            "with it."
        ),
    },
    "both": {
        "directive": (
            "There is something really happening and something they tell themselves about it. Say so plainly and ask "
            "which they want to start with: what to do about the situation, or the thought."
        ),
        "supportive": (
            "There is something really happening and something they tell themselves about it. Acknowledge both, "
            "then ask gently which they would like to start with."
        ),
        "reflective": (
            "There is something really happening and something they tell themselves about it. Name the link "
            "between the two, then ask which they would like to look at first."
        ),
    },
}
# Before the kind of problem is clear: ask what would help, in the style.
UNSURE_MOVE = "You do not know yet what kind of help fits. Ask them, in a sentence, what would help most right now."
# Whatever the style or the kind of problem, a risk to someone else comes first and is treated as practical.
RISK_FIRST = (
    "First name the risk to {who} plainly and take it seriously as something to act on, such as who should know, "
    "before anything else."
)


def help_move(style: str, picture_now: dict | None) -> str:
    """The move this reply makes once Mani is helping, from the kind of problem and the style they chose."""
    seen = picture_now or {}
    move = HELP_MOVES.get(seen.get("problem_type") or "", {}).get(style, UNSURE_MOVE)
    others = [r["risk"] for r in seen.get("risks") or [] if r.get("to") == "others"]
    return f"{RISK_FIRST.format(who=others[-1])} {move}" if others else move


def turned(
    stored: dict, reply: ConversationReply, after: dict, their_messages: list[str],
) -> bool:
    """Whether the conversation has turned from understanding to helping after this turn: it already had, or they
    asked for help, are frustrated with the conversation, or their message added nothing new, or their last
    SHORT_IN_A_ROW messages were a few words each. A new issue starts understanding again."""
    seen = after.get(picture.KEY) or {}
    if seen.get("shift") == "new_issue":
        return False
    if stored.get(HELPING) or reply.asked_for_help or reply.frustrated:
        return True
    if seen.get("quiet", 0) >= 1:
        return True
    latest = their_messages[-SHORT_IN_A_ROW:]
    return len(latest) == SHORT_IN_A_ROW and all(len(m.split()) <= SHORT_WORDS for m in latest)


def asked_before(history: list[Message]) -> list[str]:
    """The questions Mani asked in this conversation, latest last, so the note can list them."""
    asked = [
        " ".join(q.split()) for m in history if m.role is MessageRole.MANI for q in _QUESTION.findall(m.content)
    ]
    return [q for q in asked if q][-ASKED_LIMIT:]


def still_unknown(picture_now: dict | None) -> list[str]:
    """What the picture does not hold yet, in the order the conversation looks for it."""
    seen = picture_now or {}
    gaps = [
        ("what happened", seen.get("situations")),
        ("how it is for them", seen.get("feelings")),
        ("what they want", seen.get("wants")),
        ("what is stopping them", seen.get("in_the_way")),
    ]
    return [name for name, value in gaps if not value]


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
    stepped_out_of: str | None = None,
    asked: list[str] | None = None,
) -> str:
    """What this reply needs to know that the conversation does not show. Sent after their message as a
    system message, never stored. Once the conversation has turned to helping, the help move this reply makes."""
    lines = [f"Their style: {STYLE_NAMES.get(style, style)}."]
    if recent_crisis:
        lines.append(
            "Another conversation of theirs was flagged recently. You know only that. Go gently, and never "
            "mention it unless they do."
        )
    if seen := understanding.picture_line(understood or {}):
        lines.append(f"Your picture of them before their message: {seen}.")
    if so_far := understanding.render(understood or {}):
        lines.append(f"What you understood before their message: {so_far}.")
    seen = (understood or {}).get(picture.KEY) or {}
    helping = bool((understood or {}).get(HELPING))
    if asked:
        lines.append("Questions you already asked, never to ask again in any words: " + " | ".join(asked))
    if not helping and (gaps := still_unknown(seen)):
        lines.append("Still unknown: " + ", ".join(gaps) + ". Your question goes to the first of these that fits.")
    if helping:
        lines.append(
            "You are helping now: you understand enough. Each reply moves the help forward and gives them something, "
            "never only another question about what they already told you. Help move: " + help_move(style, seen)
        )
    if allowed and (due or (helping and seen.get("problem_type") in ("belief", "both"))):
        lines.append(
            "Unless their message changes your reading, this reply checks your understanding: it is the way to the "
            "set of questions."
        )
    elif allowed:
        lines.append("You may check your understanding this turn, only if heart is ready after their message.")
    elif helping:
        lines.append("Do not check your understanding this turn.")
    else:
        lines.append("Do not check your understanding this turn. Keep following their story.")
    if stepped_out_of:
        lines.append(
            f"They stepped out of {stepped_out_of} earlier. If they ask to go back to it, set back_to_framework and say "
            "warmly that you can pick it up again; code shows them the button to start it."
        )
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


def understood_after(
    stored: dict, reply: ConversationReply, *, check_written: bool, their_messages: list[str] | None = None,
) -> dict:
    """The record after this turn: the picture with what their message adds or changes, where the reply judged
    the heart of it, on a stored check its case, and whether the conversation has turned to helping. A check is
    always ready."""
    heart = understanding.READY if check_written else reply.heart
    merged = understanding.merge(stored, reply.picture, heart)
    if check_written:
        merged = understanding.merge_check(merged, case(reply))
    if turned(stored, reply, merged, their_messages or []):
        merged[HELPING] = True
    else:
        merged.pop(HELPING, None)
    return merged
