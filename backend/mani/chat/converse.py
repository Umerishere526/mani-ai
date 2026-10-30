# ABOUTME: Mani's turn whenever no framework, offer or check is open: the note sent with their message, and
# ABOUTME: what the reply decides about the heart of it and the check. Pure functions the orchestrator applies.

from __future__ import annotations

import re

from mani.chat import context, picture, understanding
from mani.db.threads import TurnContext
from mani.llm.schema import ConversationReply
from mani.models.rows import Message, MessageRole

STYLE_NAMES = {"directive": "Directive", "supportive": "Supportive", "reflective": "Reflective"}
# The core said back and not corrected. A check may only follow a reply that judged one of these, so the core is
# offered in its own exchange before Mani checks it (muhammad, 2026-10-28: the check is about the core alone).
NAMED = (understanding.CORE_NAMED, understanding.READY)


# Where the conversation presses toward the framework: they asked what to do, are frustrated, or have stopped adding.
# Kept on the thread's understanding record until a new issue or a finished framework clears it. It replaced helping
# in the chat (the client's test, 2026-10-29): the framework is the solution, and the chat listens; before it Mani
# offers at most one small idea, never a fix.
TOWARD = "toward_framework"
# Messages this short, SHORT_IN_A_ROW of them, are someone disengaging, whatever the model judged. Two were too
# few: "yes" then "I don't know" are often plain answers to Mani's questions.
SHORT_WORDS = 3
SHORT_IN_A_ROW = 3
# Messages in a row that added nothing and answered nothing before Mani presses toward the framework. One was too few: "both",
# a plain answer to Mani's either-or question, turned a chat to job-hunting before the core was named (muhammad,
# 2026-10-29). A short answer to Mani's question is now `answered`, which never counts.
QUIET_TO_HELP = 2
# Where the conversation is heading, as the last reply put it, and what that reply asked itself first (muhammad,
# 2026-10-29: what do they need, does Mani need more, what insight is supported).
PLAN = "plan"
THINKING = "thinking"
# The insights Mani already gave, latest last, so it deepens or moves on instead of reaching the same one from
# another angle (the client's review, 2026-10-29).
INSIGHTS = "insights"
INSIGHTS_KEPT = 4
# How many of Mani's own questions the note lists, so none is asked again.
ASKED_LIMIT = 6
_QUESTION = re.compile(r"[^.!?\n]*\?")

# Whatever the conversation, a risk to someone else comes first and is treated as something to act on.
RISK_FIRST = (
    "First name the risk to {who} plainly and take it seriously as something to act on, such as who should know, "
    "before anything else."
)
# What the note says once the conversation presses toward the framework.
TOWARD_LINE = (
    "They want to move: they asked what to do, are frustrated, or have stopped adding. Do not solve it in the chat. "
    "If they asked what to do, give at most one small idea (move small_idea), then say that working it through "
    "together would help. Move toward the framework: if you have not named the core as your reading, do it in this "
    "reply."
)


# What the note points out the reading still lacks, from their GAPS_FROM-th message: by then their first messages
# have usually said it (approach C, muhammad 2026-10-29: the partner chat's picture held no want, need, desire or core
# after five messages that said all four).
GAPS_FROM = 2
# A reply this short that only repeats what the picture already holds answered a question Mani should not have asked
# ("work", 2026-10-29, asked "what got in the way?" twice after they had said work).
REPEAT_WORDS = 4
_READINGS = (("wants", "what they want"), ("needs", "the need underneath"), ("desire", "what they long for"))
# A short yes to an insight: understood, so the next reply moves on instead of explaining it again (the client's
# review, 2026-10-29: "That fear makes sense..." restated the fear the person had just agreed to).
AGREED = re.compile(
    r"^\s*(?:yes|yeah|yep|yup|exactly|right|true|definitely|i think so|that's it|that's right|pretty much|kind of|"
    r"sort of|maybe|mostly)\b[\s.!,]*(?:\w+[\s.!,]*){0,3}$",
    re.IGNORECASE,
)


def gaps(
    seen: dict, *, heart: str | None, their_count: int, latest: str | None, last_shape: str | None = None,
) -> list[str]:
    """Lines for the note about what Mani's picture lacks or already holds, so the reply fills the one and never asks
    for the other, and, when they just agreed with an insight, that it is understood."""
    lines: list[str] = []
    if last_shape == "insight" and latest and AGREED.match(latest):
        lines.append(
            "They agreed with your insight: it is understood. Do not explain or restate it. Move forward: ask what it "
            "means to them or what it stands for (what they fear losing, what it would cost them), or, when the note "
            "allows, check the core."
        )
    thoughts = [b["belief"] for b in seen.get("beliefs") or [] if b.get("kind") == "thought"]
    core_now = picture.core(seen).get("belief")
    if their_count >= GAPS_FROM and thoughts and not core_now:
        lines.append(
            "Your picture holds what they tell themselves (" + " | ".join(thoughts) + ") but no core. Their words "
            "point to one: give it in your reading, and say it to them in this reply as your reading, with the "
            "feeling underneath, then set heart to core_named."
        )
    elif core_now and heart in (None, "exploring") and their_count >= GAPS_FROM + 1:
        lines.append(
            f"Your reading has a core you have not said to them yet: {core_now}. Say it in this reply as your "
            "reading, in everyday words, and let them correct it."
        )
    if their_count >= GAPS_FROM and (empty := [name for key, name in _READINGS if not seen.get(key)]):
        lines.append(
            "Still empty in your reading: " + ", ".join(empty) + ". Fill them from what they have already said; ask "
            "only if nothing they said points to them."
        )
    known = [seen.get("in_the_way"), *(d["what"] for d in seen.get("dependencies") or [] if d.get("kind") == "external")]
    if known := [k for k in known if k]:
        lines.append("Already known, never ask for it again: what is in the way: " + " | ".join(known) + ".")
    words = [w for w in re.findall(r"[a-z']+", (latest or "").lower()) if len(w) > 2]
    held = " ".join([*(seen.get("situations") or []), seen.get("in_the_way") or "",
                     *(d["what"] for d in seen.get("dependencies") or [])]).lower()
    if words and len(words) <= REPEAT_WORDS and all(w in held for w in words):
        lines.append(
            "Their answer only repeats what they already told you, so your last question asked for something you "
            "knew. Do not ask about it again. Move to what they want, or to the core."
        )
    return lines


def risk_first(picture_now: dict | None) -> str | None:
    """The line that puts a risk to someone else first, or None when there is none."""
    others = [r["risk"] for r in (picture_now or {}).get("risks") or [] if r.get("to") == "others"]
    return RISK_FIRST.format(who=others[-1]) if others else None


def toward(
    stored: dict, reply: ConversationReply, after: dict, their_messages: list[str],
) -> bool:
    """Whether the conversation presses toward the framework after this turn: it already did, or they
    asked for help, are frustrated with the conversation, or QUIET_TO_HELP messages in a row added nothing new and
    answered nothing Mani asked, or their last
    SHORT_IN_A_ROW messages were a few words each. A new issue starts understanding again."""
    seen = after.get(picture.KEY) or {}
    if seen.get("shift") == "new_issue":
        return False
    if stored.get(TOWARD) or reply.asked_for_help or reply.frustrated:
        return True
    if seen.get("quiet", 0) >= QUIET_TO_HELP:
        return True
    latest = their_messages[-SHORT_IN_A_ROW:]
    return len(latest) == SHORT_IN_A_ROW and all(len(m.split()) <= SHORT_WORDS for m in latest)


def asked_before(history: list[Message]) -> list[str]:
    """The questions Mani asked in this conversation, latest last, so the note can list them."""
    asked = [
        " ".join(q.split()) for m in history if m.role is MessageRole.MANI for q in _QUESTION.findall(m.content)
    ]
    return [q for q in asked if q][-ASKED_LIMIT:]


def check_allowed(ctx: TurnContext) -> bool:
    """Whether this reply may check Mani's understanding: the floor and cooldowns of context.may_check, and an
    earlier reply that said the heart of it back and was not corrected."""
    return context.may_check(ctx) and understanding.heart(ctx.thread.understanding) in NAMED


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
    their_count: int = 0,
    latest: str | None = None,
) -> str:
    """What this reply needs to know that the conversation does not show. Sent after their message as a
    system message, never stored. Once the conversation presses toward the framework, the line that says so."""
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
    pressing = bool((understood or {}).get(TOWARD))
    if asked:
        lines.append("Questions you already asked, never to ask again in any words: " + " | ".join(asked))
    last_shape = ((understood or {}).get(THINKING) or {}).get("shape")
    lines += gaps(seen, heart=understanding.heart(understood or {}), their_count=their_count, latest=latest,
                  last_shape=last_shape)
    if given := (understood or {}).get(INSIGHTS):
        lines.append(
            "Insights you already gave: " + " | ".join(given) + ". Never give another on the same theme from a new "
            "angle: deepen one with something new they said, ask about what they do, or move forward."
        )
    if last_shape == "reflect":
        lines.append("Your last reply asked nothing: this one asks.")
    if plan := (understood or {}).get(PLAN):
        lines.append(f"Your plan from your last reply: {plan}. Keep it, or change it if their message does.")
    if not pressing and not seen.get("situations"):
        # Only the story is ever pointed at: a list of what is still unknown drove a question every turn
        # (2026-10-29), and what Mani can infer it never asks for.
        lines.append("What happened is not known yet: let them tell it.")
    if risk := risk_first(seen):
        lines.append(risk)
    if pressing:
        lines.append(TOWARD_LINE)
    if allowed and (due or pressing):
        lines.append(
            "Unless their message changes your reading, this reply checks your understanding: it is the way to the "
            "set of questions."
        )
    elif allowed:
        lines.append("You may check your understanding this turn, only if heart is ready after their message.")
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
    """Whether this reply is Mani's check, stored so their next message answers it: allowed this turn, flagged by
    the reply, and saying the core (muhammad, 2026-10-28: the check is about the core alone)."""
    return allowed and bool(reply.checking) and bool((reply.core or "").strip())


def case(reply: ConversationReply, picture_now: dict | None = None) -> str:
    """The check's understanding as the case a framework works on: the core, and the feeling underneath when the
    reply's words do not already say it."""
    said = _sentence(reply.core)
    feeling = picture.core(picture_now).get("feeling")
    if said and feeling and feeling.lower() not in said.lower():
        said += f" Underneath it you feel {feeling}."
    return said


def understood_after(
    stored: dict, reply: ConversationReply, *, check_written: bool, their_messages: list[str] | None = None,
) -> dict:
    """The record after this turn: the picture with what their message adds or changes, where the reply judged
    the heart of it, on a stored check its case, and whether the conversation presses toward the framework. A check is
    always ready."""
    heart = understanding.READY if check_written else reply.heart
    merged = understanding.merge(stored, reply.picture, heart)
    # The reading is Mani's whole understanding, re-read every turn, laid over the facts the message added.
    if read := picture.apply_reading(merged.get(picture.KEY), reply.reading):
        merged[picture.KEY] = read
    if check_written:
        merged = understanding.merge_check(merged, case(reply, merged.get(picture.KEY)))
    if plan := " ".join((reply.plan or "").split()):
        merged[PLAN] = plan
    thinking = {
        key: value for key, value in (
            ("need", reply.need), ("needs_info", reply.needs_info), ("info", reply.info_needed),
            ("shape", reply.shape), ("window", reply.window.model_dump() if reply.window else None),
            ("insight", reply.insight), ("from", reply.insight_from), ("link", reply.link), ("move", reply.move),
        ) if value not in (None, "")
    }
    if insight := " ".join((reply.insight or "").split()):
        merged[INSIGHTS] = [*(stored.get(INSIGHTS) or []), insight][-INSIGHTS_KEPT:]
    if thinking:
        merged[THINKING] = thinking
    else:
        merged.pop(THINKING, None)
    if toward(stored, reply, merged, their_messages or []):
        merged[TOWARD] = True
    else:
        merged.pop(TOWARD, None)
    # A record from before 2026-10-29 said helping; the chat no longer helps, it presses toward the framework.
    merged.pop("helping", None)
    return merged
