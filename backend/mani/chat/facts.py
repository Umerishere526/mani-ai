# ABOUTME: What one turn tells the model: the system prompt (mani.md, the framework guide, the person) and the facts
# ABOUTME: block sent after their message. Facts only; what code would refuse is said here, before the reply.

from __future__ import annotations

from mani.chat import record as rec
from mani.chat.decide import OFFER_FROM_MESSAGE
from mani.chat.greeting import style_label
from mani.chat.pause import ReturnCheck
from mani.chat.safety import State
from mani.chat.techniques import FEELINGS, FIRST_STAGE_OPENING, STEPS, Registry, line_of, stages_of
from mani.db.threads import TurnContext
from mani.models.rows import TechniqueState
from mani.prompts import cache, composer

# How many of the latest replies the facts show what they gave and how they opened.
SAID_SHOWN = 6
OPENERS_SHOWN = 4
NO_OFFER = "You cannot offer a set of questions in this reply: never ask whether they would like to try one."
# What a tap on Start says while the turn is held for safety: the set does not start, so its first line is not said.
HELD_START = ("They tapped to start the set, but this reply is about their safety: it does not start now and you never "
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
        composer.summary_layer(ctx.summary) if summary_due else None,
    ]
    return "\n\n".join(part for part in parts if part)


def facts(
    ctx: TurnContext, config: cache.Config, *, record: dict, style: str, running: TechniqueState | None,
    open_offer: TechniqueState | None, event: str | None, wants_title: bool, return_check: ReturnCheck | None,
    answering_return: str | None, end_check_asked: bool, holding: bool, person_messages: int, state: State,
) -> str:
    """What this reply needs to know that the conversation does not show. `holding`: the turn is held for safety, so
    code moves, starts and offers nothing, and nothing here invites it."""
    safety = state.value
    lines = [f"Their style: {style_label(style)}."]
    if notes := record.get(rec.NOTES):
        lines.append(f"Your notes from your last turn: {notes}")
    lines += understanding_lines(record)
    if running is not None and (framework := config.registry.get(running.framework_id)):
        lines.append(_running_line(framework, running.phase, held=holding))
    lines += ledger_lines(rec.replies(record), open_chat=running is None and not holding)
    if open_offer is not None and not holding and (framework := config.registry.get(open_offer.framework_id)):
        lines.append(_offer_line(framework, open_offer.phase))
    if declined := rec.declined(record):
        lines.append(f"They declined in this conversation: {', '.join(declined)}. Never offer these again.")
    if finished := rec.finished(record):
        lines.append(f"They finished in this conversation: {', '.join(finished)}. Never offer a set again.")
    if safety != "clear":
        lines.append(f"A safety worry is open in this conversation ({safety}). Judge their message for it first.")
    if not offerable(config, record=record, running=running, open_offer=open_offer, holding=holding,
                     person_messages=person_messages, state=state):
        lines.append(NO_OFFER)
    lines += _pause_lines(ctx, return_check, answering_return)
    if end_check_asked:
        lines.append("You asked the safety question after the last stage. If their answer settles it, acknowledge it, "
                     "ask how they feel now about what they worked through, and set action to finish.")
    if event:
        lines.append(event)
    if wants_title:
        lines.append("Give this conversation a title.")
    return facts_block(lines)


def offerable(
    config: cache.Config, *, record: dict, running: TechniqueState | None, open_offer: TechniqueState | None,
    holding: bool, person_messages: int, state: State,
) -> tuple[str, ...]:
    """The sets this reply may offer, as code knows before the call: none while a set runs or is offered, after one
    was finished, while a safety worry is open or the turn is held, or before their 3rd message; else every active set
    they have not declined."""
    if (running is not None or open_offer is not None or rec.finished(record) or holding or state is not State.CLEAR
            or person_messages < OFFER_FROM_MESSAGE):
        return ()
    declined = rec.declined(record)
    return tuple(framework_id for framework_id in config.registry.ids if framework_id not in declined)


def understanding_lines(record: dict) -> list[str]:
    """The people and events kept from your last turn, as they said them, for this reply to carry forward."""
    lines = []
    if people := rec.people(record):
        listed = "; ".join(f"{p['called']} ({p['relation'] or 'unsaid'}): {p['told'] or 'nothing yet'}" for p in people)
        lines.append(f"The people they spoke of, as they put them: {listed}. Each detail belongs to its person only.")
    if events := rec.events(record):
        listed = "; ".join(f"[{e['when']}] {e['what']}" for e in events)
        lines.append(f"What they told you happened or is coming, as they said it: {listed}. Never speak of an upcoming "
                     "event as past, and never state as fact what they have not said.")
    return lines


def ledger_lines(kept: list[dict], *, open_chat: bool) -> list[str]:
    """What Mani already asked, and what each was for; what its recent replies gave and how they opened; and in the open
    chat, a run of replies that all asked."""
    lines = []
    if asked := [entry for entry in kept if entry.get("q")]:
        listed = "; ".join(f"[{entry.get('intent') or 'unsaid'}] \"{entry['q']}\""
                           + (f" (already answered: \"{entry['answer']}\")" if entry.get("answer") else "")
                           for entry in asked)
        lines.append(f"The questions you asked in this conversation, oldest first, with what each was for: {listed}. "
                     "Never ask again for something they answered, even in new words.")
    if gave := [entry for entry in kept[-SAID_SHOWN:] if entry.get("gist")]:
        listed = "; ".join(f"{entry.get('move') or 'other'}: {entry['gist']}" for entry in gave)
        lines.append(f"What your recent replies gave them, oldest first: {listed}. Never give the same again, even in "
                     "new words.")
    if opened := [entry["opens"] for entry in kept[-OPENERS_SHOWN:] if entry.get("opens")]:
        lines.append(f"Your recent replies opened with: {'; '.join(f'\"{words}\"' for words in opened)}. Open this "
                     "one differently.")
    run = next((i for i, entry in enumerate(reversed(kept)) if not (entry.get("q") and entry.get("open_chat"))),
               len(kept))
    if open_chat and run >= 3:
        lines.append(f"Your last {run} replies each ended on a question. This one gives them something and asks nothing, "
                     "unless its question moves them a step on.")
    return lines


def facts_block(lines: list[str]) -> str:
    """The facts as the model reads them, after their message."""
    return "Facts for this reply (never mention them):\n" + "\n".join(f"- {line}" for line in lines)


def _offer_line(framework, phase: str | None) -> str:
    """Where the open offer stands: at the lead-in code adds the five steps after the reply; after them, a clear yes
    starts the set."""
    if phase == STEPS:
        return (f"{framework.name}'s five steps are showing (id {framework.id}). A clear yes in their words starts it: "
                f"set stage to its first stage and open it with {FIRST_STAGE_OPENING}. A clear no: set action to stop.")
    return (f"Your last reply was the lead-in to {framework.name} (id {framework.id}); its five steps follow your reply, "
            "added by code. Answer what they said in a sentence or two and do not start the set. A clear no: set action "
            "to stop.")


def _running_line(framework, phase: str | None, *, held: bool) -> str:
    if phase == FEELINGS and held:
        return (f"{framework.name}'s last stage is done and you asked how they feel. This reply is about their safety: "
                "answer that, and say nothing about the set or a next step. The set stays open and nothing closes now.")
    if phase == FEELINGS:
        return (f"{framework.name}'s last stage is done and you asked how they feel now. Answer how they feel, warmly, "
                "in a sentence or two (in Directive, one), never calling the set a success. Recap nothing and force no "
                "question: if it didn't help or they feel the same, ask what they still need; otherwise offer a next "
                "step only if one would clearly help, or check they got what they came for only if that is unclear. "
                "Code closes the set and shows the closing buttons.")
    stages = stages_of(framework)
    at = stages.index(phase) if phase in stages else 0
    if held:
        after = " This reply is about their safety: Stay on this stage and never say another stage's line."
    elif at + 1 < len(stages):
        after = (f" If its purpose is met, move to `{stages[at + 1]}` and say its line: "
                 f"\"{line_of(framework, stages[at + 1])}\". Never move further than that. If they say they already "
                 "have what they came for, never push on through the steps left: ask how they feel now and set action "
                 "to finish.")
    else:
        after = (" It is the last stage: when the new belief is said in their own words, acknowledge it, ask how they "
                 "feel now, and set action to finish.")
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
