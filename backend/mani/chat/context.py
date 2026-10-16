# ABOUTME: The hidden [ctx] block prefixed to the user's message for one turn only.
# ABOUTME: Built fresh from database state and never stored, so history cannot replay it.

from __future__ import annotations

import re

from mani.chat import repairs, understanding, walk
from mani.chat.greeting import AFTER_FRAMEWORK_QUESTIONS, CHAT_MORE_LABEL
from mani.chat.techniques import OFFERING
from mani.db.threads import TurnContext
from mani.llm.schema import Moment
from mani.models.rows import (
    ENDING_STAGES,
    Framework,
    Message,
    MessageRole,
    TechniqueOutcome,
    TechniqueState,
)

# How many messages must pass after a declined offer, or a check they did not confirm, before
# Mani may check its understanding again: three of its replies (muhammad, 2026-09-24).
COOLDOWN_AFTER_DECLINE = 6

# The message by which a check is expected, "two to four exchanges" in the client's cadence. Only
# logged when it passes without one, never sent to the model (spec 0006, AC-11).
CHECK_EXPECTED_BY = 5
# The greeting, the style they tapped, and that style's opener.
OPENING_MESSAGES = 3
COOLDOWN_AFTER_COMPLETE = 45

# The default when neither the conversation nor the profile has chosen a style yet.
# `conversation_style` is set per-thread by PATCH /v1/threads/{id} and wins over
# profile.support_style, which holds the onboarding answer.
DEFAULT_STYLE = "supportive"

_CTX_BLOCK = re.compile(r"^\[ctx\].*?\[/ctx\]\s*", re.DOTALL)


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


def _after_framework_question(history: list[Message]) -> str | None:
    """The next of the client's three questions, once a framework has ended.

    A framework ends on the reply that offers Chat More. The questions asked since, that reply
    included, are read from Mani's own replies, so they come in order and none twice. Once Mani
    has replied as many times as there are questions, or has made an offer since, the
    conversation has moved on and none are offered.
    """
    mani = [m for m in history if m.role is MessageRole.MANI]
    ended = next(
        (i for i in range(len(mani) - 1, -1, -1)
         if any(str(o.get("label", "")).lower() == CHAT_MORE_LABEL.lower()
                for o in (mani[i].prompt_options or []))),
        None,
    )
    if ended is None:
        return None
    since_ended = mani[ended + 1:]
    if len(since_ended) >= len(AFTER_FRAMEWORK_QUESTIONS) or any(
        o.get("technique") for m in since_ended for o in (m.prompt_options or [])
    ):
        return None
    since = " ".join(m.content.lower() for m in mani[ended:])
    return next((q for q in AFTER_FRAMEWORK_QUESTIONS if q.lower().rstrip("?") not in since), None)


def cooldown_for(outcome: TechniqueOutcome) -> int:
    return (
        COOLDOWN_AFTER_COMPLETE
        if outcome is TechniqueOutcome.ACCEPTED
        else COOLDOWN_AFTER_DECLINE
    )


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
    """Whether this reply may check Mani's understanding: once the problem, its core issue and what
    is in their control are all stored, which takes at least four of their messages, so the reply
    that receives the control answer is an ordinary one (spec 0007, AC-10); with no framework live
    and no check waiting for its answer, and once the cooldowns after the last check and the last
    offer have passed. The only way to an offer (spec 0006)."""
    if understanding.next_step(ctx.thread.understanding) is not None:
        return False
    if live(ctx.technique) is not None or check_open(ctx):
        return False
    count, at = ctx.thread.message_count, ctx.thread.check_at_message_count
    if at is not None and count - at < COOLDOWN_AFTER_DECLINE:
        return False
    technique = ctx.technique
    return technique is None or count - technique.at_message_count >= cooldown_for(technique.outcome)


def moment(
    technique: TechniqueState | None,
    outcome: TechniqueOutcome | None,
    retiring_framework_id: str | None,
    framework: Framework | None,
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
        phase = technique.phase
        if phase in ENDING_STAGES or (framework is not None and phase == framework.closing):
            return Moment.BODY
        return Moment.IN_STAGES
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
        "the style they chose, for the whole conversation. conversation_style in your instructions "
        "says what each reply is trying to do in it."
    ),
    "conversation_phase": {
        "understanding": (
            "nothing has been offered yet. Take in what they said, then ask for what you still "
            "need: the problem, the core issue under it, or what is in their control."
        ),
        "framework": "the questions are running, so follow the stage.",
        "talking": (
            "an offer was declined or the questions finished, so talk with them, following "
            "what they say."
        ),
    },
    "offer_waiting": {
        "yes": (
            "your last reply offered and they typed instead of tapping. On a yes, begin. "
            "Otherwise follow them."
        ),
    },
    "check": {
        "may_check": (
            "the problem, its core issue and what is in their control are all found. Give your reading "
            "now by filling check, from their words only, and ask the one question that moves forward. "
            "Never ask whether you have it right, and never ask for what is already clear."
        ),
        "open": (
            "your last reply gave your reading. Set check_answer for the reading, not for your question. "
            "Going along with it, even by answering your question with no or not yet, always brings the offer: fill offer for the set closest to what "
            "they told you, even when its Use it when does not fit exactly. Anything else, follow what "
            "they said toward the root of it."
        ),
    },
    "understanding": (
        "what they have told you so far, kept for you. A step marked missing is still to be found. In "
        "understanding_update report only what their message names or changes."
    ),
    "feeling_change": (
        "your last reply asked whether their feeling has moved from the first word to the second. Set "
        "feeling_answer from how they take that, then go on with what the rest of this block says."
    ),
    "understanding_next": {
        "problem": (
            "the problem is not pinned down yet. Help them narrow it to what actually happens: who, "
            "what, how often, what is expected of them. If their message already gives it, report it "
            "and ask about the core issue under it."
        ),
        "core_issue": (
            "the problem is clear, what lies under it is not. Ask plainly: what usually happens next, "
            "what falls on them, or what keeps it going. A feeling, such as not being enough, is not yet "
            "the core issue: ask what makes them feel it or what keeps it going. Once their answers show "
            "the core issue, offer it in your reply as your understanding, report it, and ask what is in "
            "their control. They don't need to name it themselves."
        ),
        "control": (
            "the problem and its core issue are clear. Ask what is in their control: what they could "
            "do, influence or decide about it, once, never twice in other words. If they say they don't "
            "know, that is their answer: report in_their_control as \"you're not sure yet\"."
        ),
    },
    "since_last": "how many messages have passed since the last offer.",
    "this_thread": (
        "what was last offered in this conversation and how it went. One they declined may come "
        "back once the cooldown has passed, if it still fits. One they just finished may not. "
        "If they ask for one they declined, that is a yes at any time, so begin it."
    ),
    "history": "what was tried earlier in this conversation, and whether it helped.",
    "library_pending": {"yes": "offer the Library before anything new."},
    "current_phase": "the stage the questions are on, as last recorded.",
    "finished_framework": (
        "what they found in the framework they finished, stage by stage in their words. Use it when they "
        "ask about it or say it did not help. Never summarise it unasked."
    ),
    "safety": {
        "concern": (
            "something they said may mean they are not safe. No stage question and no offer. "
            "Stay with what they said, gently and plainly, and leave room for more. The "
            "questions will wait."
        ),
    },
    "recent_crisis": {
        "yes": (
            "another conversation of theirs was flagged recently. You know only that. Go gently "
            "and slowly, and do not mention it unless they do."
        ),
    },
    "recent_styles": "the shapes of your last few replies. A shape may come back.",
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
        "what they have said for each stage the walk has reached, kept for you. Never ask for what a "
        "stage already holds. In stage_updates report the stage in force from their message."
    ),
    "after_framework_question": (
        "they kept chatting after the questions ended and are still on the same issue. Reflect "
        "what they said, then ask this question word for word."
    ),
}


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
    safety_concern: bool = False,
    offer_waiting: bool = False,
    starting: bool = False,
    yes_framework: Framework | None = None,
    finished: Framework | None = None,
) -> str:
    """Format the metadata header for this turn.

    Every value is read from the composed turn snapshot, so the block describes what the
    database holds rather than what an in-memory copy was mutated to mid-request. `framework` and
    `history` are what the framework content and the caller's own history add - both optional,
    so a turn with neither still formats exactly as before.

    `framework` is the one already active. `starting` is a turn that opens it, and `yes_framework`
    the set a yes in this message would open; both ask the reply to report what they already said.
    `finished` is the framework of the thread's finished row, whose stages stay in view after it ends.

    `history` is the same window the caller already loads for the model's own conversation
    view - nothing new is fetched for it.
    """
    technique = ctx.technique
    # Named first because every stage_ask and offer_ask below is resolved from it, and named
    # `conversation_style` rather than `style` because `recent_styles` three lines down means
    # the response shape, which is a different thing entirely.
    lines: list[str] = _line("conversation_style", resolve_style(ctx))
    if safety_concern:
        # The deterministic screen heard something that may be a risk. The framework waits:
        # no stage question to relay, no offer to make, until the person is safe to go on.
        lines += _line("safety", "concern")
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
    understood = understanding.render(ctx.thread.understanding)
    if understood:
        lines += _line("understanding", understood)
    pending = ctx.thread.understanding.get(understanding.PENDING)
    if pending:
        lines += _line("feeling_change", f"{disarm(ctx.thread.understanding.get('feeling', ''))} -> {disarm(pending)}")
    step = understanding.next_step(ctx.thread.understanding)
    if step and live(ctx.technique) is None and not safety_concern:
        lines += _line("understanding_next", step)
    if offer_waiting:
        # Mani's last reply was an offer, and they typed rather than tapped.
        lines += _line("offer_waiting", "yes")
    question = None if safety_concern else _after_framework_question(history or [])
    if question:
        lines += _line("after_framework_question", question)

    # Told to the model as the reply shape enforces it: a check only where the shape has the field,
    # and an offer only on the answer to one (spec 0006).
    if not safety_concern:
        if check_open(ctx):
            lines += _line("check", "open")
        elif may_check(ctx):
            lines += _line("check", "may_check")
    if technique is not None:
        since_last = ctx.thread.message_count - technique.at_message_count
        lines += _line("since_last", since_last)
        lines += _line("this_thread", f"{technique.framework_id} ({technique.outcome})")
        if (
            technique.outcome is TechniqueOutcome.ACCEPTED
            and not technique.library_offered_since
        ):
            lines += _line("library_pending", "yes")
        if technique.phase:
            lines += _line("current_phase", technique.phase)
        elif finished is not None and technique.outcome is TechniqueOutcome.ACCEPTED:
            known = technique.stages_known.get(finished.id) or {}
            lines += _line("finished_framework", f"{finished.id}: {_stored(finished, known, finished.closing)}")

    if ctx.summary and ctx.summary.techniques_tried:
        tried = ", ".join(
            f"{t.name} ({'helpful' if t.helpful else 'not helpful'})"
            for t in ctx.summary.techniques_tried
        )
        lines += _line("history", tried)

    if ctx.recent_styles:
        styles = " → ".join(s.shape for s in ctx.recent_styles)
        lines += _line("recent_styles", styles)

    if running:
        lines += _running_lines(ctx, framework, offer_waiting=offer_waiting, starting=starting)
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
        lines.append(f"next: {walk.next_line(framework, known, technique.phase)}")
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
        parts.append(f'{stage} {status}: "{disarm(said)}"' if said else f"{stage} {status}")
    return " | ".join(parts)


def _start_lines(framework: Framework, style: str) -> list[str]:
    """On a turn that can start the set: what the reply does with the first stage, which the walk
    reaches, and that stage in full to judge it by."""
    first = walk.content_stages(framework)[0]
    return [f"next: the walk reaches {first}: {walk.reach_line(first)}",
            *_stage_lines("next_stage", framework, first, style)]

def _stage_lines(prefix: str, framework: Framework, phase: str, style: str) -> list[str]:
    """One stage's full guidance - current or next - resolved to one conversation style.

    Purpose, listening cues, readiness, the help when they are stuck and boundaries are clinical
    rather than tonal and do not vary; `ask` is the one leaf a style changes, so only the resolved
    style's variant is sent rather than all three.
    """
    stage = framework.stages.get(phase)
    if not stage:
        return [f"{prefix}: {phase}"]

    lines = [f"{prefix}: {phase}"]
    for field in ("purpose", "listen_for", "ready_when", "when_stuck"):
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
    ask = repairs.styled(stage.get("ask"), style)
    if ask:
        lines.append(f"{prefix}_ask: {ask}")
    return lines
