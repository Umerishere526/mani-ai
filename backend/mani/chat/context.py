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
from mani.chat.techniques import OFFERING, SOMATIC_STAGES, STUCK_BRANCH, moves_on_after
from mani.db.threads import TurnContext
from mani.models.rows import Framework, Message, MessageRole, TechniqueOutcome

# An offer may come from the person's second message. Counted in the person's own messages.
CLEAR_OFFER_AFTER = 2
# After "I want to keep talking" an offer may come back after two more exchanges, the same
# framework or a different one, whichever fits now.
CLEAR_COOLDOWN_AFTER_DECLINE = 4

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


def their_messages(history: list[Message] | None) -> int:
    """How many messages the person has sent, this one included: their messages in the history,
    not counting a tap on the greeting's style buttons. The history window is long enough that
    any conversation it fills is past its first message."""
    style_labels = {option["label"].lower() for option in STYLE_OPTIONS}
    return 1 + sum(
        1 for m in history or []
        if m.role is MessageRole.USER and (m.selected_prompt or "").lower() not in style_labels
    )


def clarification_used(history: list[Message] | None) -> bool:
    """Whether Mani has already asked the client's one-time clarifying question in this
    conversation. Read from history rather than a stored flag, so it holds even if a process
    restart drops anything else about how the turn was built."""
    return any(
        m.role is MessageRole.MANI
        and any(q in m.content.lower() for q in CLARIFICATION_QUESTIONS)
        for m in (history or [])
    )


# What the separating question sounds like however Mani words it: two possibilities offered
# back as a choice. The router's CLARIFY is the only turn that asks one, so finding one in
# Mani's own replies is how a later turn knows it has already been asked.
_OFFERS_A_CHOICE = re.compile(
    r"\b(or (do|would|are|is|does)|, or\b|either\b).*\?|"
    r"\?.*\b(or (do|would|are|is|does))\b",
    re.IGNORECASE | re.DOTALL,
)


def asked_which_fits(history: list[Message] | None) -> bool:
    """Whether Mani has already asked the question that tells two sets of questions apart.

    Read from Mani's own replies: the question is worded freshly every time, so there is no
    fixed phrase, but it always offers two possibilities back as a choice. Not stored, because
    it is true for a few turns and a column would outlive the fact.
    """
    return any(
        m.role is MessageRole.MANI and _OFFERS_A_CHOICE.search(m.content)
        for m in (history or [])
    )


def offer_refusal(
    ctx: TurnContext,
    history: list[Message] | None,
    *,
    urgent: bool = False,
    safety_concern: bool = False,
) -> str | None:
    """Why no new offer may be made on this turn, or None when one may (spec 0010, AC-3). The
    framework a person's words rule out (the grief veto) and an id the registry does not know are
    refused per offer by the caller; these are the refusals that hold for any offer.

    A finished framework is the latest row, accepted with its phase cleared: once one is
    finished nothing more is offered, so no later row can replace it.
    """
    technique = ctx.technique
    if safety_concern:
        return "safety_concern"
    if technique is not None and technique.outcome is TechniqueOutcome.ACCEPTED:
        return "running" if technique.phase else "finished"
    if technique is not None and technique.outcome is TechniqueOutcome.DECLINED:
        since = ctx.thread.message_count - technique.at_message_count
        return "cooling_down" if since < CLEAR_COOLDOWN_AFTER_DECLINE else None
    if technique is None and not urgent and their_messages(history) < CLEAR_OFFER_AFTER:
        # An action about to be taken is the one case not worth waiting a message for.
        return "first_message"
    return None


# What a person says when they ask only to be listened to, and when they are telling Mani it
# missed something they already said. Phrases, after normalising, so a word inside a real
# sentence is not mistaken for either.
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


# A message this short is read as the answer to the question Mani just asked.
SHORT_REPLY_WORDS = 3
_RAW_WORD = re.compile(r"[^\W_]+(?:['’][^\W_]+)*")


def word_count(text: str) -> int:
    """The words in a message as they were typed: punctuation does not count and a contraction
    stays one word, so "I don't know" is three. `normalize` expands "don't" to "do not", which
    would make it four, so it is not used here."""
    return len(_RAW_WORD.findall(text))


# What a person says when they did not understand a question or want it another way, as it reads
# after `normalize`. A free phrase counts anywhere in the message, as whole words.
HEARD_AGAIN_FREE_PHRASES = (
    "i do not get it", "do not get it", "i do not understand", "do not understand",
    "what you mean", "what do you mean", "what did you mean", "what d you mean",
    "what does that mean", "what s that mean", "whats that mean", "what do u mean", "wdym", "wym",
    "i do not follow", "do not follow", "not following", "what are you asking",
    "say that differently", "say that another way", "say it differently", "say it another way",
    "can you rephrase", "rephrase that", "i am confused", "i am lost",
)
# These read as a story or an objection inside a longer sentence ("I applied and didn't get it",
# "No, you didn't understand", "I don't want to repeat that"), so they count only when the
# message is the phrase, with at most "i", "can you" or "could you" before it and a few short
# words after it.
HEARD_AGAIN_ANCHORED_PHRASES = (
    "did not understand", "did not get it", "did not get that", "did not catch that",
    "say that again", "repeat that", "that does not make sense", "that makes no sense",
    "does not make sense", "makes no sense", "do not know what that means",
    "not sure what that means", "no idea what that means", "idk what that means",
)
_ANCHORED_AFTER = ("it", "that", "you", "u", "the question", "to me", "what you mean", "what you meant")
_ANCHORED = re.compile(
    r"^(?:(?:i|can you|could you) )?(?:"
    + "|".join(re.escape(phrase) for phrase in HEARD_AGAIN_ANCHORED_PHRASES)
    + r")(?: (?:" + "|".join(re.escape(word) for word in _ANCHORED_AFTER) + r"))*$"
)
# Words that do not change what was said.
_HEARD_AGAIN_FILLER = frozenset(
    {"still", "really", "so", "sorry", "just", "very", "honestly", "actually", "please", "quite"}
)
# Words that make the same phrase a statement about their situation, not about the question:
# "I don't understand why he left", "I'm confused about my feelings".
_ABOUT_THEIR_SITUATION = (
    "why", "how", "about", "without", "because", "for me", "mean for", "means for", "not want",
    "my", "he", "she", "they", "him", "her", "them",
)
HEARD_AGAIN_MAX_WORDS = 8
# A message that is only this says they did not follow, the way most people say it: "what?",
# "huh", "wait what", "??".
HEARD_AGAIN_BARE = frozenset(
    {"what", "what what", "wait what", "huh", "eh", "hm", "hmm", "pardon", "come again", "what now"}
)


def asks_to_hear_again(text: str) -> bool:
    """Whether a typed message says they did not understand the question or asks for it another
    way. A short list of phrases, so a request in other words is left to the model."""
    if word_count(text) > HEARD_AGAIN_MAX_WORDS:
        return False
    words = [w for w in normalize(text).split() if w not in _HEARD_AGAIN_FILLER]
    said = " ".join(words)
    padded = f" {said} "
    if any(f" {word} " in padded for word in _ABOUT_THEIR_SITUATION):
        return False
    if said in HEARD_AGAIN_BARE or (not said and "?" in text):
        return True
    return any(f" {phrase} " in padded for phrase in HEARD_AGAIN_FREE_PHRASES) or bool(
        _ANCHORED.match(said)
    )


def classify_reply(text: str) -> str | None:
    """`heard` for a reply that asks only to be listened to, `correction` for one that says Mani
    missed what they had already said, `short` for one of three raw words or fewer, otherwise
    None, in that order of priority. A deterministic read, so the model is told rather than left
    to notice."""
    normalized = normalize(text)
    if any(phrase in normalized for phrase in _HEARD_PHRASES):
        return "heard"
    if any(phrase in normalized for phrase in _CORRECTION_PHRASES):
        return "correction"
    if word_count(text) <= SHORT_REPLY_WORDS:
        return "short"
    return None


_QUESTION = re.compile(r"[^.!?\n]*\?")
# The longest stretch of Mani's last question that is sent back to the model.
MAX_ANSWERING_CHARS = 200


def last_question(text: str) -> str | None:
    """The last question in a message, found wherever it sits in it: the words from the sentence
    break before it up to its question mark."""
    questions = _QUESTION.findall(text)
    return questions[-1].strip() if questions else None


def _answering(history: list[Message]) -> str | None:
    """The question Mani last asked, for a person who has answered it in a word or two. Not the
    code's own permission question: it answers an offer, and the offer is what `offer_waiting`
    is for."""
    last = next((m.content for m in reversed(history) if m.role is MessageRole.MANI), None)
    question = last_question(last) if last else None
    if not question or question in repairs.PERMISSION_QUESTIONS.values():
        return None
    quoted = re.sub(r"[\"“”]", "'", question)
    return disarm(quoted[-MAX_ANSWERING_CHARS:].strip())


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
    framework: Framework | None = None,
    candidate: Framework | None = None,
    history: list[Message] | None = None,
    safety_concern: bool = False,
    offer_waiting: bool = False,
    framework_starting: bool = False,
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
    database holds rather than what an in-memory copy was mutated to mid-request. `framework`,
    `candidate` and `recent_mani_replies` are what the framework content and the caller's own
    history add - all optional, so a turn with none of them still formats exactly as before.

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
    # They asked to hear the question again, on a turn that moves on. Their message is then not an
    # answer to go on from, so `their_last` and `answering` are left out whatever the count.
    heard_again = bool(
        asked_again and running and not framework_starting and not offer_waiting
        and moves_on_after(framework, technique.phase)
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
    if their_last and not offer_waiting and not safety_concern and not heard_again and (
        not running or their_last in ("correction", "short")
    ):
        # Said while the questions run too, except `heard`: a stage says what to do when an
        # answer is unclear, and the base says that guidance wins over `answering`.
        lines.append(f"their_last: {their_last}")
        answering = _answering(history or []) if their_last == "short" else None
        if answering:
            lines.append(f'answering: "{answering}"')
    if offer_waiting:
        # Mani's last reply was an offer, and they typed rather than tapped.
        lines.append("offer_waiting: yes")
    question = None if safety_concern else _after_framework_question(history or [])
    if question:
        lines.append(f"after_framework_question: {question}")

    # Told to the model as it is enforced, so it never writes an offer the code removes.
    lines.append(f"offer_allowed: {'no' if refusal else 'yes'}")
    if technique is not None:
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
        lines.append(f"explain_offer: {EXPLANATIONS[resolve_style(ctx)]}")
        if explaining.summary:
            lines.append(f"offer_looks_at: {' '.join(explaining.summary.split())}")

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
        lines.extend(
            _running_lines(
                framework, technique.phase, resolve_style(ctx), technique.holds,
                framework_starting=framework_starting, offer_waiting=offer_waiting,
                rephrase=heard_again and technique.holds == 0, known=technique.known,
            )
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
    sent rather than all three. `stuck` asks the stage through its `stuck` branch, for a person
    offered the framework because they were stuck.
    """
    stage = framework.stages.get(phase)
    if not stage:
        return [f"{prefix}: {phase}"]
    branch = stage.get(STUCK_BRANCH) if stuck else None
    lines = [f"{prefix}: {phase}"]
    purpose = (branch or {}).get("purpose") or stage.get("purpose")
    if purpose:
        lines.append(f"{prefix}_purpose: {purpose}")
    for field in ("listen_for", "ready_when"):
        if stage.get(field):
            lines.append(f"{prefix}_{field}: {stage[field]}")
    boundaries = [*(stage.get("boundaries") or []), *((branch or {}).get("boundaries") or [])]
    if boundaries:
        lines.append(f"{prefix}_boundaries: " + "; ".join(boundaries))
    if stage.get("if_unclear"):
        lines.append(f"{prefix}_if_unclear: {_branch_lines(stage['if_unclear'], style)}")
    ask = ((branch or {}).get("ask") or stage.get("ask") or {}).get(style)
    if ask:
        lines.append(f"{prefix}_ask: {ask}")
    panic = stage.get("panic")
    if panic:
        # DBT STOP's second branch: the lines above are for an action about to happen.
        lines.append(f"{prefix}_when_panicked: {panic_guidance(panic, style)}")
    return lines


# The offer's stuck branch on the turn right after "Are you feeling stuck?" was asked.
_STUCK_CHECK_ANSWERED = (
    "only if they answered yes to \"Are you feeling stuck?\", offer with this instead of the lines "
    "above; if they said no, offer nothing"
)


def stuck_guidance(branch: dict, label: str) -> str:
    """The offer's branch for a person who stays stuck, on one line. It carries no question: the
    description and the permission question are added to the offer by the code."""
    parts = [label, branch.get("purpose", "")]
    if branch.get("boundaries"):
        parts.append("; ".join(branch["boundaries"]))
    return ". ".join(p for p in parts if p)


def panic_guidance(panic: dict, style: str) -> str:
    """A stage's branch for someone panicked with no action named, on one line."""
    parts = [
        "when they are panicked right now with no action named, use this instead of the lines "
        "above, which are for when they are about to act",
        panic.get("purpose", ""),
    ]
    if panic.get("boundaries"):
        parts.append("; ".join(panic["boundaries"]))
    ask = (panic.get("ask") or {}).get(style)
    if ask:
        parts.append(f"ask: {ask}")
    return ". ".join(p for p in parts if p)
