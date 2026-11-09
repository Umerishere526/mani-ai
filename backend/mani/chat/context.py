# ABOUTME: The hidden [ctx] block prefixed to the user's message for one turn only.
# ABOUTME: Built fresh from database state and never stored, so history cannot replay it.

from __future__ import annotations

import re
from difflib import SequenceMatcher

from mani.chat import body, repairs, understanding, walk
from mani.chat.techniques import OFFERING
from mani.db.threads import TurnContext
from mani.llm.schema import Moment
from mani.models.rows import (
    Framework,
    Message,
    MessageRole,
    TechniqueOutcome,
    TechniqueState,
)

# How many messages must pass after a declined offer, or a check they did not confirm, before
# Mani may check its understanding again: three of its replies (muhammad, 2026-09-24).
COOLDOWN_AFTER_DECLINE = 6

# After they corrected what an offer said back about them (the client meeting, 2026-11-03), no wait: the reply to the
# correction says the corrected reading back, and once their next message confirms it the offer may come again.
COOLDOWN_AFTER_CORRECTION = 0

# Their message before which Mani never checks its understanding, however ready its reading seems: Lolly's own
# conversations reached the heart of it at about the tenth exchange (muhammad, 2026-10-26, R33).
CHECK_FROM = 5
# The greeting, the style they tapped, and that style's opener.
OPENING_MESSAGES = 3

# The default when neither the conversation nor the profile has chosen a style yet.
# `conversation_style` is set per-thread by PATCH /v1/threads/{id} and wins over
# profile.support_style, which holds the onboarding answer.
DEFAULT_STYLE = "supportive"

_CTX_BLOCK = re.compile(r"^\[ctx\].*?\[/ctx\]\s*", re.DOTALL)
# How many of Mani's own questions a turn is shown, so none is asked again, in the chat and in the questions alike.
ASKED_LIMIT = 6
_QUESTION = re.compile(r"[^.!?\n]*\?")
# The same question in other words, as it was asked twice (the daughter chat, 2026-11-03).
SAME_QUESTION = (
    "never ask one again, nor one about the same thing in other words: \"what feels hardest about leaving them\" and "
    "\"what feels most worrying about being away\" are one question"
)


def strip(content: str) -> str:
    """Remove a context block from stored text.

    Kept for messages written by the previous system, which prefixed the block and then
    saved it - so a long thread replayed up to ten stale and mutually contradictory
    blocks to the model on every turn. Nothing written here contains one.
    """
    return _CTX_BLOCK.sub("", content, count=1)


_CTX_MARKER = re.compile(r"\[\s*(/?)\s*ctx\s*\]", re.IGNORECASE)


def disarm(text: str) -> str:
    """Turn any [ctx] or [/ctx] a person typed into inert text.

    The model is told the block is backend metadata, so a person who could type one could
    set their own style, stage guidance or cooldown - and it would replay from history for
    the next twenty turns. Only the brackets change; what they wrote is still sent.
    """
    return _CTX_MARKER.sub(lambda m: f"({m.group(1)}ctx)", text)


def asked_before(history: list[Message]) -> list[str]:
    """The questions Mani asked in this conversation, latest last, so a turn can be shown them."""
    asked = [
        " ".join(q.split()) for m in history if m.role is MessageRole.MANI for q in _QUESTION.findall(m.content)
    ]
    return [q for q in asked if q][-ASKED_LIMIT:]


def last_question(history: list[Message]) -> str | None:
    """The question Mani's last reply ended on, or None when it asked nothing."""
    last = next((m for m in reversed(history) if m.role is MessageRole.MANI), None)
    asked = _QUESTION.findall(last.content) if last else []
    return " ".join(asked[-1].split()) if asked else None


# A message this close to Mani's last reply is that reply sent back, not an answer to it. Long enough that "yes",
# "okay" or a short phrase of Mani's they repeat is never caught (the friend chat, 2026-11-04).
COPY_SHARE = 0.9
COPY_MIN_CHARS = 40


def _plain(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9']+", text.casefold().replace("\u2019", "'")))


def copies_last_reply(content: str, history: list[Message]) -> bool:
    """Whether their message is Mani's last reply sent back, as a copy and paste would."""
    last = next((m for m in reversed(history) if m.role is MessageRole.MANI), None)
    theirs = _plain(content)
    if last is None or len(theirs) < COPY_MIN_CHARS:
        return False
    return SequenceMatcher(None, theirs, _plain(last.content)).ratio() >= COPY_SHARE


def their_messages(ctx: TurnContext) -> int:
    """How many messages the person has sent. The reply to their Nth is written at 3 + 2(N - 1)."""
    return (ctx.thread.message_count - OPENING_MESSAGES) // 2 + 1


def live(technique: TechniqueState | None) -> TechniqueState | None:
    """The framework that is live on this turn, offered and awaiting an answer or accepted and
    mid-way, or None. A finished row (phase cleared) or a declined one stays stored, because the
    cooldowns are measured from it, but it is not live."""
    if technique is None or technique.phase is None:
        return None
    if technique.outcome not in (TechniqueOutcome.OFFERED, TechniqueOutcome.ACCEPTED):
        return None
    return technique


def check_open(ctx: TurnContext) -> bool:
    """Whether Mani's last reply checked its understanding, so this message answers the check.
    Any later turn finds it used, whatever happened on this one (spec 0006)."""
    at = ctx.thread.check_at_message_count
    return at is not None and at == ctx.thread.message_count and live(ctx.technique) is None


def may_check(ctx: TurnContext) -> bool:
    """Whether this reply may check Mani's understanding: from their CHECK_FROM-th message, with no framework
    live and no check waiting for its answer, and once the cooldowns after the last check and the last offer
    have passed. Code stores the check only when the same reply judges the heart of it ready (R33). The only
    way to an offer (spec 0006)."""
    if their_messages(ctx) < CHECK_FROM:
        return False
    if live(ctx.technique) is not None or check_open(ctx):
        return False
    count, at = ctx.thread.message_count, ctx.thread.check_at_message_count
    if at is not None and count - at < COOLDOWN_AFTER_DECLINE:
        return False
    # Only a declined offer holds the next check back. A finished framework does not (muhammad, 2026-10-27): its
    # reading is cleared when it finishes, so a new check needs a fresh understanding first.
    technique = ctx.technique
    cooldown = (
        COOLDOWN_AFTER_CORRECTION if (ctx.thread.understanding or {}).get(understanding.CORRECTED)
        else COOLDOWN_AFTER_DECLINE
    )
    return (
        technique is None
        or technique.outcome is not TechniqueOutcome.DECLINED
        or count - technique.at_message_count >= cooldown
    )


def moment(
    technique: TechniqueState | None,
    outcome: TechniqueOutcome | None,
    retiring_framework_id: str | None,
    concern: bool,
    check_open: bool = False,
) -> Moment:
    """What is happening this turn, from the database and the safety screen alone; the first that
    matches wins. `technique` is the live row, offered or running, and `outcome` is its outcome,
    accepted when a Try it tap starts it this turn. `check_open` is a check in Mani's last reply."""
    if concern:
        return Moment.CONCERN
    if retiring_framework_id is not None:
        return Moment.BODY
    if technique is None:
        return Moment.CHECK_OPEN if check_open else Moment.CHATTING
    if outcome is TechniqueOutcome.ACCEPTED:
        return Moment.BODY if technique.phase in body.STAGES else Moment.IN_STAGES
    if outcome is TechniqueOutcome.OFFERED:
        return Moment.OFFER_OPEN
    return Moment.CHATTING


def resolve_style(ctx: TurnContext) -> str:
    """The conversation style in force this turn: which style layer is composed, and which of a
    framework's style variants is surfaced.

    The conversation's own choice wins over the profile's, which is the point of having
    both: onboarding sets a default, and a thread may differ from it without changing it.
    """
    if ctx.thread.conversation_style:
        return ctx.thread.conversation_style.value
    if ctx.profile and ctx.profile.support_style:
        return ctx.profile.support_style.value
    return DEFAULT_STYLE


# What each line of the block means, sent under the line itself and only for the value it has
# this turn: a vague reply carries the vague guidance and nothing about being heard. Keeping the
# meaning beside the value is also what keeps the two from drifting apart, which they did while
# the meanings lived in response_format.md (2026-10-08).
_MEANING: dict[str, str | dict[str, str]] = {
    "conversation_style": (
        "the style they chose, for the whole conversation. Your instructions say what each reply is "
        "trying to do in it."
    ),
    "conversation_phase": {
        "understanding": (
            "nothing has been offered yet. Follow their story in order toward the heart of it: what "
            "happened, what it means to them, what it says about them, down to the core and the feeling underneath."
        ),
        "framework": "the questions are running, so follow the stage.",
        "talking": (
            "an offer was declined or the questions finished, so talk with them, following "
            "what they say."
        ),
    },
    "offer_waiting": {
        "yes": (
            "your last reply offered and they typed instead of tapping. On a yes, begin. When they correct what the "
            "offer said about them, set offer_answer corrected: say back what you understand now, from their words, "
            "in a sentence, and ask one question that lets them confirm or add to it. Otherwise follow them."
        ),
    },
    "check": {
        "open": (
            "your last reply gave your insight into the core and asked whether it captures what they feel. Set "
            "check_answer. A clear yes always brings the offer: fill offer for the set closest to "
            "what they confirmed, even when its Use it when does not fit exactly; when something really happening is "
            "part of it, the set looks at what they tell themselves about it. Anything else, follow what they said "
            "toward the root of it, without offering fixes: the set of questions is the way to work it out."
        ),
    },
    "picture": (
        "your picture of them so far, from the whole conversation, the same in the chat and in a framework: what "
        "is happening, what they feel and about what, what they tell themselves, what they say is really "
        "happening, what they want, what is in the way, risks, the situation in focus, and the core with the feeling "
        "underneath, as you read it. Build on it and never "
        "ask for what it holds. In picture, report only what their message adds or changes."
    ),
    "understanding": "the feelings they named, kept for you, and where your last reply judged the heart of it.",
    "their_case": (
        "what you and they found before the questions began: the feelings they named and the case they "
        "confirmed, the core of it and the feeling underneath. Every question you ask and every "
        "possibility you offer is about this core and the feeling underneath it, never generic. Never ask them again for "
        "anything in it: say it back and build on it."
    ),
    "since_last": "how many messages have passed since the last offer.",
    "this_thread": (
        "what was last offered in this conversation and how it went. One they declined may come "
        "back once the cooldown has passed, if it still fits. One they just finished may not. "
        "If they ask for one they declined, that is a yes at any time, so begin it."
    ),
    "history": "what was tried earlier in this conversation, and whether it helped.",
    "current_phase": "the stage the questions are on, as last recorded.",
    # manasa's safety test, 2026-11-06: "stay with what they said... leave room for more" was all this said, and each
    # time she pushed back Mani agreed to drop it and went back to ordinary conversation.
    "safety": {
        "open": (
            "something said in this conversation may mean they are not safe, and it is not settled. Stay with them and "
            "what they are going through, warmly and plainly, listening more than asking. Come back to their safety "
            "gently in your own words, in this reply unless your last one asked and they have not answered yet; then "
            "stay with what they said and come back to it next time. A refusal, a change of subject or frustration "
            "with the question changes how you ask, never whether it stays open: never say you will stop asking or "
            "drop it, and never steer to everyday topics or offer a choice of them. No set of questions, no offer, no "
            "library. Report safety.answer."
        ),
        "unsafe": (
            "they may be in danger now: a plan, the means near them, fear of what they might do, or having acted. "
            "Stay with them and do not let the conversation move on. In every reply, in plain words and briefly, ask "
            "them to reach a person now, someone they trust or their local emergency number, and to put distance "
            "between themselves and anything they could use; a text is enough if speaking is too hard. Never repeat a "
            "sentence you already used, never lecture, never end the conversation. If they say they are safe, ask "
            "gently what has changed. Report safety.answer."
        ),
    },
    "recent_crisis": {
        "yes": (
            "another conversation of theirs was flagged recently. You know only that. Go gently "
            "and slowly, and do not mention it unless they do."
        ),
    },
    "framework_starting": {
        "yes": "they just said yes, so the walk reaches its first stage: next says what your text is for.",
    },
    "if_they_say_yes": (
        "only if their message says yes to this set, the walk reaches its first stage, and next says "
        "what your text is for. Otherwise follow them."
    ),
    "active_framework": (
        "the set of questions running, with its stages in order. Then the stage you are on, with "
        "its purpose, what to listen for, when it is done, its boundaries and what to do if "
        "unclear. Its ask is a model question already in this style."
    ),
    "stages_known": (
        "what they have said for each stage the walk has reached. Never ask for what a stage already "
        "holds. Where a part is still to ask, ask only that part. In stage_updates report the stage in "
        "force from their message."
    ),
    "landed_on": "what they said for the last of the questions, in their words: where they ended up.",
    "asked": f"questions you already asked: {SAME_QUESTION}.",
    "last_ending": (
        "how your last reply ended. End this one differently: \"is there more to it?\" twice in a row reads as a script "
        "(the father chat, 2026-11-04)."
    ),
    "not_helping": {
        "stalled": (
            "two turns on this stage have brought nothing new: the questions have stopped helping. In your own words, "
            "offer to step out of them and help with what they need in the conversation instead, and set "
            "framework_fit. Do not ask this stage's question again."
        ),
        "situation": (
            "what they describe is really happening, not a thought to question. Say so plainly, offer in your own "
            "words to step out of the questions and help with it in the conversation, and set framework_fit to "
            "real_not_belief."
        ),
    },
    # What the questions left them with, kept after they end (muhammad, 2026-11-06: finishing the questions is not
    # solving the problem): what they took away and what is still open, carried into the chat that follows.
    "after_questions": (
        "what they took away from the questions they finished, and what is still open for them. Continue from what is "
        "still open when it matters to them; never treat the questions as having solved it, and never ask again for "
        "what they took away."
    ),
    # What the conversation has explored and given so far (muhammad, 2026-11-06: every question earns its place, and
    # several aha moments rather than one): read after each reply and carried into the next.
    "insights_given": (
        "the insights you already gave in this conversation. Never give one again, even from a new angle: the next "
        "insight adds something new, a connection, a pattern, a need or an assumption to reconsider."
    ),
    "recent_progress": "what your recent replies added. This reply adds something they did not.",
    "explored": (
        "the parts of their experience already explored: never ask about them again unless their message opens "
        "something new there."
    ),
    "worth_exploring": (
        "the parts worth exploring next and why, most useful first: choose from them, or follow their message when it "
        "opens something else."
    ),
    "connections": (
        "connections you can infer and have not said. Offer one as your reading, a possibility they can correct, once "
        "their own words support it; one at a time."
    ),
    "stage_explored": (
        "the parts of this stage already opened: never ask about them again. The stage moves on when its purpose is met "
        "(stage_ready_when) and nothing left in stage_explore would help them now; it stays while something would."
    ),
    "exit_offered": {
        "yes": (
            "your last reply offered to step out of the questions. If they agree, report stop and go on with them in "
            "your text. If they want to carry on, carry on with the stage."
        ),
    },
    "body_step": {
        body.ASK: (
            "they were asked whether they would like to check in with their body, with Yes and Not right now. In "
            "body report yes or no, pain, or unclear. Code sends what follows."
        ),
        body.BODY: (
            "they were asked where they feel tension, with Chest, Stomach, Head, Somewhere Else and No Tension. "
            "In body report the place they name (chest, stomach, head, jaw_face, hands, eyes, feet, toes, arms), "
            "other when they say somewhere else and name no place (your text asks where), nearest when they name "
            "a place with no exercise (your text offers the closest exercise in your own words and asks whether "
            "they would like to try it), none for no tension, no for declining, pain, or unclear. When they say "
            "yes to the closest exercise, report the place you offered. Code sends the client's exercise."
        ),
        body.PRACTICE: (
            "they were guided through one exercise and asked how their body feels. In body report better, same, "
            "worse, pain or unclear. Never assume tension has eased. Code sends the client's lines."
        ),
        body.EFFECT: (
            "they were asked whether the whole conversation helped with what brought them. In body report helped, "
            "somewhat, not_really or unclear. Code sends the client's lines."
        ),
        "closing": (
            "they were offered Keep Chatting, Go to Library and Finish for Now. If they want to end for now, report "
            "finish and write one warm line with no question. Otherwise report keep_chatting and continue from "
            "their_case and landed_on in the same shape as before the questions: a mirror of where they ended up, one "
            "open question, and possibilities in options. Never ask what they would like to talk about, and never ask "
            "again for anything their_case already holds. What they chose to do in landed_on is settled: never ask "
            "them to pick, name or narrow it again (the father chat, 2026-11-04); go on from what is still open (after_questions)."
        ),
    },
}


# What a stage that carries the case asks of its question: the case they confirmed, said back in their words,
# whatever the framework (a stage says so with `carries_case: true`).
CARRIES_CASE = (
    "their_case is in this question, in their words: the core and how they feel, the feeling underneath included "
    "once they accepted it. Fit as much as the style allows, never a list, never anything they did not say."
)


# On the understanding record: what the finished questions left them with, what they took away (landing's words) and
# what is still open, set on the reply that ends them (muhammad, 2026-11-06).
AFTER = "after_questions"
# What recent replies added, newest last, and the after-reply reading's map of what is explored and what can be inferred.
PROGRESS = "progress"
PROGRESS_KEPT = 4
EXPLORATION = "exploration"
INSIGHTS = "insights"
INSIGHTS_KEPT = 4


def after_line(understood: dict | None) -> str | None:
    """What the finished questions left them with, as one line, or None."""
    after = (understood or {}).get(AFTER) or {}
    parts = []
    if after.get("took_away"):
        parts.append(f"took away: {disarm(after['took_away'])}")
    if after.get("still_open"):
        parts.append("still open: " + " | ".join(disarm(o) for o in after["still_open"]))
    return "; ".join(parts) or None


def meaning_of(key: str) -> str:
    """What a [ctx] key means, as a sentence, for the chat's note; empty when it has none or depends on its value."""
    meaning = _MEANING.get(key)
    return meaning[0].upper() + meaning[1:] if isinstance(meaning, str) and meaning else ""


def journey(understood: dict | None) -> list[tuple[str, str]]:
    """What the conversation has given and explored so far, as (key, value) pairs for [ctx] and the chat's note."""
    stored = understood or {}
    pairs: list[tuple[str, str]] = []
    if given := stored.get(INSIGHTS):
        pairs.append(("insights_given", " | ".join(disarm(i) for i in given)))
    if recent := [p.get("adds") for p in stored.get(PROGRESS) or [] if p.get("adds")]:
        pairs.append(("recent_progress", " | ".join(disarm(r) for r in recent)))
    seen = stored.get(EXPLORATION) or {}
    if seen.get("explored"):
        pairs.append(("explored", ", ".join(seen["explored"])))
    if seen.get("next"):
        pairs.append(("worth_exploring", " | ".join(f"{n['area']}: {disarm(n['why'])}" for n in seen["next"])))
    if seen.get("connections"):
        pairs.append(("connections", " | ".join(disarm(c) for c in seen["connections"])))
    return pairs


def with_progress(stored: dict, kinds: list[str], adds: str | None) -> dict:
    """The record with this reply's progress kept, newest last, PROGRESS_KEPT at most."""
    if not kinds and not (adds or "").strip():
        return stored
    entry = {"kinds": list(kinds), **({"adds": " ".join(adds.split())} if (adds or "").strip() else {})}
    return {**stored, PROGRESS: [*(stored.get(PROGRESS) or []), entry][-PROGRESS_KEPT:]}


def with_insight(stored: dict, insight: str | None) -> dict:
    """The record with an insight this reply gave kept, so none is given twice, INSIGHTS_KEPT at most."""
    said = " ".join((insight or "").split())
    if not said:
        return stored
    return {**stored, INSIGHTS: [*(stored.get(INSIGHTS) or []), said][-INSIGHTS_KEPT:]}


def _meaning(key: str, value: object) -> list[str]:
    """The line that says what `key` means for the value it has this turn, if it has one."""
    meaning = _MEANING.get(key)
    if isinstance(meaning, dict):
        meaning = meaning.get(str(value))
    return [f"  means: {meaning}"] if meaning else []


def _line(key: str, value: object) -> list[str]:
    """A key, its value, and what that value means for this turn."""
    return [f"{key}: {value}", *_meaning(key, value)]


def build(
    ctx: TurnContext,
    *,
    framework: Framework | None = None,
    history: list[Message] | None = None,
    safety: str = "clear",
    offer_waiting: bool = False,
    starting: bool = False,
    yes_framework: Framework | None = None,
    landed_on: str | None = None,
) -> str:
    """Format the metadata header for this turn.

    Every value is read from the composed turn snapshot, so the block describes what the
    database holds rather than what an in-memory copy was mutated to mid-request. `framework` and
    `history` are what the framework content and the caller's own history add - both optional,
    so a turn with neither still formats exactly as before.

    `framework` is the one already active. `starting` is a turn that opens it, and `yes_framework`
    the set a yes in this message would open; both ask the reply to report what they already said.

    `history` is the same window the caller already loads for the model's own conversation
    view - nothing new is fetched for it.
    """
    technique = ctx.technique
    # Named first because every stage_ask and offer_ask below is resolved from it.
    lines: list[str] = _line("conversation_style", resolve_style(ctx))
    # Where the conversation stands on safety, from the thread and this message's screen (chat/safety.State). While it
    # is not clear the framework waits: no stage question to relay, no offer to make.
    safety_concern = safety != "clear"
    if safety_concern:
        lines += _line("safety", safety)
    if ctx.recent_crisis:
        lines += _line("recent_crisis", "yes")

    running = (
        framework is not None and technique is not None and technique.phase
        and not safety_concern
    )
    if running:
        phase = "framework"
    elif not ctx.techniques_offered and technique is None:
        # Nothing offered yet: the exchanges the client's cadence spends asking,
        # checking and confirming before a framework is offered.
        phase = "understanding"
    else:
        phase = "talking"
    lines += _line("conversation_phase", phase)
    if seen := understanding.picture_line(ctx.thread.understanding):
        lines += _line("picture", seen)
    for key, value in journey(ctx.thread.understanding):
        lines += _line(key, value)
    understood = understanding.render(ctx.thread.understanding)
    if understood:
        # Once a framework is running or about to start, the findings are the case its questions are about.
        in_play = (
            bool(running) or (yes_framework is not None and not safety_concern) or body.closing_shown(history or [])
        )
        lines += _line("their_case" if in_play else "understanding", understood)
    if offer_waiting:
        # Mani's last reply was an offer, and they typed rather than tapped.
        lines += _line("offer_waiting", "yes")
    if not safety_concern and body.closing_shown(history or []):
        lines += _line("body_step", "closing")
        if landed_on:
            lines += _line("landed_on", disarm(landed_on))
        if after := after_line(ctx.thread.understanding):
            lines += _line("after_questions", after)

    # An offer only on the answer to Mani's check (spec 0006). The check itself is made in Mani's own conversation.
    if not safety_concern and check_open(ctx):
        lines += _line("check", "open")
    if technique is not None:
        since_last = ctx.thread.message_count - technique.at_message_count
        lines += _line("since_last", since_last)
        lines += _line("this_thread", f"{technique.framework_id} ({technique.outcome})")
        if technique.phase:
            lines += _line("current_phase", technique.phase)

    if ctx.summary and ctx.summary.techniques_tried:
        tried = ", ".join(
            f"{t.name} ({'helpful' if t.helpful else 'not helpful'})"
            for t in ctx.summary.techniques_tried
        )
        lines += _line("history", tried)

    if running:
        lines += _running_lines(ctx, framework, offer_waiting=offer_waiting, starting=starting)
        if asked := asked_before(history or []):
            lines += _line("asked", disarm(" | ".join(asked)))
        if ending := last_question(history or []):
            lines += _line("last_ending", disarm(ending))
    if yes_framework is not None and not safety_concern:
        lines += _line("if_they_say_yes", yes_framework.id)
        lines += _start_lines(yes_framework, resolve_style(ctx))

    return "[ctx]\n" + "\n".join(lines) + "\n[/ctx]\n\n"


def _running_lines(
    ctx: TurnContext, framework: Framework, *, offer_waiting: bool, starting: bool
) -> list[str]:
    """The running set: on the turn it starts, the first stage it reaches; at the offer, the offering
    stage; on a stage, that stage, what is stored for each stage, what this reply is for and the next
    stage in full, which the reply judges when the walk reaches it (2026-10-13)."""
    technique, style = ctx.technique, resolve_style(ctx)
    lines = _line("active_framework", framework.id)
    lines.append(f"framework_stages: {', '.join(framework.phases)}")
    if starting:
        return lines + _line("framework_starting", "yes") + _start_lines(framework, style)
    if technique.phase in body.STAGES:
        # The body check-in is the client's script, sent by code: the model only reads the answer.
        return lines + _line("body_step", technique.phase)
    stage = _stage_lines("stage", framework, technique.phase, style)
    if offer_waiting:
        # The offering stage's question is the offer they have just typed past.
        stage = [line for line in stage if not line.startswith("stage_ask:")]
    lines.extend(stage)
    if technique.phase == OFFERING:
        return lines
    known = technique.stages_known.get(framework.id) or {}
    lines += _line("stages_known", _stored(framework, known, technique.phase))
    if technique.phase in walk.content_stages(framework):
        in_force = known.get(technique.phase) or {}
        kind = ((ctx.thread.understanding or {}).get("picture") or {}).get("problem_type")
        if in_force.get("exit_offered"):
            lines += _line("exit_offered", "yes")
        elif kind == "situation":
            lines += _line("not_helping", "situation")
        elif in_force.get("stalls", 0) >= walk.STALLS_TO_STEP_OUT:
            lines += _line("not_helping", "stalled")
        if opened := in_force.get(walk.COVERED):
            lines += _line("stage_explored", ", ".join(opened))
    if technique.phase in walk.content_stages(framework):
        lines.append(f"next: {walk.next_line(framework, technique.phase)}")
    index = framework.phase_index(technique.phase)
    following = framework.phases[index + 1] if 0 <= index < len(framework.phases) - 1 else None
    if following:
        lines.extend(_stage_lines("next_stage", framework, following, style))
    return lines


def _stored(framework: Framework, known: dict[str, dict], phase: str) -> str:
    """Every content stage with its stored status, and their words when there are some. A stage after
    the one in force is not reached yet, whatever an earlier version stored for it."""
    at = framework.phase_index(phase)
    parts = []
    for stage in walk.content_stages(framework):
        ahead = framework.phase_index(stage) > at
        entry = {} if ahead and (known.get(stage) or {}).get("status") != "done" else known.get(stage) or {}
        status = entry.get("status") or ("not reached" if ahead else "missing")
        said = entry.get("said")
        part = f"{stage} {status}"
        if status == "partial" and entry.get("gap"):
            part += f", still to ask {entry['gap']}"
        parts.append(f'{part}: "{disarm(said)}"' if said else part)
    return " | ".join(parts)


# A stage is a step, not an exam: it never needs complete or certain answers, and a person asked
# the same thing a third time feels interrogated (live, 2026-10-08: five times running).
def _start_lines(framework: Framework, style: str) -> list[str]:
    """On a turn that can start the set: what the reply does with the first stage, which the walk
    reaches, and that stage in full to judge it by."""
    first = walk.content_stages(framework)[0]
    return [f"next: the walk reaches {first}: {walk.reach_line(first)}",
            *_stage_lines("next_stage", framework, first, style)]

def _stage_lines(prefix: str, framework: Framework, phase: str, style: str) -> list[str]:
    """One stage's full guidance - current or next - resolved to one conversation style.

    Purpose, listening cues, readiness and boundaries are clinical rather than tonal and do
    not vary; `ask` is the one leaf a style changes, so only the resolved style's variant is
    sent rather than all three.
    """
    stage = framework.stages.get(phase)
    if not stage:
        return [f"{prefix}: {phase}"]

    lines = [f"{prefix}: {phase}"]
    for field in ("purpose", "listen_for", "ready_when"):
        if stage.get(field):
            lines.append(f"{prefix}_{field}: {stage[field]}")
    if prefix == "next_stage" and stage.get("reach"):
        # How the stage is judged when the walk reaches it, beside its ready_when.
        lines.append(f"{prefix}_reach: {stage['reach']}")
    if stage.get("boundaries"):
        lines.append(f"{prefix}_boundaries: " + "; ".join(stage["boundaries"]))
    if stage.get("if_unclear"):
        # A body route branch is shown by its id, which the reply names in `body`: code sends its text.
        rendered = " | ".join(
            f"{e['id']}: {e['when']}" if e.get("id") else f"if {e['when']}: {repairs.reply_for(e, style)}"
            for e in stage["if_unclear"]
        )
        lines.append(f"{prefix}_if_unclear: {rendered}")
    if prefix == "stage" and stage.get("explore"):
        # The different parts of the experience this stage can open, each only when it adds something.
        lines.append(f"{prefix}_explore: " + " | ".join(f"{e['id']}: {e['about']}" for e in stage["explore"]))
    ask = (stage.get("ask") or {}).get(style)
    if ask:
        lines.append(f"{prefix}_ask: {ask}")
    if stage.get("carries_case"):
        lines.append(f"{prefix}_carries_case: {CARRIES_CASE}")
    return lines
