# ABOUTME: What one turn tells the model: the system prompt (mani.md, the framework guide, the person) and the facts
# ABOUTME: block sent after their message. Facts only; what code would refuse is said here, before the reply.

from __future__ import annotations

from mani.chat import record as rec
from mani.chat.greeting import style_label
from mani.chat.pause import ReturnCheck
from mani.chat.techniques import Registry, line_of, stages_of
from mani.db.threads import TurnContext
from mani.models.rows import TechniqueState
from mani.prompts import cache, composer

NO_OFFER = "You cannot offer a set of questions in this reply: never ask whether they would like to try one."
# What a tap on Try it says while the turn is held for safety: the set does not start, so its first line is not said.
HELD_START = ("They tapped Try it, but this reply is about their safety: the set does not start now and you never "
              "say its line.")


def framework_guide(registry: Registry) -> str:
    """Each active framework: when it fits, when never to offer it, and each stage's line, purpose and when it is
    answered."""
    parts = ["# The sets of questions"]
    for framework in (registry.get(fid) for fid in registry.ids):
        fits = " ".join(((framework.activation or {}).get("central_indication") or "").split())
        lines = [f"## {framework.name} (id: {framework.id})", framework.summary, f"It fits when: {fits}"]
        if never := (framework.activation or {}).get("contraindications"):
            lines += ["Never offer it when:", *(f"- {' '.join(line.split())}" for line in never)]
        lines.append("Stages, in order:")
        for stage_id in stages_of(framework):
            stage = framework.stages.get(stage_id) or {}
            lines.append(f"- `{stage_id}`. Line: \"{line_of(framework, stage_id)}\" Purpose: {stage.get('purpose', '')} "
                         f"Answered when: {stage.get('ready_when', '')}")
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


def system_prompt(config: cache.Config, ctx: TurnContext, *, summary_due: bool) -> str:
    """mani.md, the framework guide, what is known of the person, and the summary once messages left the window."""
    parts = [
        config.require("mani").content,
        framework_guide(config.registry),
        composer.user_context(ctx.profile),
        composer.user_memory(ctx.memory),
        composer.summary_layer(ctx.summary) if summary_due else None,
    ]
    return "\n\n".join(part for part in parts if part)


def facts(
    ctx: TurnContext, config: cache.Config, *, record: dict, style: str, running: TechniqueState | None,
    open_offer: TechniqueState | None, event: str | None, wants_title: bool, return_check: ReturnCheck | None,
    answering_return: str | None, end_check_asked: bool, holding: bool,
) -> str:
    """What this reply needs to know that the conversation does not show. `holding`: the turn is held for safety, so
    code moves, starts and offers nothing, and nothing here invites it."""
    safety = ctx.thread.safety
    lines = [f"Their style: {style_label(style)}."]
    if notes := record.get(rec.NOTES):
        lines.append(f"Your notes from your last turn: {notes}")
    if running is not None and (framework := config.registry.get(running.framework_id)):
        lines.append(_running_line(framework, running.phase, held=holding))
    if open_offer is not None and not holding and (framework := config.registry.get(open_offer.framework_id)):
        lines.append(f"Your last reply offered {framework.name} (id {framework.id}). A clear yes in their words starts "
                     "it: set stage to its first stage and open it.")
    if declined := rec.declined(record):
        lines.append(f"They declined in this conversation: {', '.join(declined)}. Never offer these again.")
    if finished := rec.finished(record):
        lines.append(f"They finished in this conversation: {', '.join(finished)}. Never offer a set again.")
    if safety != "clear":
        lines.append(f"A safety worry is open in this conversation ({safety}). Judge their message for it first.")
    if running is not None or open_offer is not None or finished or holding or safety != "clear":
        lines.append(NO_OFFER)
    lines += _pause_lines(ctx, return_check, answering_return)
    if end_check_asked:
        lines.append("You asked the safety question after the last stage. If their answer settles it, close the set "
                     "now in two or three warm sentences and set action to finish.")
    if event:
        lines.append(event)
    if wants_title:
        lines.append("Give this conversation a title.")
    return facts_block(lines)


def facts_block(lines: list[str]) -> str:
    """The facts as the model reads them, after their message."""
    return "Facts for this reply (never mention them):\n" + "\n".join(f"- {line}" for line in lines)


def _running_line(framework, phase: str | None, *, held: bool) -> str:
    stages = stages_of(framework)
    at = stages.index(phase) if phase in stages else 0
    if held:
        after = " This reply is about their safety: Stay on this stage and never say another stage's line."
    elif at + 1 < len(stages):
        after = (f" If its purpose is met, move to `{stages[at + 1]}` and say its line: "
                 f"\"{line_of(framework, stages[at + 1])}\". Never move further than that.")
    else:
        after = " It is the last stage: when it is answered, close and finish."
    return (f"{framework.name} is running. You are on stage `{stages[at]}` (its line, already said: "
            f"\"{line_of(framework, stages[at])}\"). Stay on it while it helps.{after}")


def _pause_lines(ctx: TurnContext, return_check: ReturnCheck | None, answering_return: str | None) -> list[str]:
    if return_check is not None:
        return [f"Their chat was paused earlier because of a safety worry ({return_check.reason or 'no reason kept'}). "
                "Before anything else, ask them plainly how things are with that now."]
    if answering_return is not None:
        reason = ctx.pause.reason if ctx.pause is not None else None
        return [f"Your last reply asked how they are after a pause for a safety worry ({reason or 'no reason kept'}). "
                "This message answers it: judge it for safety."]
    if ctx.recent_crisis:
        return ["Another conversation of theirs raised a safety worry recently. Go gently; never mention it."]
    return []
