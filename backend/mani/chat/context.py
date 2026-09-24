# ABOUTME: The hidden [ctx] block prefixed to the user's message for one turn only.
# ABOUTME: Built fresh from database state and never stored, so history cannot replay it.

from __future__ import annotations

import re

from mani.chat.greeting import AFTER_FRAMEWORK_QUESTIONS, CHAT_MORE_LABEL
from mani.chat.router import Signal, is_confident
from mani.db.threads import TurnContext
from mani.models.rows import Framework, Message, MessageRole, TechniqueOutcome

# How many messages must pass before a technique may be offered again.
# After "Keep chatting", three of Mani's replies before it may check again - the same
# framework or a different one, whichever fits now (muhammad, 2026-09-24).
COOLDOWN_AFTER_DECLINE = 6
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


def cooldown_passed(ctx: TurnContext) -> bool:
    """Whether a framework may be offered yet: [ctx] reports it, repairs.apply enforces it."""
    technique = ctx.technique
    if technique is None:
        return True
    return ctx.thread.message_count - technique.at_message_count >= cooldown_for(
        technique.outcome
    )


def resolve_style(ctx: TurnContext) -> str:
    """Which of the framework's three `ask` variants to surface this turn.

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
    candidate: Framework | None = None,
    history: list[Message] | None = None,
    safety_concern: bool = False,
    offer_waiting: bool = False,
    framework_starting: bool = False,
) -> str:
    """Format the metadata header for this turn.

    Every value is read from the composed turn snapshot, so the block describes what the
    database holds rather than what an in-memory copy was mutated to mid-request. `shortlist`,
    `framework`, `candidate` and `recent_mani_replies` are what the router, the framework
    content and the caller's own history add - all optional, so a turn with none of them still
    formats exactly as before.

    `framework` is the one already active; its current and next stage go in full. `candidate`
    is the router's top pick when it is confident enough to be worth more than a bare id and
    score - its offer line goes in, so the offer draws on authored language rather than being
    improvised from the Framework Index's one-liner alone. Never both at once: a framework is
    either running or being considered, not both.

    `history` is the same window the caller already loads for the model's own conversation
    view - nothing new is fetched for it. Only Mani's own messages in it become recent_openers;
    the person's messages are read here but never surfaced back to the model as an "opener".
    """
    technique = ctx.technique
    # Named first because every stage_ask and offer_ask below is resolved from it, and named
    # `conversation_style` rather than `style` because `recent_styles` three lines down means
    # the response shape and voice, which is a different thing entirely.
    lines: list[str] = [f"conversation_style: {resolve_style(ctx)}"]
    if safety_concern:
        # The deterministic screen heard something that may be a risk. The framework waits:
        # no stage question to relay, no offer to make, until the person is safe to go on.
        lines.append("safety: concern")
    if ctx.recent_crisis:
        lines.append("recent_crisis: yes")

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
    lines.append(f"conversation_phase: {phase}")
    if not running:
        # What the question is about while no stage decides it (muhammad, 2026-09-24): said
        # here, next to the message, because the style rule in the long prompt alone did not hold.
        focus = "next step" if resolve_style(ctx) == "direct" else "feelings"
        lines.append(f"question_focus: {focus}")
    if offer_waiting:
        # Mani's last reply was an offer, and they typed rather than tapped.
        lines.append("offer_waiting: yes")
    question = None if safety_concern else _after_framework_question(history or [])
    if question:
        lines.append(f"after_framework_question: {question}")

    if technique is None:
        lines.append("cooldown_passed: yes")
    else:
        since_last = ctx.thread.message_count - technique.at_message_count
        lines.append(f"cooldown_passed: {'yes' if cooldown_passed(ctx) else 'no'}")
        lines.append(f"since_last: {since_last}")
        lines.append(f"this_thread: {technique.framework_id} ({technique.outcome})")
        if (
            technique.outcome is TechniqueOutcome.ACCEPTED
            and not technique.library_offered_since
        ):
            lines.append("library_pending: yes")
        if technique.phase:
            lines.append(f"current_phase: {technique.phase}")

    if ctx.summary and ctx.summary.techniques_tried:
        tried = ", ".join(
            f"{t.name} ({'helpful' if t.helpful else 'not helpful'})"
            for t in ctx.summary.techniques_tried
        )
        lines.append(f"history: {tried}")

    if ctx.recent_styles:
        styles = " → ".join(
            f"{s.shape} ({s.voice})" if s.voice else s.shape for s in ctx.recent_styles
        )
        lines.append(f"recent_styles: {styles}")

    # A separate signal from recent_styles: that is the abstract shape/voice, this is the
    # literal words a reply opened with - two replies can vary in shape while still starting
    # the same way, which is what "recent_styles" alone cannot catch.
    mani_replies = [m.content for m in (history or []) if m.role is MessageRole.MANI]
    openers = [
        _opener(text) for text in mani_replies[-RECENT_OPENERS_WINDOW:] if text.strip()
    ]
    if openers:
        quoted = ", ".join(f'"{o}"' for o in openers)
        lines.append(f"recent_openers: {quoted}")

    if shortlist and not safety_concern:
        ranked = ", ".join(f"{s.framework_id} ({s.score:.2f})" for s in shortlist)
        lines.append(f"framework_shortlist: {ranked}")
        if candidate is not None and is_confident(shortlist):
            lines.extend(_stage_lines("offer", candidate, "offering", resolve_style(ctx)))
            if candidate.summary:
                # The client's description, which the offer fits to what they said.
                lines.append(f"offer_helps: {' '.join(candidate.summary.split())}")

    if running:
        style = resolve_style(ctx)
        if framework_starting:
            # They have just said yes. What they told Mani before this counts; a stage they
            # have already answered is checked back, not asked again.
            lines.append("framework_starting: yes")
        lines.append(f"active_framework: {framework.id}")
        lines.append(f"framework_stages: {', '.join(framework.phases)}")
        stage = _stage_lines("stage", framework, technique.phase, style)
        if offer_waiting:
            # The offering stage's question is the offer they have just typed past.
            stage = [line for line in stage if not line.startswith("stage_ask:")]
        lines.extend(stage)
        index = framework.phase_index(technique.phase)
        if 0 <= index < len(framework.phases) - 1:
            lines.extend(
                _stage_lines("next_stage", framework, framework.phases[index + 1], style)
            )

    return "[ctx]\n" + "\n".join(lines) + "\n[/ctx]\n\n"


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
        rendered = " | ".join(f"if {e['when']}: {e['reply']}" for e in stage["if_unclear"])
        lines.append(f"{prefix}_if_unclear: {rendered}")
    ask = (stage.get("ask") or {}).get(style)
    if ask:
        lines.append(f"{prefix}_ask: {ask}")
    return lines
