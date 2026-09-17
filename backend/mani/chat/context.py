# ABOUTME: The hidden [ctx] block prefixed to the user's message for one turn only.
# ABOUTME: Built fresh from database state and never stored, so history cannot replay it.

from __future__ import annotations

import re

from mani.chat.router import Signal, is_confident
from mani.db.threads import TurnContext
from mani.models.rows import Framework, TechniqueOutcome

# How many messages must pass before a technique may be offered again.
COOLDOWN_AFTER_DECLINE = 20
COOLDOWN_AFTER_COMPLETE = 45

# The default when neither the conversation nor the profile has chosen a style yet.
# `conversation_style` (per-thread) is not wired to any endpoint yet; profile.support_style
# is the existing onboarding field, so it is the source until the style capsule feature lands.
DEFAULT_STYLE = "supportive"

_CTX_BLOCK = re.compile(r"^\[ctx\].*?\[/ctx\]\s*", re.DOTALL)


def strip(content: str) -> str:
    """Remove a context block from stored text.

    Kept for messages written by the previous system, which prefixed the block and then
    saved it - so a long thread replayed up to ten stale and mutually contradictory
    blocks to the model on every turn. Nothing written here contains one.
    """
    return _CTX_BLOCK.sub("", content, count=1)


def cooldown_for(outcome: TechniqueOutcome) -> int:
    return (
        COOLDOWN_AFTER_COMPLETE
        if outcome is TechniqueOutcome.ACCEPTED
        else COOLDOWN_AFTER_DECLINE
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
) -> str:
    """Format the metadata header for this turn.

    Every value is read from the composed turn snapshot, so the block describes what the
    database holds rather than what an in-memory copy was mutated to mid-request. `shortlist`,
    `framework` and `candidate` are what the router and the framework content add - all
    optional, so a turn with none of them still formats exactly as before.

    `framework` is the one already active; its current and next stage go in full. `candidate`
    is the router's top pick when it is confident enough to be worth more than a bare id and
    score - its offer line goes in, so the offer draws on authored language rather than being
    improvised from the Framework Index's one-liner alone. Never both at once: a framework is
    either running or being considered, not both.
    """
    technique = ctx.technique
    lines: list[str] = []

    if technique is None:
        lines.append("cooldown_passed: yes")
    else:
        since_last = ctx.thread.message_count - technique.at_message_count
        passed = since_last >= cooldown_for(technique.outcome)
        lines.append(f"cooldown_passed: {'yes' if passed else 'no'}")
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
        history = ", ".join(
            f"{t.name} ({'helpful' if t.helpful else 'not helpful'})"
            for t in ctx.summary.techniques_tried
        )
        lines.append(f"history: {history}")

    if ctx.recent_styles:
        styles = " → ".join(
            f"{s.shape} ({s.voice})" if s.voice else s.shape for s in ctx.recent_styles
        )
        lines.append(f"recent_styles: {styles}")

    if shortlist:
        ranked = ", ".join(f"{s.framework_id} ({s.score:.2f})" for s in shortlist)
        lines.append(f"framework_shortlist: {ranked}")
        if candidate is not None and is_confident(shortlist):
            lines.extend(_stage_lines("offer", candidate, "offering", resolve_style(ctx)))

    if framework is not None and technique is not None and technique.phase:
        style = resolve_style(ctx)
        lines.append(f"active_framework: {framework.id}")
        lines.append(f"framework_stages: {', '.join(framework.phases)}")
        lines.extend(_stage_lines("stage", framework, technique.phase, style))
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
