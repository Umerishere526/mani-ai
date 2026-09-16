# ABOUTME: The hidden [ctx] block prefixed to the user's message for one turn only.
# ABOUTME: Built fresh from database state and never stored, so history cannot replay it.

from __future__ import annotations

import re

from mani.db.threads import TurnContext
from mani.models.rows import TechniqueOutcome

# How many messages must pass before a technique may be offered again.
COOLDOWN_AFTER_DECLINE = 20
COOLDOWN_AFTER_COMPLETE = 45

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


def build(ctx: TurnContext) -> str:
    """Format the metadata header for this turn.

    Every value is read from the composed turn snapshot, so the block describes what the
    database holds rather than what an in-memory copy was mutated to mid-request.
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

    return "[ctx]\n" + "\n".join(lines) + "\n[/ctx]\n\n"
