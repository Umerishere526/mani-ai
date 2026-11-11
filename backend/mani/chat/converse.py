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


# Where the conversation presses toward the framework: they asked what to do, or have stopped adding. Frustration with
# Mani is not a reason: it calls for a repair and no offer (R27, R28; Lolly's chat of 2026-11-03, where it brought the
# framework up at her fourth message). Kept on the thread's understanding record until a new issue or a finished framework clears it. It replaced helping
# in the chat (the client's test, 2026-10-29): the framework is the solution, and the chat listens; before it Mani
# offers at most one small idea, never a fix.
TOWARD = "toward_framework"
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
INSIGHTS = context.INSIGHTS

# Whatever the conversation, a risk to someone else comes first and is treated as something to act on.
RISK_FIRST = (
    "First name the risk to {who} plainly and take it seriously as something to act on, such as who should know, "
    "before anything else."
)
# They corrected what the offer said back about them (the client meeting, 2026-11-03). Kept on the understanding record
# until the next offer, or a new issue, clears it; while it is there the next offer may come sooner (context.may_check).
CORRECTED = understanding.CORRECTED
# The move to the set of questions, which replaced the check of the summary (the client meeting, 2026-11-03).
MOVE_NOW = (
    "Unless their message changes your reading or brings out something new and painful, which gets this reply of its "
    "own (heart is then core_named, not ready), this reply moves to the set of questions: set checking, fill core, "
    "heading_toward and offer. No summary before it and no \"does that capture it\": the offer says the core back, "
    "and they can correct it there."
)
# At core_named, not only ready: waiting for a confirmation no reply asked for kept the father chat from an offer with
# the move allowed (muhammad, 2026-11-11). The offer says the core back, and they can correct it there.
MOVE_MAY = (
    "You may move to the set of questions this turn once heart is core_named or ready after their message, unless "
    "their message brings out something new and painful, which gets this reply of its own: then set checking, fill "
    "core, heading_toward and offer."
)
MOVE_NOT = "Do not move to the set of questions this turn. Keep following their story."
# Everything is explored and the heart of it is still not said back (muhammad's chest chats, 2026-11-11: twelve chat
# turns held on it). Saying it is this reply's step; the move to the set of questions follows on the next.
NAME_NOW = (
    "They have told you enough: how they feel, what they tell themselves, what it does to them or what they need, and "
    "what they have tried. Say the core back to them now{core}, as your reading in everyday words, and let them "
    "correct it (heart is then core_named), unless their message brings out something new and painful, which gets "
    "this reply of its own first."
)
MOVE_NOT_YET = "Do not move to the set of questions this turn: saying the core back is this reply's step."
# A safety concern earlier in this conversation that has settled. The chat runs only while safety is clear, and Mani
# reads the whole conversation again every turn: with nothing saying it was settled it raised it again in its replies
# (muhammad's chats and the scenario runs, 2026-11-10). It still judges every message for safety.
SETTLED_LINE = context.SETTLED_LINE
AFTER_CORRECTION = (
    "When you offered the set of questions, they corrected what you understood. Your reading follows their "
    "correction now; once their message confirms it, move to the set again."
)
# What the note says once the conversation presses toward the framework.
TOWARD_LINE = (
    "They want to move: they asked what to do, or have stopped adding. Do not solve it in the chat. "
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
# A short yes to an insight: understood, so the next reply moves on instead of explaining it again (the client's
# review, 2026-10-29: "That fear makes sense..." restated the fear the person had just agreed to).
AGREED = re.compile(
    r"^\s*(?:yes|yeah|yep|yup|exactly|right|true|definitely|i think so|that's it|that's right|pretty much|kind of|"
    r"sort of|maybe|mostly)\b[\s.!,]*(?:\w+[\s.!,]*){0,3}$",
    re.IGNORECASE,
)
# A yes that opens a longer answer to a reading Mani put as a yes/no question ("Is that part of what makes it so hard
# to go?" answered "Yes, definitely. I think I've always been..."): the reply after it said the reading back at length
# (the daughter chat, 2026-11-03). "Yes, but" is a correction, never agreement.
SAID_YES = re.compile(
    r"^\s*(?:yes|yeah|yep|yup|exactly|definitely|absolutely|that's it|that's right)\b(?![\s,.!-]*but\b)", re.IGNORECASE,
)
_YES_NO = re.compile(r"^\s*(?:is|are|was|were|do|does|did|could|would|can|has|have|will)\b", re.IGNORECASE)


def agreed(latest: str | None, *, last_shape: str | None, last_question: str | None) -> bool:
    """Whether their message agrees with the reading Mani's last reply gave: a short yes to an insight, or a yes that
    opens their answer to a reading put as a yes/no question."""
    if not latest:
        return False
    if last_shape == "insight" and AGREED.match(latest):
        return True
    asked_yes_no = bool(last_question) and bool(_YES_NO.match(last_question)) and " or " not in last_question.lower()
    return asked_yes_no and bool(SAID_YES.match(latest))


def gaps(
    seen: dict, *, heart: str | None, their_count: int, latest: str | None, last_shape: str | None = None,
    last_question: str | None = None, naming_due: bool = False,
) -> list[str]:
    """Lines for the note about what Mani's picture lacks or already holds, so the reply fills the one and never asks
    for the other, and, when they just agreed with its reading, that it is understood."""
    lines: list[str] = []
    if agreed(latest, last_shape=last_shape, last_question=last_question):
        lines.append(
            "They agreed with your reading: it is understood. Do not explain or restate it: build on what they added, "
            "or move forward. Ask what it "
            "means to them or what it stands for (what they fear losing, what it would cost them), or, when the note "
            "allows, check the core."
        )
    thoughts = [b["belief"] for b in seen.get("beliefs") or [] if b.get("kind") == "thought"]
    core_now = picture.core(seen).get("belief")
    if naming_due:
        pass  # the note says the core now; holding it would contradict that
    elif their_count >= GAPS_FROM and thoughts and not core_now:
        lines.append(
            "Your picture holds what they tell themselves (" + " | ".join(thoughts) + ") but no core yet. Never give one "
            "while they are still telling it: a long message is the first layer. Stay with them and give room (\"Is "
            "there more?\") until they have said what they came to say (the client meeting, 2026-11-05)."
        )
    elif core_now and heart in (None, "exploring") and their_count >= GAPS_FROM + 1:
        lines.append(
            f"Your reading has a core you have not said to them yet: {core_now}. Hold it until they have said what "
            "they came to say; then say it as your reading, in everyday words, and let them correct it."
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


# The funnel (the client meeting, 2026-11-03: muhammad's way of narrowing down what a feeling depends on, most relevant
# first, instead of asking around it). From their FUNNEL_FROM-th message, once the first replies have let them feel
# heard; never for a feeling with no clear cause, which leaves the ranking empty.
FUNNEL_FROM = 3


def funnel_line(seen: dict, *, their_count: int) -> str | None:
    """The note's line on what to explore next, what was explored and what was ruled out, or None."""
    if their_count < FUNNEL_FROM:
        return None
    following, done, out = picture.funnel(seen)
    if following is None and not done:
        return None
    parts = ["What their feeling may depend on, narrowed down most relevant first."]
    if following is not None:
        parts.append(f"Explore next: {following['what']} ({following['side']} them).")
    else:
        parts.append("Everything you saw it depending on has been explored: stay with what they say, or go toward the core.")
    if done:
        parts.append("Already explored: " + " | ".join(done) + ".")
    if out:
        parts.append("Ruled out, never ask about it again: " + " | ".join(out) + ".")
    if following is not None:
        parts.append(
            "When you open the window, land on what to explore next unless their message points elsewhere. When they "
            "say it is not that, put it in ruled_out."
        )
    return " ".join(parts)


def risk_first(picture_now: dict | None) -> str | None:
    """The line that puts a risk to someone else first, or None when there is none."""
    others = [r["risk"] for r in (picture_now or {}).get("risks") or [] if r.get("to") == "others"]
    return RISK_FIRST.format(who=others[-1]) if others else None


def toward(stored: dict, asked_for_help: bool, after: dict) -> bool:
    """Whether the conversation presses toward the framework after this turn: it already did, or they asked for
    help, or QUIET_TO_HELP messages in a row added nothing new and answered nothing Mani asked while something that
    happened is already known. What a message means decides, never how long it is: "he lied" adds a great deal, and
    with nothing specific known yet someone who says little is offered possibilities, not pressed toward a core
    (muhammad, 2026-11-10). Frustration with Mani never does. A new issue starts understanding again."""
    seen = after.get(picture.KEY) or {}
    if seen.get("shift") == "new_issue":
        return False
    if stored.get(TOWARD) or asked_for_help:
        return True
    return seen.get("quiet", 0) >= QUIET_TO_HELP and bool(seen.get("situations"))


# What the conversation has explored before it moves to a set of questions (muhammad, 2026-11-06: the cadence moves on
# understanding, not counts): how they feel, what they tell themselves or what it means to them, what it does to them,
# what they need or what they want to happen (the father chat, 2026-11-11), and what they have tried or whether it has
# happened before (Lolly's steps 4 and 5, folded in from conversation.md). Each group needs one area from the
# after-reply reading's map.
EXPLORED_BEFORE_MOVING = (
    frozenset({"emotion"}), frozenset({"belief", "meaning"}), frozenset({"behaviour", "need", "outcome"}),
    frozenset({"attempts", "pattern"}),
)


def still_to_explore(understood: dict | None) -> list[str]:
    """What the conversation has yet to explore before it moves to a set of questions, from the reading's map. Nothing
    when there is no map yet (no reading has landed): then the heart of it decides alone, as before."""
    seen = (understood or {}).get(context.EXPLORATION)
    if not seen:
        return []
    areas = set(seen.get("explored") or [])
    return [_either(sorted(group)) for group in EXPLORED_BEFORE_MOVING if not areas & group]


def _either(areas: list[str]) -> str:
    """"belief or meaning", "behaviour, need or outcome"."""
    return f"{', '.join(areas[:-1])} or {areas[-1]}" if len(areas) > 1 else areas[0]


def move_held_by(ctx: TurnContext) -> str | None:
    """What keeps this reply from moving to the set of questions, for the turn's trace; None when it may move. In
    order: the floor and cooldowns of context.may_check, an earlier reply that said the heart of it back and was not
    corrected, something being prepared, and enough of their experience explored."""
    if not context.may_check(ctx):
        return "too early, a set already open, or a cooldown"
    if (heart := understanding.heart(ctx.thread.understanding)) not in NAMED:
        return f"the heart of it is not named yet ({heart or 'nothing stored'})"
    if ctx.thread.understanding.get(context.PREPARING):
        return "something is being prepared"
    if left := still_to_explore(ctx.thread.understanding):
        return "still to explore: " + "; ".join(left)
    return None


def naming_due(ctx: TurnContext) -> bool:
    """Whether this reply is the one that says the core back: everything the cadence waits on is explored and nothing
    else holds the move, yet the heart of it was never said back. Judged on what is understood, not on a count."""
    understood = ctx.thread.understanding or {}
    return (
        context.may_check(ctx) and understanding.heart(understood) not in NAMED
        and not understood.get(context.PREPARING) and bool(understood.get(context.EXPLORATION))
        and not still_to_explore(understood)
    )


def check_allowed(ctx: TurnContext) -> bool:
    """Whether this reply may move to the set of questions."""
    return move_held_by(ctx) is None


def note(
    style: str,
    *,
    allowed: bool,
    due: bool,
    wants_title: bool,
    naming_due: bool = False,
    understood: dict[str, str] | None = None,
    recent_crisis: bool = False,
    stepped_out_of: str | None = None,
    asked: list[str] | None = None,
    last_question: str | None = None,
    their_count: int = 0,
    latest: str | None = None,
    frameworks: str | None = None,
) -> str:
    """What this reply needs to know that the conversation does not show. Sent after their message as a
    system message, never stored. Once the conversation presses toward the framework, the line that says so."""
    lines = [f"Their style: {STYLE_NAMES.get(style, style)}."]
    if recent_crisis:
        lines.append(
            "Another conversation of theirs was flagged recently. You know only that. Go gently, and never "
            "mention it unless they do."
        )
    if (understood or {}).get(context.SAFETY_SETTLED):
        lines.append(SETTLED_LINE)
    if seen := understanding.picture_line(understood or {}):
        lines.append(f"Your picture of them before their message: {seen}.")
    if so_far := understanding.render(understood or {}):
        lines.append(f"What you understood before their message: {so_far}.")
    seen = (understood or {}).get(picture.KEY) or {}
    pressing = bool((understood or {}).get(TOWARD))
    if asked:
        lines.append(f"Questions you already asked ({context.SAME_QUESTION}): " + " | ".join(asked))
    last_shape = ((understood or {}).get(THINKING) or {}).get("shape")
    lines += gaps(seen, heart=understanding.heart(understood or {}), their_count=their_count, latest=latest,
                  last_shape=last_shape, last_question=last_question, naming_due=naming_due)
    if given := (understood or {}).get(INSIGHTS):
        lines.append(
            "Insights you already gave: " + " | ".join(given) + ". Never give another on the same theme from a new "
            "angle: the next one adds something new, or deepen one with something new they said, or move forward."
        )
    for key, value in context.journey(understood):
        if key != "insights_given":
            lines.append(f"{key.replace('_', ' ').capitalize()}: {value}. {context.meaning_of(key)}")
    if preparing := (understood or {}).get(context.PREPARING):
        # They chose Plan Next Step after the questions (muhammad, 2026-11-06): the chat helps them prepare it until
        # they have it, and nothing moves toward a set of questions meanwhile.
        lines.append(
            f"You are helping them prepare what they chose after the questions: {preparing.get('for') or 'their next step'}. "
            f"{context.follow_through_guide(preparing.get('kind', '')) or ''} Set prepared when they have what they "
            "need for it, or want to talk about something else."
        )
    if plan := (understood or {}).get(PLAN):
        lines.append(f"Your plan from your last reply: {plan}. Keep it, or change it if their message does.")
    if not pressing and not seen.get("situations"):
        # Only the story is ever pointed at: a list of what is still unknown drove a question every turn
        # (2026-10-29), and what Mani can infer it never asks for.
        lines.append("What happened is not known yet: let them tell it.")
    if risk := risk_first(seen):
        lines.append(risk)
    if not pressing and (narrowing := funnel_line(seen, their_count=their_count)):
        lines.append(context.disarm(narrowing))
    if pressing:
        lines.append(TOWARD_LINE)
    if (understood or {}).get(CORRECTED):
        lines.append(AFTER_CORRECTION)
    if not allowed and (left := still_to_explore(understood)):
        lines.append(
            "Before any set of questions, the question after your text opens what is still unexplored: "
            + "; ".join(left) + ", in a way that follows from what they just said, never asking for what they have told you."
        )
    if naming_due and not allowed:
        said = f" ({core})" if (core := picture.core(seen).get("belief")) else ""
        lines.append(NAME_NOW.format(core=said))
    if allowed and (due or pressing):
        lines.append(MOVE_NOW)
    elif allowed:
        lines.append(MOVE_MAY)
    else:
        lines.append(MOVE_NOT_YET if naming_due else MOVE_NOT)
    if allowed and frameworks:
        lines.append(frameworks)
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


def replied(stored: dict, reply: ConversationReply, *, check_written: bool, allowed: bool = False) -> dict:
    """The record once the reply is written, before Mani reads what their message adds (read, after the reply is
    sent): where the reply judged the heart of it, what its window landed on, on a move to the set its case, its plan
    and what it asked itself, and that asking for help presses toward the framework. A move to the set is always
    ready. A move allowed and not made is kept, so the next reply is due to make it (due)."""
    heart = understanding.READY if check_written else reply.heart
    merged = understanding.merge(stored, None, heart)
    if reply.window is not None and reply.shape in ("window", "insight"):
        # What the window landed on is explored, so the funnel moves to the next (2026-11-03).
        merged[picture.KEY] = picture.explored(merged.get(picture.KEY), reply.window.closest)
    if check_written:
        merged = understanding.merge_check(merged, case(reply, merged.get(picture.KEY)))
    if plan := " ".join((reply.plan or "").split()):
        merged[PLAN] = plan
    thinking = {
        key: value for key, value in (
            ("need", reply.need), ("needs_info", reply.needs_info), ("info", reply.info_needed),
            ("shape", reply.shape), ("window", reply.window.model_dump() if reply.window else None),
            ("insight", reply.insight), ("from", reply.insight_from), ("link", reply.link), ("move", reply.move),
            ("asked_for_help", reply.asked_for_help or None), ("heart", heart),
            ("held_back", (allowed and not check_written) or None),
        ) if value not in (None, "")
    }
    merged = context.with_insight(merged, reply.insight)
    if reply.progress is not None:
        merged = context.with_progress(merged, reply.progress.kinds, reply.progress.adds)
    if thinking:
        merged[THINKING] = thinking
    else:
        merged.pop(THINKING, None)
    # Kept until read says otherwise, so a reading that never arrives does not lose that they asked.
    if stored.get(TOWARD) or reply.asked_for_help:
        merged[TOWARD] = True
    # A record from before 2026-10-29 said helping; the chat no longer helps, it presses toward the framework.
    merged.pop("helping", None)
    return merged


def due(understood: dict | None) -> bool:
    """Whether this reply should move to the set of questions, when it may: the heart of it was confirmed, or the last
    reply was allowed to move and did not (the father chat, replayed 2026-11-11: allowed for three turns, the model
    kept asking, and no offer came). One reply of waiting, never more."""
    understood = understood or {}
    return understanding.ready(understood) or bool((understood.get(THINKING) or {}).get("held_back"))


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
    asked = bool((stored.get(THINKING) or {}).get("asked_for_help"))
    if toward(stored, asked, merged):
        merged[TOWARD] = True
    else:
        merged.pop(TOWARD, None)
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
