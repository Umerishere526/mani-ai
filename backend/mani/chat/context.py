# ABOUTME: The hidden [ctx] block prefixed to the user's message for one turn only.
# ABOUTME: Built fresh from database state and never stored, so history cannot replay it.

from __future__ import annotations

import re

from mani.chat import repairs, understanding, walk
from mani.chat.techniques import OFFERING
from mani.config import get_settings
from mani.chat.greeting import AFTER_FRAMEWORK_QUESTIONS, CLARIFICATION_QUESTIONS, CHAT_MORE_LABEL
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

# How many messages must pass before a technique may be offered again.
# After "Keep chatting", three of Mani's replies before it may check again - the same
# framework or a different one, whichever fits now (muhammad, 2026-09-24).
COOLDOWN_AFTER_DECLINE = 6

# The first offer waits for the person's third message and is due by their fifth, the same in
# every style: the client's cadence puts about two to four exchanges between the issue and the
# offer, and no framework comes after the first message (Lolly, 2026-10-12, R1). Counted in the
# person's own messages.
FIRST_OFFER_OPENS = 3
FIRST_OFFER_DUE = 5
# The greeting, the style they tapped, and that style's opener.
OPENING_MESSAGES = 3
COOLDOWN_AFTER_COMPLETE = 45

# The default when neither the conversation nor the profile has chosen a style yet.
# `conversation_style` is set per-thread by PATCH /v1/threads/{id} and wins over
# profile.support_style, which holds the onboarding answer.
DEFAULT_STYLE = "supportive"

# How many of a reply's own leading words count as its "opener" for repetition purposes.
# Matches the threshold the eval harness already uses to call two openers the same one.
RECENT_OPENERS_WORDS = 2
# How many of Mani's own past replies to surface. Small on purpose: this is a nudge against
# an immediate repeat, not a transcript.
RECENT_OPENERS_WINDOW = 3


def _opener(text: str) -> str:
    """The first couple of words of a reply, lowercased - enough to name a repeated opening
    without exposing the reply itself in [ctx]."""
    return " ".join(text.split()[:RECENT_OPENERS_WORDS]).lower()

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
    included, are read from Mani's own replies, so they come in order and none twice. Once that
    reply has scrolled out of the history window the conversation has moved on, and none are
    offered.
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
    since = " ".join(m.content.lower() for m in mani[ended:])
    return next((q for q in AFTER_FRAMEWORK_QUESTIONS if q.lower().rstrip("?") not in since), None)


def cooldown_for(outcome: TechniqueOutcome) -> int:
    return (
        COOLDOWN_AFTER_COMPLETE
        if outcome is TechniqueOutcome.ACCEPTED
        else COOLDOWN_AFTER_DECLINE
    )


def _their_messages(ctx: TurnContext) -> int:
    """How many messages the person has sent. The reply to their Nth is written at 3 + 2(N - 1)."""
    return (ctx.thread.message_count - OPENING_MESSAGES) // 2 + 1


def clarification_used(history: list[Message] | None) -> bool:
    """Whether Mani has already asked the client's one-time clarifying question in this
    conversation. Read from history rather than a stored flag, so it holds even if a process
    restart drops anything else about how the turn was built."""
    return any(
        m.role is MessageRole.MANI
        and any(q in m.content.lower() for q in CLARIFICATION_QUESTIONS)
        for m in (history or [])
    )


def offer_window(ctx: TurnContext) -> str:
    """Whether an offer may be made in this reply: `not_yet`, `open`, or `due` once they have
    talked for several replies without one. The reply schema and repairs.apply enforce the floor;
    `due` never forces an offer that does not fit. After an earlier offer it reopens once the
    cooldown has passed and is never due."""
    technique = ctx.technique
    if technique is not None:
        since = ctx.thread.message_count - technique.at_message_count
        return "open" if since >= cooldown_for(technique.outcome) else "not_yet"
    if get_settings().pause_first_offer_window:
        return "open"
    theirs = _their_messages(ctx)
    if theirs >= FIRST_OFFER_DUE:
        return "due"
    return "open" if theirs >= FIRST_OFFER_OPENS else "not_yet"


def moment(
    technique: TechniqueState | None,
    outcome: TechniqueOutcome | None,
    retiring_framework_id: str | None,
    awaiting_place: bool,
    framework: Framework | None,
    concern: bool,
) -> Moment:
    """What is happening this turn, from the database and the safety screen alone; the first that
    matches wins. `technique` is the live row, offered or running, and `outcome` is its outcome,
    accepted when a Try it tap starts it this turn."""
    if concern:
        return Moment.CONCERN
    if retiring_framework_id is not None:
        return Moment.BODY
    if technique is None:
        return Moment.CHATTING
    if outcome is TechniqueOutcome.ACCEPTED:
        phase = technique.phase
        at_the_body = phase == "somatic_checkin" or (phase == "somatic_practice" and awaiting_place)
        if at_the_body or (framework is not None and phase == framework.closing):
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


# How a start turn uses what they said before the yes. Its text is code's, so only the fields count.
_SEED = (
    "The first stage is sent for you, so your text is not sent. In stage_updates report every stage "
    "below that what they have said, here or in the Conversation Context, already answers."
)

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
            "nothing has been offered yet. Your questions come from listening, the way a "
            "specialist listens. Never tell them what they feel. One question, in plain everyday "
            "words. No menu of choices, no advice and no suggestion hidden in a question. What "
            "they say about how it is for them shows which set fits."
        ),
        "framework": "the questions are running, so follow the stage.",
        "talking": (
            "an offer was declined or the questions finished, so talk with them, following "
            "what they say."
        ),
    },
    "clarification_available": {
        "yes": (
            "if several distinct things have come up and you cannot tell which matters most, "
            "you may ask one of the client's two lines, word for word, \"Do I have this right?\" "
            "or \"What would you like us to focus on today?\" Then follow their answer. Once "
            "asked, never again."
        ),
    },
    "offer_waiting": {
        "yes": (
            "your last reply offered and they typed instead of tapping. On a yes, begin. "
            "Otherwise follow them."
        ),
    },
    "offer_window": {
        "not_yet": "offer nothing in this reply.",
        "due": (
            "you have talked for several replies without offering. If a set fits, offer it now. If "
            "none fits yet, offer nothing and check your understanding in one short question."
        ),
    },
    "understanding": (
        "what they have told you so far, kept for you. In understanding_update report only what their "
        "message names or changes."
    ),
    "since_last": "how many messages have passed since the last offer.",
    "this_thread": (
        "what was last offered in this conversation and how it went. One they declined may come "
        "back once the cooldown has passed, if it still fits. One they just finished may not. "
        "If they ask for one they declined, that is a yes at any time, so begin it."
    ),
    "history": "what was tried earlier in this conversation, and whether it helped.",
    "library_pending": {"yes": "offer the Library before anything new."},
    "current_phase": "the stage the questions are on, as last recorded.",
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
    "recent_openers": (
        "the first words of your last few replies. Do not open your new reply the same way."
    ),
    "framework_starting": {"yes": f"they just said yes. {_SEED}"},
    "if_they_say_yes": f"only if their message says yes to this set: {_SEED}",
    "active_framework": (
        "the set of questions running, with its stages in order. Then the stage you are on, with "
        "its purpose, what to listen for, when it is done, its boundaries and what to do if "
        "unclear. Its ask is a model question already in this style."
    ),
    "stages_known": (
        "what they have said for each stage, kept for you. Never ask for what a stage already "
        "holds. In stage_updates report only what is new or changed in their message."
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
) -> str:
    """Format the metadata header for this turn.

    Every value is read from the composed turn snapshot, so the block describes what the
    database holds rather than what an in-memory copy was mutated to mid-request. `framework` and
    `history` are what the framework content and the caller's own history add - both optional,
    so a turn with neither still formats exactly as before.

    `framework` is the one already active. `starting` is a turn that opens it, and `yes_framework`
    the set a yes in this message would open; both ask the reply to report what they already said.

    `history` is the same window the caller already loads for the model's own conversation
    view - nothing new is fetched for it. Only Mani's own messages in it become recent_openers;
    the person's messages are read here but never surfaced back to the model as an "opener".
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
    if not running and not clarification_used(history):
        lines += _line("clarification_available", "yes")
    if offer_waiting:
        # Mani's last reply was an offer, and they typed rather than tapped.
        lines += _line("offer_waiting", "yes")
    question = None if safety_concern else _after_framework_question(history or [])
    if question:
        lines += _line("after_framework_question", question)

    # Told to the model as it is enforced, so it is never told it may offer what code then drops.
    # An open window is not sent: read every turn, it was taken as "offer now" (2026-10-12).
    window = "not_yet" if safety_concern else offer_window(ctx)
    if window != "open":
        lines += _line("offer_window", window)
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

    if ctx.summary and ctx.summary.techniques_tried:
        tried = ", ".join(
            f"{t.name} ({'helpful' if t.helpful else 'not helpful'})"
            for t in ctx.summary.techniques_tried
        )
        lines += _line("history", tried)

    if ctx.recent_styles:
        styles = " → ".join(s.shape for s in ctx.recent_styles)
        lines += _line("recent_styles", styles)

    # A separate signal from recent_styles: that is the abstract shape, this is the
    # literal words a reply opened with - two replies can vary in shape while still starting
    # the same way, which is what "recent_styles" alone cannot catch.
    mani_replies = [m.content for m in (history or []) if m.role is MessageRole.MANI]
    openers = [
        _opener(text) for text in mani_replies[-RECENT_OPENERS_WINDOW:] if text.strip()
    ]
    if openers:
        quoted = ", ".join(f'"{o}"' for o in openers)
        lines += _line("recent_openers", quoted)

    if running:
        lines += _running_lines(ctx, framework, offer_waiting=offer_waiting, starting=starting)
    if yes_framework is not None and not safety_concern:
        lines += _line("if_they_say_yes", yes_framework.id)
        lines += _seed_lines(yes_framework)

    return "[ctx]\n" + "\n".join(lines) + "\n[/ctx]\n\n"


def _running_lines(
    ctx: TurnContext, framework: Framework, *, offer_waiting: bool, starting: bool
) -> list[str]:
    """The running set: on the turn it starts, what to report from before the yes; at the offer, the
    offering stage; on a stage, that stage, what is stored for every stage and what this reply is
    for. The next stage goes in full only when the reply needs it: partly answered, or the body route."""
    technique, style = ctx.technique, resolve_style(ctx)
    lines = _line("active_framework", framework.id)
    lines.append(f"framework_stages: {', '.join(framework.phases)}")
    if starting:
        return lines + _line("framework_starting", "yes") + _seed_lines(framework)
    stage = _stage_lines("stage", framework, technique.phase, style)
    if offer_waiting:
        # The offering stage's question is the offer they have just typed past.
        stage = [line for line in stage if not line.startswith("stage_ask:")]
    lines.extend(stage)
    if technique.phase == OFFERING:
        return lines
    known = technique.stages_known.get(framework.id) or {}
    lines += _line("stages_known", _stored(framework, known))
    if technique.phase in walk.content_stages(framework):
        lines.append(f"next: {walk.next_line(framework, known, technique.phase)}")
        lines.append(f"two_tries: {_TWO_TRIES}")
    index = framework.phase_index(technique.phase)
    following = framework.phases[index + 1] if 0 <= index < len(framework.phases) - 1 else None
    if following and (following in ENDING_STAGES or (known.get(following) or {}).get("status") == "partial"):
        lines.extend(_stage_lines("next_stage", framework, following, style))
    return lines


def _stored(framework: Framework, known: dict[str, dict]) -> str:
    """Every content stage with its stored status, and their words when there are some."""
    parts = []
    for stage in walk.content_stages(framework):
        entry = known.get(stage) or {}
        status = entry.get("status") or "missing"
        said = entry.get("said")
        parts.append(f'{stage} {status}: "{disarm(said)}"' if said else f"{stage} {status}")
    return " | ".join(parts)


def _seed_lines(framework: Framework) -> list[str]:
    """The content stages, each with what to listen for, so a yes can report what is already answered."""
    return [
        f"stage_to_seed: {stage}: {(framework.stages.get(stage) or {}).get('listen_for', '')}".rstrip(": ")
        for stage in walk.content_stages(framework)
    ]


# A stage is a step, not an exam: it never needs complete or certain answers, and a person asked
# the same thing a third time feels interrogated (live, 2026-10-08: five times running).
_TWO_TRIES = (
    "If you have already asked for this stage's thing twice, take what they gave you and move to "
    "the next stage, unless stage_ready_when says to stay."
)


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
    if stage.get("boundaries"):
        lines.append(f"{prefix}_boundaries: " + "; ".join(stage["boundaries"]))
    if stage.get("if_unclear"):
        # A body route branch is shown by its id, which the reply names in `body`: code sends its text.
        rendered = " | ".join(
            f"{e['id']}: {e['when']}" if e.get("id") else f"if {e['when']}: {repairs.reply_for(e, style)}"
            for e in stage["if_unclear"]
        )
        lines.append(f"{prefix}_if_unclear: {rendered}")
    ask = (stage.get("ask") or {}).get(style)
    if ask:
        lines.append(f"{prefix}_ask: {ask}")
    return lines
