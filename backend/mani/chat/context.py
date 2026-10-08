# ABOUTME: The hidden [ctx] block prefixed to the user's message for one turn only.
# ABOUTME: Built fresh from database state and never stored, so history cannot replay it.

from __future__ import annotations

import re

from mani.chat import ending
from mani.chat.greeting import AFTER_FRAMEWORK_QUESTIONS, CLARIFICATION_QUESTIONS, CHAT_MORE_LABEL
from mani.chat.router import Signal
from mani.chat.safety import normalize
from mani.chat.techniques import OFFERING
from mani.db.threads import TurnContext
from mani.models.rows import Framework, Message, MessageRole, TechniqueOutcome
from mani.prompts.composer import tried_line

# An offer may come from the person's second message, in any style: it was four rounds for
# Supportive and Reflective until Mani's own judgement was made the signal (muhammad,
# 2026-10-01). Counted in the person's own messages.
CLEAR_OFFER_AFTER = 2
# After "Keep chatting" an offer may come back after two more exchanges.
CLEAR_COOLDOWN_AFTER_DECLINE = 4
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


# Every key a [ctx] line may carry. Each one's meaning is said once, in response_format.md's `ctx`
# section, and a test ties the two together in both directions, so the code sends only keys and
# values and never a sentence of instruction.
CTX_KEYS = frozenset({
    "conversation_style", "safety", "recent_crisis", "conversation_phase",
    "clarification_available", "question_focus", "their_last", "offer_waiting",
    "after_framework_question", "cooldown_passed", "since_last", "this_thread",
    "library_pending", "current_phase", "history", "recent_styles", "recent_openers",
    "ruled_out", "framework_shortlist", "framework_starting", "active_framework",
    "framework_stages",
    "stage", "stage_purpose", "stage_listen_for", "stage_ready_when", "stage_boundaries",
    "stage_if_unclear", "stage_ask",
    "next_stage", "next_stage_purpose", "next_stage_listen_for", "next_stage_ready_when",
    "next_stage_boundaries", "next_stage_if_unclear", "next_stage_ask",
})


def _line(key: str, value: object) -> str:
    """One [ctx] line. A key the prompt does not explain is refused, so none can reach the model."""
    if key not in CTX_KEYS:
        raise ValueError(f"[ctx] key {key!r} is not in CTX_KEYS")
    return f"{key}: {value}"


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


def clear_cooldown_for(outcome: TechniqueOutcome) -> int:
    return (
        COOLDOWN_AFTER_COMPLETE
        if outcome is TechniqueOutcome.ACCEPTED
        else CLEAR_COOLDOWN_AFTER_DECLINE
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


def cooldown_passed(ctx: TurnContext, *, urgent: bool = False) -> bool:
    """Whether an offer may be made yet: [ctx] tells the model, which keeps to it."""
    technique = ctx.technique
    if technique is None:
        # An action about to be taken is the one case not worth waiting the rounds out.
        return urgent or _their_messages(ctx) >= CLEAR_OFFER_AFTER
    return ctx.thread.message_count - technique.at_message_count >= clear_cooldown_for(
        technique.outcome
    )


# What a person says when they have given almost nothing, and when they are telling Mani it
# missed something they already said. Whole messages / phrases, after normalising, so a vague
# word inside a real sentence ("yeah, my manager shouted") is not mistaken for either.
_VAGUE_REPLIES = frozenset({
    "yeah", "yea", "yup", "yep", "ok", "okay", "maybe", "hmm", "hm", "sure", "i guess",
    "idk", "dunno", "i do not know", "do not know", "i am not sure", "not sure", "no idea",
    "kind of", "sort of", "kinda", "i suppose",
})
_HEARD_PHRASES = (
    "just need to get it out", "just want to get it out", "just need to vent", "just want to vent",
    "just want to talk", "just need to talk", "just listen", "dont want advice", "do not want advice",
    "not looking for advice", "dont ask me", "do not ask me", "no questions",
    "dont give me a technique", "do not give me a technique", "dont want a technique",
    "do not want a technique", "dont want to do an exercise", "do not want to do an exercise",
)
_CORRECTION_PHRASES = (
    "just told you", "i told you", "already told you", "i already told", "i just said",
    "already said", "i said that", "like i said", "as i said", "you asked that",
    "you already asked", "i just answered", "i answered",
)


def classify_reply(text: str) -> str | None:
    """`vague` for a reply that says almost nothing, `correction` for one that says Mani missed
    what they had already said, `heard` for one that asks only to be listened to, otherwise None. A deterministic read, so the model is told rather
    than left to notice."""
    normalized = normalize(text)
    if any(phrase in normalized for phrase in _HEARD_PHRASES):
        return "heard"
    if any(phrase in normalized for phrase in _CORRECTION_PHRASES):
        return "correction"
    if normalized in _VAGUE_REPLIES:
        return "vague"
    return None


def resolve_style(ctx: TurnContext) -> str:
    """The conversation style this turn: named in [ctx], and the variant of a somatic stage's
    `ask` that is sent.

    The conversation's own choice wins over the profile's, which is the point of having
    both: onboarding sets a default, and a thread may differ from it without changing it.
    """
    if ctx.thread.conversation_style:
        return ctx.thread.conversation_style.value
    if ctx.profile and ctx.profile.support_style:
        return ctx.profile.support_style.value
    return DEFAULT_STYLE


def build(
    ctx: TurnContext,
    *,
    shortlist: list[Signal] | None = None,
    framework: Framework | None = None,
    history: list[Message] | None = None,
    safety_concern: bool = False,
    offer_waiting: bool = False,
    framework_starting: bool = False,
    urgent: bool = False,
    their_last: str | None = None,
    ruled_out: list[str] | None = None,
) -> str:
    """Format the metadata header for this turn.

    Every value is read from the composed turn snapshot, so the block describes what the
    database holds rather than what an in-memory copy was mutated to mid-request. `shortlist`,
    `framework` and `history` are what the router, the framework content and the caller's own
    history add - all optional, so a turn with none of them still formats exactly as before.

    `framework` is the one already active; its current and next stage go in by id, since the
    model reads what each stage asks from the framework's Stages line in the index. Only the
    somatic stages carry a block, and theirs go in full. `shortlist` is every framework the
    router found signs of, ranked; its ids are the only sets the model may offer from.

    `history` is the same window the caller already loads for the model's own conversation
    view - nothing new is fetched for it. Only Mani's own messages in it become recent_openers;
    the person's messages are read here but never surfaced back to the model as an "opener".

    `ruled_out` is the frameworks what they have said rules out. It is told to the model while no
    framework runs, and the caller has already taken them off `shortlist`.
    """
    technique = ctx.technique
    # Named first because the model writes every stage question in it and a somatic stage's ask
    # is resolved from it, and named `conversation_style` rather than `style` because `recent_styles` three lines down means
    # the response shape, which is a different thing entirely.
    lines: list[str] = [_line("conversation_style", resolve_style(ctx))]
    if safety_concern:
        # The deterministic screen heard something that may be a risk. The framework waits:
        # no stage question to relay, no offer to make, until the person is safe to go on.
        lines.append(_line("safety", "concern"))
    if ctx.recent_crisis:
        lines.append(_line("recent_crisis", "yes"))

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
    lines.append(_line("conversation_phase", phase))
    if not running and not clarification_used(history):
        lines.append(_line("clarification_available", "yes"))
    if not running:
        # What the question is about while no stage decides it (muhammad, 2026-09-24): said
        # here, next to the message, because the style rule in the long prompt alone did not hold.
        focus = "feeling_then_way_through" if resolve_style(ctx) == "direct" else "feelings"
        lines.append(_line("question_focus", focus))
    if their_last and not offer_waiting and not safety_concern and (
        not running or their_last == "correction"
    ):
        # A vague reply is not flagged while the questions run: each stage already says what to
        # do with one. A correction is, because no stage says to take what they already told you.
        lines.append(_line("their_last", their_last))
    if offer_waiting:
        # Mani's last reply was an offer, and they typed rather than tapped.
        lines.append(_line("offer_waiting", "yes"))
    question = None if safety_concern else _after_framework_question(history or [])
    if question:
        lines.append(_line("after_framework_question", question))

    # The offer's timing is told to the model, which keeps to it.
    lines.append(_line("cooldown_passed", "yes" if cooldown_passed(ctx, urgent=urgent) else "no"))
    if technique is not None:
        since_last = ctx.thread.message_count - technique.at_message_count
        lines.append(_line("since_last", since_last))
        lines.append(_line("this_thread", f"{technique.framework_id} ({technique.outcome})"))
        if (
            technique.outcome is TechniqueOutcome.ACCEPTED
            and not technique.library_offered_since
        ):
            lines.append(_line("library_pending", "yes"))
        if technique.phase:
            lines.append(_line("current_phase", technique.phase))

    if ctx.summary and ctx.summary.techniques_tried:
        lines.append(_line("history", tried_line(ctx.summary.techniques_tried)))

    if ctx.recent_styles:
        styles = " → ".join(s.shape for s in ctx.recent_styles)
        lines.append(_line("recent_styles", styles))

    # A separate signal from recent_styles: that is the abstract shape, this is the
    # literal words a reply opened with - two replies can vary in shape while still starting
    # the same way, which is what "recent_styles" alone cannot catch.
    mani_replies = [m.content for m in (history or []) if m.role is MessageRole.MANI]
    openers = [
        _opener(text) for text in mani_replies[-RECENT_OPENERS_WINDOW:] if text.strip()
    ]
    if openers:
        quoted = ", ".join(f'"{o}"' for o in openers)
        lines.append(_line("recent_openers", quoted))

    if ruled_out and not running and not safety_concern:
        lines.append(_line("ruled_out", ", ".join(ruled_out)))
    if shortlist and not safety_concern:
        # Ids only, in ranked order: the model sees which sets the router found signs of and
        # which most, never a strength to read as a verdict.
        lines.append(_line("framework_shortlist", ", ".join(s.framework_id for s in shortlist)))

    if running:
        style = resolve_style(ctx)
        if framework_starting:
            # They have just said yes. What they told Mani before this counts toward the first
            # stage; response_format.md says how to use it.
            lines.append(_line("framework_starting", "yes"))
        lines.append(_line("active_framework", framework.id))
        lines.append(_line("framework_stages", ", ".join(framework.phases)))
        phase = technique.phase
        index = framework.phase_index(phase)
        if framework_starting and phase == OFFERING and index + 1 < len(framework.phases):
            index += 1
            phase = framework.phases[index]
        lines.extend(_stage_lines("stage", framework, phase, style))
        # An offer still open has no next stage: offer_waiting says how to take what they typed.
        if phase != OFFERING and 0 <= index < len(framework.phases) - 1:
            lines.extend(_stage_lines("next_stage", framework, framework.phases[index + 1], style))

    return "[ctx]\n" + "\n".join(lines) + "\n[/ctx]\n\n"


def _stage_lines(prefix: str, framework: Framework, phase: str, style: str) -> list[str]:
    """One stage - current or next - as its id, and in full when it carries a block.

    Only the somatic stages do. Purpose, listening cues, readiness and boundaries are clinical
    rather than tonal and do not vary; `ask` is the one leaf a style changes, so only the
    resolved style's variant is sent rather than all three.
    """
    lines = [_line(prefix, phase)]
    stage = framework.stages.get(phase)
    if not stage:
        return lines

    for field in ("purpose", "listen_for", "ready_when"):
        if stage.get(field):
            lines.append(_line(f"{prefix}_{field}", stage[field]))
    if stage.get("boundaries"):
        lines.append(_line(f"{prefix}_boundaries", "; ".join(stage["boundaries"])))
    if stage.get("if_unclear"):
        rendered = " | ".join(f"if {e['when']}: {ending.reply_for(e, style)}" for e in stage["if_unclear"])
        lines.append(_line(f"{prefix}_if_unclear", rendered))
    ask = (stage.get("ask") or {}).get(style)
    if ask:
        lines.append(_line(f"{prefix}_ask", ask))
    return lines
