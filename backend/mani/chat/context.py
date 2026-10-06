# ABOUTME: The hidden [ctx] block prefixed to the user's message for one turn only.
# ABOUTME: Built fresh from database state and never stored, so history cannot replay it.

from __future__ import annotations

import re

from mani.chat import repairs
from mani.chat.greeting import AFTER_FRAMEWORK_QUESTIONS, CLARIFICATION_QUESTIONS, CHAT_MORE_LABEL
from mani.chat.offer import Action as OfferAction, Decision
from mani.chat.router import Signal, is_confident
from mani.chat.safety import normalize
from mani.db.threads import TurnContext
from mani.models.rows import Framework, Message, MessageRole, TechniqueOutcome

# How many messages must pass before a technique may be offered again.
# After "Keep chatting", three of Mani's replies before it may check again - the same
# framework or a different one, whichever fits now (muhammad, 2026-09-24).
COOLDOWN_AFTER_DECLINE = 6

# A confident offer may come from the person's second message, in any style: it was four rounds
# for Supportive and Reflective until Mani's own confidence was made the signal (muhammad,
# 2026-10-01). A fit that is only the nearest may be offered from their fourth message, when
# Mani judges the situation clear enough; it is never owed by a count (client meeting,
# 2026-10-02). Counted in the person's own messages.
CLEAR_OFFER_AFTER = 2
CLOSEST_FIT_AFTER = 4
# After "Keep chatting" a confident offer may come back after two more exchanges; the closest
# fit waits the full COOLDOWN_AFTER_DECLINE.
CLEAR_COOLDOWN_AFTER_DECLINE = 4
# A stage asked about this many times without being met is moved on from (client meeting,
# 2026-10-02: "if she doesn't get an outcome after two or three turns, we need to pivot").
STAGE_ASKS_BEFORE_MOVING_ON = 3
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


def their_messages(ctx: TurnContext) -> int:
    """How many messages the person has sent. Public because the offer cadence is counted in
    their messages, not in turns."""
    return _their_messages(ctx)


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


# What a person says when they have given almost nothing, and when they are telling Mani it
# missed something they already said. Whole messages / phrases, after normalising, so a vague
# word inside a real sentence ("yeah, my manager shouted") is not mistaken for either.
_VAGUE_REPLIES = frozenset({
    "yeah", "yea", "yup", "yep", "ok", "okay", "maybe", "hmm", "hm", "sure", "i guess",
    "idk", "dunno", "i do not know", "do not know", "i am not sure", "not sure", "no idea",
    "kind of", "sort of", "kinda", "i suppose", "yes", "yeah right", "no", "nope",
    "i do not know what i need", "i do not know what i want",
})
_HEARD_PHRASES = (
    "just need to get it out", "just want to get it out", "just need to vent", "just want to vent",
    "just want to talk", "just need to talk", "just listen", "dont want advice", "do not want advice",
    "not looking for advice", "dont ask me", "do not ask me", "no questions",
    "dont give me a technique", "do not give me a technique", "dont want a technique",
    "do not want a technique", "dont want to do an exercise", "do not want to do an exercise",
    "stop asking me questions", "stop asking questions", "enough questions",
    "so many questions", "too many questions",
    "dont want a framework", "do not want a framework",
)
_CORRECTION_PHRASES = (
    "just told you", "i told you", "already told you", "i already told", "i just said",
    "already said", "i said that", "like i said", "as i said", "you asked that",
    "you already asked", "i just answered", "i answered", "already answered",
    "that is not what i said", "that is not what i mean", "not what i meant",
    "you are misunderstanding", "you misunderstood",
)
# The person has turned to the conversation itself: how Mani is listening or talking. That is
# answered before anything else, and nothing is offered on that turn (client meeting,
# 2026-10-02: "I'm frustrated with you" was answered with an offer of questions).
_ABOUT_MANI_PHRASES = (
    "you are not listening", "you do not listen", "you dont listen", "you never listen",
    "you are not hearing me", "you do not hear me", "you dont hear me",
    "you do not understand me", "you dont understand me", "frustrated with you",
    "annoyed with you", "angry with you", "angry at you", "that is not helpful",
    "this is not helpful", "you are not helping", "can we go back", "you are going off topic",
    "going off topic", "why are you asking", "sounds robotic", "you sound like a robot",
    "talk normally", "speak normally", "talk like a person", "in plain words", "down to earth",
)


def with_rewrite_notes(prefix: str, reasons: list[str]) -> str:
    """The same [ctx] block with a line per reason the draft cannot stand, so the model writes it
    again. Said in the block the model already reads."""
    lines = "\n".join(f"rewrite: {reason}" for reason in reasons)
    return prefix.replace("\n[/ctx]", f"\n{lines}\n[/ctx]", 1)


# A whole message that ends the framework they are in. Whole messages only, so "he won't stop
# calling me" or "I want to stop drinking" is never read as one.
_STOP_REPLIES = frozenset({
    "stop", "stop here", "stop this", "lets stop", "let s stop", "let us stop", "lets stop here",
    "let s stop here",
    "can we stop", "can we stop here", "can we stop this", "i want to stop", "i want to stop here",
    "i want to stop this", "i would like to stop", "never mind", "nevermind", "forget it",
    "leave it", "drop it", "not now", "enough", "that is enough", "i am done", "im done",
    "i do not want to do this", "i do not want to do this anymore", "i do not want to continue",
    "forget it i do not want to do this anymore", "forget it i do not want to do this",
})
_STOP_FILLER = frozenset({"ok", "okay", "please", "mani", "just", "no"})


def wants_to_stop(text: str) -> bool:
    """Whether the whole message asks to end the framework now."""
    words = normalize(text).split()
    while words and words[0] in _STOP_FILLER:
        words = words[1:]
    while words and words[-1] in _STOP_FILLER:
        words = words[:-1]
    return " ".join(words) in _STOP_REPLIES


def _says(normalized: str, phrases: tuple[str, ...]) -> bool:
    """Whether any phrase appears as whole words, so "i told you" is not found in "i told your"."""
    padded = f" {normalized} "
    return any(f" {phrase} " in padded for phrase in phrases)


def classify_reply(text: str) -> str | None:
    """`vague` for a reply that says almost nothing, `correction` for one that says Mani missed
    what they had already said, `heard` for one that asks only to be listened to, `about_mani`
    for one about how Mani is listening or talking, otherwise None. A deterministic read, so
    the model is told rather than left to notice."""
    normalized = normalize(text)
    if _says(normalized, _HEARD_PHRASES):
        return "heard"
    if _says(normalized, _CORRECTION_PHRASES):
        return "correction"
    if _says(normalized, _ABOUT_MANI_PHRASES):
        return "about_mani"
    if normalized in _VAGUE_REPLIES:
        return "vague"
    return None


# What they said about the conversation itself is answered before anything else is asked or
# offered.
HOLDS_THE_QUESTIONS = ("correction", "about_mani", "heard")


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
    decision: Decision | None = None,
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
        not running or their_last in ("correction", "about_mani")
    ):
        # A vague reply is not flagged while the questions run: each stage already says what to
        # do with one. A correction or a word about Mani is, because no stage says what to do.
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
    if not safety_concern and not running and closest_fit_ok(ctx, urgent=urgent):
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

    if decision is not None:
        # Code has already decided what this turn does, so the model is told the action
        # rather than the evidence: a shortlist invites it to choose again. The framework id
        # is never named outside the offer's own lines, so it cannot be echoed to the person.
        if not safety_concern:
            lines.append(f"action: {decision.action.value}")
            if decision.action is OfferAction.CLARIFY and decision.separates_as_text:
                lines.append(f"separates: {decision.separates_as_text}")
            if decision.offers and candidate is not None:
                # The client's description is not here: the backend adds it to the offer, and
                # a model given the text copied it, so offers showed it twice.
                lines.extend(_stage_lines("offer", candidate, "offering", resolve_style(ctx)))
    elif shortlist and not safety_concern:
        ranked = ", ".join(f"{s.framework_id} ({s.score:.2f})" for s in shortlist)
        lines.append(f"framework_shortlist: {ranked}")
        if (
            candidate is not None
            and is_confident(shortlist)
            and cooldown_passed(ctx, urgent=urgent)
            and their_last not in HOLDS_THE_QUESTIONS
        ):
            lines.extend(_stage_lines("offer", candidate, "offering", resolve_style(ctx)))

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
        if offer_waiting or their_last == "about_mani":
            # The offering stage's question is the offer they have just typed past; and a word
            # about how Mani is talking is answered before the next question is asked.
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
        asks = _asks_in_stage(ctx)
        if asks == STAGE_ASKS_BEFORE_MOVING_ON - 1 and not framework_starting:
            # Asked once already and still not met. Asking the same thing again in other
            # words is where a framework starts to read as a form (muhammad, 2026-10-05):
            # follow what they actually said, and let it still serve the stage.
            lines.append(
                "stage_note: they have not answered what this stage needs. Do not ask it "
                "again in other words. Take what they did say, follow it the way a friend "
                "would, and let that question reach the same thing from where they are"
            )
        if asks >= STAGE_ASKS_BEFORE_MOVING_ON and not framework_starting:
            lines.append(
                f"stage_note: you have asked about this stage {asks} times; take what they have "
                "given as enough and ask the next stage's question, or ask whether they want to "
                "stop here. Never ask for this stage again in other words"
            )
        if 0 <= index < len(framework.phases) - 1:
            lines.extend(
                _stage_lines("next_stage", framework, framework.phases[index + 1], style)
            )

    return "[ctx]\n" + "\n".join(lines) + "\n[/ctx]\n\n"


def _asks_in_stage(ctx: TurnContext) -> int:
    """How many of Mani's replies have asked about the current stage, this one included."""
    since = ctx.technique.phase_since if ctx.technique else None
    if since is None:
        return 0
    return (ctx.thread.message_count - since) // 2 + 1


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
        rendered = " | ".join(f"if {e['when']}: {repairs.reply_for(e, style)}" for e in stage["if_unclear"])
        lines.append(f"{prefix}_if_unclear: {rendered}")
    ask = (stage.get("ask") or {}).get(style)
    if ask:
        lines.append(f"{prefix}_ask: {ask}")
    return lines
