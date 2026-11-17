# ABOUTME: Mani's turn whenever no framework, offer or check is open: the note sent with their message, and
# ABOUTME: what the reply decides about the heart of it and the check. Pure functions the orchestrator applies.

from __future__ import annotations

import re

from mani.chat import context, picture, understanding
from mani.db.threads import TurnContext
from mani.llm.schema import ConversationReply, ConversationUnderstanding

STYLE_NAMES = {"directive": "Directive", "supportive": "Supportive", "reflective": "Reflective"}
# The core said back and not corrected. A check may only follow a reply that judged one of these, so the core is
# offered in its own exchange before Mani checks it (muhammad, 2026-10-28: the check is about the core alone).
NAMED = (understanding.CORE_NAMED, understanding.READY)


# What the last reply asked itself first (muhammad, 2026-10-29: what do they need, does Mani need more, what insight is
# supported).
THINKING = "thinking"
# The insights Mani already gave, latest last, so it deepens or moves on instead of reaching the same one from
# another angle (the client's review, 2026-10-29).
INSIGHTS = context.INSIGHTS
# What the chat's note carries of the conversation's record besides the insights: what recent replies added, and
# connections Mani can infer and has not said. What is explored and what to explore next are left out (muhammad,
# 2026-11-16: in his local chat they named the same areas as explored and as worth exploring, beside a question the
# last reply had planned, and the reply asked on for twenty turns).
NOTED = ("recent_progress", "connections")

# Whatever the conversation, a risk to someone else comes first and is treated as something to act on.
RISK_FIRST = (
    "First name the risk to {who} plainly and take it seriously as something to act on, such as who should know, "
    "before anything else."
)
# They corrected what the offer said back about them (the client meeting, 2026-11-03). Kept on the understanding record
# until the next offer, or a new issue, clears it; while it is there the next offer may come sooner (context.may_check).
CORRECTED = understanding.CORRECTED
# Whether this reply can move to the set of questions, said as a fact. When it moves is the model's judgment, from
# "Moving to the framework" in conversation.md: code decides only that an offer names a reading an earlier reply said
# back (spec 0008, D2, muhammad 2026-11-16).
# Once the core was said back and stands, the reply moves, or names why it waits (muhammad's local chat, 2026-11-16:
# the move was allowed on eight replies in a row and never made, and he had to type "framework?"; the same happened on
# 2026-11-11, the father chat). Their message still gets its own answer first when the reply reports a reason to wait.
MOVE_NOW = (
    "Your reading was said back in an earlier reply and they have not corrected it: this reply moves to the set of "
    "questions (set checking, fill core, heading_toward and offer). It waits only when they are frustrated with you "
    "or asked what to do, or when their message corrects your reading, asks you something or brings out something "
    "new and painful: then name which in not_moving, and answer that."
)
# Something new and painful holds the move for one reply (the Supportive and Reflective baselines, 2026-11-16: it
# held it on two replies in a row in about a quarter of the turns that could move, so someone who brings something
# each time never reached the offer).
MOVE_NOW_AFTER_NEW = (
    "Your reading was said back and stands, and your last reply stayed with something new they brought: this reply "
    "moves to the set of questions (set checking, fill core, heading_toward and offer), and what they add now goes "
    "with it in a line. It waits only when they are frustrated with you or asked what to do, or when their message "
    "corrects your reading or asks you something: then name which in not_moving, and answer that."
)
# With what happened, what they tell themselves and what it does to them known, the next step is to say the core back
# (muhammad, 2026-11-16): the same chat had the belief by their third message and was still asking at their thirteenth.
KNOWN = context.KNOWN
ENOUGH = ("happened", "tells_themselves", "does_to_them")
NAME_NOW = (
    "You know what is happening, what they tell themselves about it and what it does to them. That is enough: ask "
    "nothing more about them. Say the core back to them in this "
    "reply, as your reading in everyday words, and let your question be whether it fits (heart is then core_named). "
    "Only when their message corrects you, is frustrated with you or asks you something does that come first."
)
MOVE_NOT_POSSIBLE = "This reply cannot move to the set of questions."
# A safety concern earlier in this conversation that has settled. The chat runs only while safety is clear, and Mani
# reads the whole conversation again every turn: with nothing saying it was settled it raised it again in its replies
# (muhammad's chats and the scenario runs, 2026-11-10). It still judges every message for safety.
SETTLED_LINE = context.SETTLED_LINE
AFTER_CORRECTION = (
    "When you offered the set of questions, they corrected what you understood. Your reading follows their "
    "correction now; once their message confirms it, move to the set again."
)
# Their answer to the question about a pause (muhammad, 2026-11-16): what the pause rested on is kept on the pause, so
# the reply knows what they faced in whichever conversation they come back.
RETURNED = "Before their chat with you was paused, the worry was this: {reason}. That was then. " + context.RETURN_ANSWER


def risk_first(picture_now: dict | None) -> str | None:
    """The line that puts a risk to someone else first, or None when there is none."""
    others = [r["risk"] for r in (picture_now or {}).get("risks") or [] if r.get("to") == "others"]
    return RISK_FIRST.format(who=others[-1]) if others else None


def move_held_by(ctx: TurnContext) -> str | None:
    """What keeps this reply from moving to the set of questions, for the turn's trace; None when it may move. In
    order: a set already open or a cooldown (context.may_check), no earlier reply that said the heart of it back
    uncorrected, and something being prepared."""
    if not context.may_check(ctx):
        return "a set already open, or a cooldown"
    if (heart := understanding.heart(ctx.thread.understanding)) not in NAMED:
        return f"the heart of it is not named yet ({heart or 'nothing stored'})"
    if ctx.thread.understanding.get(context.PREPARING):
        return "something is being prepared"
    return None


def check_allowed(ctx: TurnContext) -> bool:
    """Whether this reply may move to the set of questions."""
    return move_held_by(ctx) is None


def stayed_for_new(understood: dict | None) -> bool:
    """Whether the last reply could have moved to the set and waited for something new they brought."""
    return ((understood or {}).get(THINKING) or {}).get("waited") == "new"


def enough(understood: dict | None) -> bool:
    """Whether the replies so far reported all three things a set of questions works on."""
    known = (understood or {}).get(KNOWN) or {}
    return all(known.get(part) for part in ENOUGH)


def naming_due(ctx: TurnContext) -> bool:
    """Whether this reply is the one that says the core back: enough is known, no earlier reply said it, and a set of
    questions could still be offered in this conversation. Judged on what the replies reported, never on a count of
    messages or on the reading that lands after a reply."""
    understood = ctx.thread.understanding or {}
    return (
        enough(understood) and understanding.heart(understood) not in NAMED
        and context.may_check(ctx) and not understood.get(context.PREPARING)
    )


def note(
    style: str,
    *,
    allowed: bool,
    wants_title: bool,
    naming_due: bool = False,
    understood: dict[str, str] | None = None,
    recent_crisis: bool = False,
    returned_from: str | None = None,
    stepped_out_of: str | None = None,
    asked: list[str] | None = None,
    frameworks: str | None = None,
    finished: str | None = None,
    ended_on: str | None = None,
) -> str:
    """What this reply needs to know that the conversation does not show. Sent after their message as a
    system message, never stored. Once the conversation presses toward the framework, the line that says so."""
    lines = [f"Their style: {STYLE_NAMES.get(style, style)}."]
    if returned_from:
        lines.append(RETURNED.format(reason=context.disarm(returned_from)))
    elif recent_crisis:
        lines.append(
            "Another conversation of theirs was flagged recently. You know only that. Go gently, and never "
            "mention it unless they do."
        )
    if (understood or {}).get(context.SAFETY_SETTLED):
        lines.append(SETTLED_LINE)
    lines += [context.UNCLEAR_WORDS, context.DANGER_DIRECTION]
    if seen := picture.brief((understood or {}).get(picture.KEY)):
        lines.append(f"What you understood of them before their message: {context.disarm(seen)}.")
    if so_far := understanding.render(understood or {}):
        lines.append(f"What you understood before their message: {so_far}.")
    seen = (understood or {}).get(picture.KEY) or {}
    seen_known = (understood or {}).get(KNOWN) or {}
    naming = naming_due and not allowed and enough(understood)
    if asked:
        lines.append(f"Questions you already asked ({context.SAME_QUESTION}): " + " | ".join(asked))
    if given := (understood or {}).get(INSIGHTS):
        lines.append(
            "Insights you already gave: " + " | ".join(given) + ". Never give another on the same theme from a new "
            "angle: the next one adds something new, or deepen one with something new they said, or move forward."
        )
    for key, value in context.journey(understood):
        if key in NOTED:
            lines.append(f"{key.replace('_', ' ').capitalize()}: {value}. {context.meaning_of(key)}")
    if preparing := (understood or {}).get(context.PREPARING):
        # They chose Plan Next Step after the questions (muhammad, 2026-11-06): the chat helps them prepare it until
        # they have it, and nothing moves toward a set of questions meanwhile.
        lines.append(
            f"You are helping them prepare what they chose after the questions: {preparing.get('for') or 'their next step'}. "
            f"{context.follow_through_guide(preparing.get('kind', '')) or ''} Set prepared when they have what they "
            "need for it, or want to talk about something else."
        )
    if not seen.get("situations") and not seen_known.get("happened"):
        # Only the story is ever pointed at: a list of what is still unknown drove a question every turn
        # (2026-10-29), and what Mani can infer it never asks for.
        lines.append("What happened is not known yet: let them tell it.")
    if risk := risk_first(seen):
        lines.append(risk)
    if (understood or {}).get(CORRECTED):
        lines.append(AFTER_CORRECTION)
    if naming:
        lines.append(NAME_NOW)
    lines.append((MOVE_NOW_AFTER_NEW if stayed_for_new(understood) else MOVE_NOW) if allowed else MOVE_NOT_POSSIBLE)
    if allowed and frameworks:
        lines.append(frameworks)
    if finished:
        # A fact the chat was never shown (manasa's test, 2026-11-16: after ABCDE it went back over why she felt
        # that way and then offered ABCDE again). What to do with it is "After a set of questions" in conversation.md.
        where = f", where they ended on: {context.disarm(ended_on)}" if ended_on else ""
        lines.append(f"They finished {finished} earlier in this conversation{where}.")
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
    """Whether this reply moves to the set of questions: allowed this turn, flagged by the reply, and saying the core
    (muhammad, 2026-10-28: about the core alone). Since the client meeting (2026-11-03) it is no longer a check they
    answer: the offer goes with it."""
    return allowed and bool(reply.checking) and bool((reply.core or "").strip())


def case(reply: ConversationReply, picture_now: dict | None = None) -> str:
    """The check's understanding as the case a framework works on: the core, and the feeling underneath when the
    reply's words do not already say it, as Mani's reading, never as a fact about them (the review, 2026-11-03)."""
    said = _sentence(reply.core)
    feeling = picture.core(picture_now).get("feeling") or ""
    # Each feeling once: "inadequacy and discouragement" adds only the one the core does not already say (the career
    # chat, 2026-11-03: "...a painful sense of inadequacy. Underneath it you feel Inadequacy and discouragement.").
    parts = [p.strip() for p in re.split(r",|;|\band\b|/", feeling) if p.strip()]
    missing = [p for p in parts if p.lower() not in said.lower()]
    if said and missing and "underneath" not in said.lower():
        said += f" Underneath it, there may be {' and '.join(m[0].lower() + m[1:] for m in missing)}."
    return said


def replied(stored: dict, reply: ConversationReply, *, check_written: bool) -> dict:
    """The record once the reply is written, before Mani reads what their message adds (read, after the reply is
    sent): where the reply judged the heart of it, what its window landed on, on a move to the set its case, its plan
    and what it asked itself, and that asking for help presses toward the framework. A move to the set is always
    ready."""
    heart = understanding.READY if check_written else reply.heart
    if heart in NAMED and not (reply.core or "").strip():
        # Said back means its words went out: a reply that reports the core named without them has not said it, and an
        # offer after it would be the first time they heard it.
        heart = understanding.EXPLORING
    merged = understanding.merge(stored, None, heart)
    if check_written:
        merged = understanding.merge_check(merged, case(reply, merged.get(picture.KEY)))
    if reply.known is not None:
        # Kept once known: a later reply that leaves a part empty does not take it back.
        said = {part: " ".join(value.split()) for part, value in reply.known.model_dump().items() if value and value.strip()}
        if known := (merged.get(KNOWN) or {}) | said:
            merged[KNOWN] = known
    thinking = {
        key: value for key, value in (
            ("need", reply.need), ("needs_info", reply.needs_info), ("info", reply.info_needed),
            ("shape", reply.shape), ("window", reply.window.model_dump() if reply.window else None),
            ("insight", reply.insight), ("from", reply.insight_from), ("link", reply.link), ("move", reply.move),
            ("asked_for_help", reply.asked_for_help or None), ("heart", heart),
            ("waited", getattr(reply, "not_moving", None)),
        ) if value not in (None, "")
    }
    merged = context.with_insight(merged, reply.insight)
    if reply.progress is not None:
        merged = context.with_progress(merged, reply.progress.kinds, reply.progress.adds)
    if thinking:
        merged[THINKING] = thinking
    else:
        merged.pop(THINKING, None)
    # Records from before 2026-11-16 held that they had asked for help, as a state every later reply was told about.
    merged.pop("helping", None)
    merged.pop("toward_framework", None)
    return merged


def _explored_so_far(stored: dict, seen: ConversationUnderstanding) -> dict:
    """The reading's map, with the areas already explored kept: what is worth exploring next and what can be inferred
    are this reading's, but an area once explored stays explored, because the reading re-judges the whole list every
    turn and the move to a set of questions would be allowed one turn and held the next. A new issue starts the map
    again."""
    now = seen.exploration.model_dump()
    if ((seen.picture.shift if seen.picture else None) or "").strip().lower() == "new_issue":
        return now
    before = (stored.get(context.EXPLORATION) or {}).get("explored") or []
    now["explored"] = [*before, *(area for area in now["explored"] if area not in before)]
    return now


def read(
    stored: dict, seen: ConversationUnderstanding, *, with_picture: bool = True,
) -> dict:
    """The record with what Mani read after its reply: the picture with what their message adds or changes, the whole
    reading laid over it, and whether the conversation presses toward the framework. `stored` is the record as it is
    now, which may already be a turn further on. Another situation clears the heart of it, unless the reply judged it
    with their message in view."""
    if not with_picture:
        # Inside the questions the stage reply wrote the picture and the heart of it stays where the walk put it; the
        # reading after it brings only the map of what is explored, so it can never rewrite the core the questions
        # look at (the career chat, 2026-11-03).
        merged = understanding.merge(stored, None, None)
        if seen.exploration is not None:
            merged[context.EXPLORATION] = _explored_so_far(stored, seen)
        return merged
    merged = understanding.merge(stored, seen.picture, (stored.get(THINKING) or {}).get("heart"))
    # The reading is Mani's whole understanding, re-read every turn, laid over the facts the message added.
    if reading := picture.apply_reading(merged.get(picture.KEY), seen.reading):
        merged[picture.KEY] = reading
    if seen.exploration is not None:
        merged[context.EXPLORATION] = _explored_so_far(stored, seen)
    return merged


def read_note(style: str, understood: dict) -> str:
    """What the reading after a reply is told: the record as it was, and what to fill. Never stored."""
    lines = [f"Their style: {STYLE_NAMES.get(style, style)}."]
    if seen := understanding.picture_line(understood):
        lines.append(f"Your picture of them before their message: {seen}.")
    if so_far := understanding.render(understood):
        lines.append(f"What you understood before their message: {so_far}.")
    lines.append(
        "Your reply has gone to them. Write nothing to them now: fill reading and picture from the whole conversation, "
        "their last message read against what you already understood, as Maintain the working picture says."
    )
    return "Note for this reading only. Never mention it.\n" + "\n".join(lines)
