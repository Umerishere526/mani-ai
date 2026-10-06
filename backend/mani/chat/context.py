# ABOUTME: The hidden [ctx] block prefixed to the user's message for one turn only.
# ABOUTME: Built fresh from database state and never stored, so history cannot replay it.

from __future__ import annotations

import re

from mani.chat import repairs
from mani.chat.greeting import (
    AFTER_FRAMEWORK_QUESTIONS, CHAT_MORE_LABEL, CLARIFICATION_QUESTIONS, STYLE_OPTIONS,
)
from mani.chat.offer import Action as OfferAction, Decision
from mani.chat.safety import normalize
from mani.db.threads import TurnContext
from mani.models.rows import Framework, Message, MessageRole, TechniqueOutcome

# How many messages must pass before a technique may be offered again.
# After "Keep chatting", three of Mani's replies before it may check again - the same
# framework or a different one, whichever fits now (muhammad, 2026-09-24).
COOLDOWN_AFTER_DECLINE = 6

# A confident offer may come from the person's second message, in any style: it was four rounds
# for Supportive and Reflective until Mani's own confidence was made the signal (muhammad,
# 2026-10-01). When it has not offered by their fourth message the closest fit is due: it offers
# that, with Keep chatting beside it. Counted in the person's own messages.
CLEAR_OFFER_AFTER = 2
CLOSEST_FIT_AFTER = 4
# After "Keep chatting" a confident offer may come back after two more exchanges; the closest
# fit waits the full COOLDOWN_AFTER_DECLINE.
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
    """Whether a confident offer may be made yet: [ctx] reports it, repairs.apply enforces it."""
    technique = ctx.technique
    if technique is None:
        # An action about to be taken is the one case not worth waiting the rounds out.
        return urgent or _their_messages(ctx) >= CLEAR_OFFER_AFTER
    return ctx.thread.message_count - technique.at_message_count >= clear_cooldown_for(
        technique.outcome
    )


def earliest_offer_ok(ctx: TurnContext, activation: dict | None, *, urgent: bool = False) -> bool:
    """A framework file may set `earliest_offer_message` where its fit needs more than the first
    two messages (ABCDE, Thought Reframe and ACT depend on what the person took it to mean).
    Only the first offer waits; after Keep chatting they have said more."""
    if ctx.technique is not None or urgent:
        return True
    return _their_messages(ctx) >= (activation or {}).get("earliest_offer_message", 0)


def closest_fit_ok(ctx: TurnContext, *, urgent: bool = False) -> bool:
    """Whether the closest fit may be offered when nothing fits well."""
    technique = ctx.technique
    if technique is None:
        return urgent or _their_messages(ctx) >= CLOSEST_FIT_AFTER
    return ctx.thread.message_count - technique.at_message_count >= cooldown_for(
        technique.outcome
    )


def closest_fit_due(ctx: TurnContext) -> bool:
    """The first offer has not come by their fourth message: the closest fit is owed now."""
    return ctx.technique is None and _their_messages(ctx) >= CLOSEST_FIT_AFTER


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


def with_rewrite_notes(prefix: str, reasons: list[str]) -> str:
    """The same [ctx] block with a line per reason the draft cannot stand, so the model writes it
    again. Said in the block the model already reads."""
    lines = "\n".join(f"rewrite: {reason}" for reason in reasons)
    return prefix.replace("\n[/ctx]", f"\n{lines}\n[/ctx]", 1)


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
    urgent: bool = False,
    their_last: str | None = None,
    asked_again: bool | None = None,
    stuck_candidate: bool = False,
    refusal: str | None = None,
    explaining: Framework | None = None,
    answering_practice: bool = False,
    decision: Decision | None = None,
    skipped: bool = False,
    their_question: bool = False,
) -> str:
    """Format the metadata header for this turn.

    Every value is read from the composed turn snapshot, so the block describes what the
    database holds rather than what an in-memory copy was mutated to mid-request. `shortlist`,
    `framework`, `candidate` and `recent_mani_replies` are what the router, the framework
    content and the caller's own history add - all optional, so a turn with none of them still
    formats exactly as before.

    `framework` is the one already active; its current and next stage go in full. `candidate`
    is DBT STOP when an action is about to happen (`router.urgent`) - its offer lines go in, so
    that offer draws on authored language before the model is asked - or, with
    `stuck_candidate`, the framework for a person who stays stuck, on the turn right after Mani
    asked "Are you feeling stuck?". Never both at once: a framework is either running or being
    considered, not both. `refusal` is `offer_refusal` for this turn, told to the model as
    `offer_allowed`. `explaining` is the framework whose offer they asked to hear more about:
    its name and what it looks at go in, as they do with `candidate`, so either reply can say
    what it is called and what you will look at together.

    `history` is the same window the caller already loads for the model's own conversation
    view - nothing new is fetched for it. Only Mani's own messages in it become recent_openers;
    the person's messages are read here but never surfaced back to the model as an "opener".
    """
    technique = ctx.technique
    # Named first because every stage_ask and offer_ask below is resolved from it, and named
    # `conversation_style` rather than `style` because `recent_styles` three lines down means
    # the response shape, which is a different thing entirely.
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
    if not running and not clarification_used(history):
        lines.append("clarification_available: yes")
    if not running:
        # What the question is about while no stage decides it (muhammad, 2026-09-24): said
        # here, next to the message, because the style rule in the long prompt alone did not hold.
        focus = "feeling, then the way through" if resolve_style(ctx) == "direct" else "feelings"
        lines.append(f"question_focus: {focus}")
    if their_last and not offer_waiting and not safety_concern and (
        not running or their_last == "correction"
    ):
        # A vague reply is not flagged while the questions run: each stage already says what to
        # do with one. A correction is, because no stage says to take what they already told you.
        lines.append(f"their_last: {their_last}")
    if offer_waiting:
        # Mani's last reply was an offer, and they typed rather than tapped.
        lines.append("offer_waiting: yes")
    question = None if safety_concern else _after_framework_question(history or [])
    if question:
        lines.append(f"after_framework_question: {question}")

    # Told to the model as it is enforced: a first offer used to read "yes" here whatever the
    # count, and the code then dropped what the model had been told it could do.
    lines.append(f"cooldown_passed: {'yes' if cooldown_passed(ctx, urgent=urgent) else 'no'}")
    if not safety_concern and not running:
        if closest_fit_due(ctx):
            lines.append("closest_fit: due")
        elif closest_fit_ok(ctx, urgent=urgent):
            lines.append("closest_fit: ok")
    if technique is not None:
        since_last = ctx.thread.message_count - technique.at_message_count
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
        styles = " → ".join(s.shape for s in ctx.recent_styles)
        lines.append(f"recent_styles: {styles}")

    # A separate signal from recent_styles: that is the abstract shape, this is the
    # literal words a reply opened with - two replies can vary in shape while still starting
    # the same way, which is what "recent_styles" alone cannot catch.
    mani_replies = [m.content for m in (history or []) if m.role is MessageRole.MANI]
    openers = [
        _opener(text) for text in mani_replies[-RECENT_OPENERS_WINDOW:] if text.strip()
    ]
    if openers:
        quoted = ", ".join(f'"{o}"' for o in openers)
        lines.append(f"recent_openers: {quoted}")

    if answering_practice:
        # Their message is how they feel after the body practice that ends a framework.
        lines.append("answering_practice: yes")
    if explaining is not None:
        lines.append("explain_offer: yes")
        lines.extend(_named_offer_lines(explaining))

    if decision is not None and not safety_concern:
        # Code has already decided what this turn does, so the model is told the action rather
        # than the evidence: a shortlist invites it to choose again. The framework id is never
        # named outside the offer's own lines, so it cannot be echoed to the person.
        lines.append(f"action: {decision.action.value}")
        if decision.action is OfferAction.CLARIFY and decision.separates_as_text:
            lines.append(f"separates: {decision.separates_as_text}")
        if decision.action is OfferAction.ASSESS and decision.to_find_out:
            # What the nearest sets of questions still need to know. The model picks the one
            # worth asking and the words for it; this is never a list to work through, and
            # the framework ids it came from are not here, so none can be echoed.
            lines.append(
                "to_find_out: " + "; ".join(decision.to_find_out)
            )

    if skipped:
        # They passed the question over. The step is already being left, so the reply must not
        # ask it again in any form; the next step's question is in the steps below.
        lines.append(
            "skipped: yes\nstep_note: they are passing this question over. Take it lightly in a "
            "few words, never ask it again in any form, and go straight on to the next step"
        )

    if their_question and not safety_concern:
        # They asked Mani something: answered first, plainly (spec 0011, AC-19).
        lines.append("their_question: yes")

    if candidate is not None and refusal is None:
        lines.extend(_named_offer_lines(candidate))
        lines.extend(_stage_lines("offer", candidate, "offering", resolve_style(ctx)))
        branch = (candidate.stages.get("offering") or {}).get(STUCK_BRANCH)
        if stuck_candidate and branch:
            lines.append(f"offer_when_stuck: {stuck_guidance(branch, _STUCK_CHECK_ANSWERED)}")

    if running:
        style = resolve_style(ctx)
        if framework_starting:
            # They have just said yes. What they told Mani before this counts toward the first
            # stage; the note below says how to use it.
            lines.append("framework_starting: yes")
        lines.append(f"active_framework: {framework.id}")
        lines.append(f"framework_stages: {', '.join(framework.phases)}")
        stage = _stage_lines("stage", framework, technique.phase, style)
        # The turn they say yes, a first stage their words already answer (by its ready_when) is
        # said back and the second stage's question is asked; otherwise the first is asked.
        index = framework.phase_index(technique.phase)
        if offer_waiting:
            # The offering stage's question is the offer they have just typed past.
            stage = [line for line in stage if not line.startswith("stage_ask:")]
        if framework_starting and technique.phase == "offering" and index + 1 < len(framework.phases):
            index += 1
            stage = _stage_lines("stage", framework, framework.phases[index], style)
        lines.extend(stage)
        if framework_starting:
            lines.append(
                "stage_note: first judge whether what they have told you meets stage_ready_when. "
                "If it does, say it back in a clause, in their words, and ask the next stage's "
                "question (next_stage_ask) in the same reply, never asking them to confirm it. "
                "If it does not, ask stage_ask built from what they said, in their words, so "
                "that it asks for the missing thing"
            )
        else:
            lines.append(
                "stage_note: put the stage question in terms of what they have told you, in "
                "their words; never send it bare"
            )
        if 0 <= index < len(framework.phases) - 1:
            lines.extend(
                _stage_lines("next_stage", framework, framework.phases[index + 1], style)
            )

    return "[ctx]\n" + "\n".join(lines) + "\n[/ctx]\n\n"


def _named_offer_lines(framework: Framework) -> list[str]:
    """What an offer, or the explanation of one, says the framework is called and looks at."""
    lines = [f"offer_name: {framework.name}"]
    if framework.summary:
        lines.append(f"offer_looks_at: {' '.join(framework.summary.split())}")
    return lines


def _running_lines(
    framework: Framework,
    phase: str,
    style: str,
    holds: int,
    *,
    framework_starting: bool,
    offer_waiting: bool,
    rephrase: bool = False,
    known: dict[str, str] | None = None,
) -> list[str]:
    """The framework section of the block. The model judges when a step is done (spec 0010,
    AC-5), so it sees every step still ahead, each with what makes it done; the body check
    stages, which the code routes, go as before."""
    lines: list[str] = []
    if framework_starting:
        lines.append("framework_starting: yes")
    lines.append(f"active_framework: {framework.id}")
    if phase in SOMATIC_STAGES:
        lines.extend(_stage_lines("stage", framework, phase, style))
        index = framework.phase_index(phase)
        if index + 1 < len(framework.phases):
            lines.extend(_stage_lines("next_stage", framework, framework.phases[index + 1], style))
        return lines
    starting = framework_starting or (offer_waiting and phase == OFFERING)
    if phase == OFFERING and not starting:
        # Offered and not yet answered: the offering stage is what the reply is about.
        return lines + _stage_lines("stage", framework, phase, style)
    first = framework.phase_index(OFFERING) + 1 if phase == OFFERING else framework.phase_index(phase)
    check_in = framework.phase_index("somatic_checkin")
    end = check_in if check_in >= 0 else len(framework.phases)
    stuck = STUCK_BRANCH in (known or {})
    for step in framework.phases[first:end]:
        lines.extend(_stage_lines("step", framework, step, style, stuck=stuck))
    if starting:
        lines.append(_START_NOTE if framework_starting else _IF_YES_NOTE)
        return lines
    lines.append(f"current_step: {phase}")
    if rephrase:
        lines.append("asked_again: yes")
        lines.append(_REPHRASE_NOTE)
    elif holds:
        lines.append("hold_used: yes")
        lines.append(_HOLD_USED_NOTE)
    else:
        lines.append(_STEP_NOTE)
    return lines


def _branch_lines(branches: list[dict], style: str) -> str:
    """A stage's branches on one line."""
    return " | ".join(f"if {e['when']}: {repairs.reply_for(e, style)}" for e in branches)


# The turn they say yes: straight to the first step not already met, with no opening line
# (Lolly's review, spec 0011, AC-4). The step the offer was built on is met (AC-5).
_START_NOTE = (
    "step_note: they said yes. Ask the first step whose ready_when what they have told you does "
    "not already meet, and report it as step. The step the offer was built on is already met"
)
_IF_YES_NOTE = (
    "step_note: if they said yes, ask the first step whose ready_when what they have told you "
    "does not already meet, and report it as step. The step the offer was built on is already met"
)
# A turn inside the framework: they have answered current_step.
_STEP_NOTE = (
    "step_note: they have answered current_step. If it, or anything they said, meets a step's "
    "ready_when, that step is done: ask the next step that is not, and report it as step. If it "
    "does not, make one more attempt at current_step, more simply or another way, reporting it as "
    "step. If the framework has what it needs, or is no longer helping, end it and report ending"
)
_HOLD_USED_NOTE = (
    "step_note: you have made your one more attempt at current_step, so it is done whatever they "
    "said. Ask the next step their words do not already meet, or end the framework and report "
    "ending; never invent what they did not give"
)
_REPHRASE_NOTE = (
    "step_note: they did not understand your last question. Ask it again once in simpler, shorter "
    "everyday words, as one question, reporting current_step as step"
)


def _stage_lines(prefix: str, framework: Framework, phase: str, style: str, *, stuck: bool = False) -> list[str]:
    """One stage's guidance, resolved to one conversation style.

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
        rendered = " | ".join(f"if {e['when']}: {repairs.reply_for(e, style)}" for e in stage["if_unclear"])
        lines.append(f"{prefix}_if_unclear: {rendered}")
    ask = (stage.get("ask") or {}).get(style)
    if ask:
        lines.append(f"{prefix}_ask: {ask}")
    return lines
