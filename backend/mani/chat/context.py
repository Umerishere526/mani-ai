# ABOUTME: The hidden [ctx] block prefixed to the user's message for one turn only.
# ABOUTME: Built fresh from database state and never stored, so history cannot replay it.

from __future__ import annotations

import re

from mani.chat import repairs
from mani.chat.greeting import AFTER_FRAMEWORK_QUESTIONS, CLARIFICATION_QUESTIONS, CHAT_MORE_LABEL
from mani.chat.safety import normalize
from mani.chat.techniques import SOMATIC_STAGES, covered_stages, moves_on_after
from mani.db.threads import TurnContext
from mani.models.rows import Framework, Message, MessageRole, TechniqueOutcome

# An offer may come from the person's second message, in any style: it was four rounds for
# Supportive and Reflective until Mani's own confidence was made the signal (muhammad,
# 2026-10-01). From their fourth message, a framework the facts fully fit that has still not been
# offered is asked for (spec 0005, AC-16). Counted in the person's own messages.
CLEAR_OFFER_AFTER = 2
OFFER_DUE_AFTER = 4
# After "Keep chatting" an offer may come back after two more exchanges, the same framework or a
# different one, whichever fits now.
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


def offer_due(ctx: TurnContext) -> bool:
    """Nothing has been offered by their fourth message: a framework the facts fully fit is asked
    for now. Never after a decline or a finished framework, and never sent in [ctx]; the redraft
    applies it to the facts after the draft."""
    return ctx.technique is None and _their_messages(ctx) >= OFFER_DUE_AFTER


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


def with_rewrite_notes(prefix: str, reasons: list[str]) -> str:
    """The same [ctx] block with a line per reason the draft cannot stand, so the model writes it
    again. Said in the block the model already reads."""
    lines = "\n".join(f"rewrite: {reason}" for reason in reasons)
    return prefix.replace("\n[/ctx]", f"\n{lines}\n[/ctx]", 1)


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
    urgent: bool = False,
    their_last: str | None = None,
    asked_again: bool | None = None,
) -> str:
    """Format the metadata header for this turn.

    Every value is read from the composed turn snapshot, so the block describes what the
    database holds rather than what an in-memory copy was mutated to mid-request. `framework`,
    `candidate` and `recent_mani_replies` are what the framework content and the caller's own
    history add - all optional, so a turn with none of them still formats exactly as before.

    `framework` is the one already active; its current and next stage go in full. `candidate`
    is DBT STOP when an action is about to happen (`router.urgent`) - its offer lines go in, so
    that offer draws on authored language before the model is asked. Every other offer is
    checked against the facts after the draft. Never both at once: a framework is either
    running or being considered, not both.

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

    # Told to the model as it is enforced: a first offer used to read "yes" here whatever the
    # count, and the code then dropped what the model had been told it could do.
    lines.append(f"cooldown_passed: {'yes' if cooldown_passed(ctx, urgent=urgent) else 'no'}")
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

    if candidate is not None and not safety_concern and cooldown_passed(ctx, urgent=urgent):
        # The client's description is not here: the backend adds it to the offer, and a
        # model given the text copied it, so offers showed it twice.
        lines.extend(_stage_lines("offer", candidate, "offering", resolve_style(ctx)))

    if running:
        lines.extend(
            _running_lines(
                framework, technique.phase, resolve_style(ctx), technique.holds,
                framework_starting=framework_starting, offer_waiting=offer_waiting,
                rephrase=heard_again and technique.holds == 0, known=technique.known,
            )
        )

    return "[ctx]\n" + "\n".join(lines) + "\n[/ctx]\n\n"


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
    """The framework section of the block: which stages Mani sees and how to use them."""
    lines: list[str] = []
    if framework_starting:
        # They have just said yes. What they told Mani before this counts toward the first
        # stage; the note below says how to use it.
        lines.append("framework_starting: yes")
    lines.append(f"active_framework: {framework.id}")
    lines.append(f"framework_stages: {', '.join(framework.phases)}")
    if not framework_starting and moves_on_after(framework, phase):
        lines.extend(_move_on_lines(framework, phase, style, holds, rephrase=rephrase))
        return lines
    stage = _stage_lines("stage", framework, phase, style)
    # The turn they say yes, a first stage their words already answer (by its ready_when) is
    # said back and the second stage's question is asked; otherwise the first is asked.
    index = framework.phase_index(phase)
    if offer_waiting:
        # The offering stage's question is the offer they have just typed past.
        stage = [line for line in stage if not line.startswith("stage_ask:")]
    told = (
        covered_stages(framework, known or {})
        if (framework_starting or offer_waiting) and phase == "offering"
        else []
    )
    if framework_starting and phase == "offering" and index + 1 < len(framework.phases):
        index += 1 + len(told)
        stage = _stage_lines("stage", framework, framework.phases[index], style, to_ask=bool(told))
    lines.extend(stage)
    if told:
        lines.append(_told_line(framework, told, known or {}))
        lines.append(_TOLD_NOTE if framework_starting else _TOLD_IF_YES_NOTE)
        if offer_waiting:
            # If they said yes, the stage to begin with is the first one they have not answered.
            index += len(told)
    elif framework_starting:
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
            _stage_lines(
                "next_stage", framework, framework.phases[index + 1], style,
                to_ask=offer_waiting and bool(told),
            )
        )
    return lines


def _told_line(framework: Framework, told: list[str], known: dict[str, str]) -> str:
    """The stages their earlier words answer, each with those words."""
    answers = (
        (stage, known[framework.stages[stage]["answered_by"]].replace('"', ""))
        for stage in told
    )
    return "already_told: " + " | ".join(f'{stage}: "{words}"' for stage, words in answers)


def _branch_lines(branches: list[dict], style: str, *, mark_counted: bool = False) -> str:
    """A stage's branches on one line. On the stage just answered, a branch that keeps Mani on
    it is marked as using the stage's one extra turn."""
    return " | ".join(
        f"if {e['when']}{' (uses your extra turn)' if mark_counted and e.get('counted') else ''}: "
        f"{repairs.reply_for(e, style)}"
        for e in branches
    )


# The first turn of a framework when what they said before accepting already answers its first
# stages: those are not asked, and the reply shows they were heard.
_TOLD_NOTE = (
    "stage_note: they told you the stages in already_told, in the words shown, before they "
    "accepted. Never ask those stages. Say back what they told you in one short clause, in "
    "their words, adding no feeling or meaning they did not give, then ask stage_ask in their "
    "words, never bare. Report stage as your step"
)

# The same, for an offer they answered by typing: the model decides whether that was a yes.
_TOLD_IF_YES_NOTE = (
    "stage_note: if they said yes, they told you the stages in already_told, in the words shown, "
    "before the offer. Never ask those. Open with the client's line, say back what they told you "
    "in one short clause, in their words, adding no feeling or meaning they did not give, then "
    "ask next_stage_ask in their words, never bare, and report next_stage as your step"
)

# The stage asked on a turn that moves on, word for word. The model reports `stage` as its
# step, or `answered` when it holds.
_MOVE_ON_NOTE = (
    "stage_note: they have replied to the answered stage, so it is done. Ask stage_ask now, "
    "in their words, never bare. If stage_if_earlier_missing is given and nothing usable was "
    "said at that stage, ask that instead. Report stage as your step. Stay on the answered "
    "stage, reporting answered as your step, only in these cases: they did not understand the "
    "question, so say it again once in simpler everyday words; or a branch in "
    "answered_if_unclear applies (a branch marked uses your extra turn uses it up) or you use "
    "one of the client's lines, so use its reply as written"
)

# The same turn at a stage where they choose among options they named: the exception to
# asking the next stage comes first, because it was folded into the next question when it came
# after "ask stage_ask now".
_PICKS_NOTE = (
    "stage_note: they have replied to the answered stage, which asks them to choose among "
    "options they named. If they named two or more options in this conversation and say they "
    "do not know, cannot choose, or ask you to suggest or pick one, stay on the answered stage, "
    "reporting answered as your step, and do not ask stage_ask: offer ONE of their options with "
    "a short reason from what they said, and ask whether it suits them or another would be "
    "easier. Never decide for them. Otherwise it is done: if they asked you to choose, say "
    "plainly that this one is theirs to say, then ask stage_ask now, in their words, never "
    "bare. If stage_if_earlier_missing is given and nothing usable was said at that stage, ask "
    "that instead. Report stage as your step. Also stay on the answered stage only if they did "
    "not understand the question, so say it again once in simpler everyday words, or a branch "
    "in answered_if_unclear applies or you use one of the client's lines, so use its reply as "
    "written"
)

# The turn they asked to hear the question again: the model is shown only that stage's own
# question, so there is nothing to fold the request into.
_REPHRASE_NOTE = (
    "stage_note: they say they did not understand your last message or ask for it another way. "
    "Stay on the answered stage, reporting answered as your step, and ask no other question: "
    "say again the question your last message asked, in simpler, shorter, everyday words, as "
    "ONE question, with answered_ask_simpler as its wording when it is given and answered_ask "
    "as its model otherwise, with nothing added after it, no new topic, no new example, no "
    "answer for them to pick and no explaining of the method. If your last message asked none "
    "or more than one, ask that one question instead. If a branch in "
    "answered_if_unclear applies, use its reply as written instead, with nothing added"
)

# The turn that answers a framework's last stage: Mani concludes, and the code adds the body
# check-in after it, so the model asks nothing of its own.
_CONCLUDE_NOTE = (
    "stage_note: they have replied to the last stage, so the framework is done. Write the "
    "short concluding message that stage_purpose describes, in their words, and ask no "
    "question of your own: the body check in is added after it exactly as written. Report "
    "stage as your step. Stay on the answered stage, reporting answered as your step, only in "
    "these cases: they did not understand the question, so say it again once in simpler "
    "everyday words; or a branch in answered_if_unclear applies (a branch marked uses your "
    "extra turn uses it up) or you use one of the client's lines, so use its reply as written"
)

# The same, once the last stage has used its extra turn.
_CONCLUDE_USED_NOTE = (
    "stage_note: you have already stayed on the answered stage once, so the framework is done "
    "whatever they said. Write the short concluding message that stage_purpose describes, in "
    "their words, and ask no question of your own: the body check in is added after it exactly "
    "as written. Report stage as your step. Only a branch in answered_if_unclear that is not "
    "marked uses your extra turn, or one of the client's lines, may keep you on the answered "
    "stage, and then use its reply as written"
)

# The same turn once the stage has used its extra turn: it is done whatever they said.
_HOLD_USED_NOTE = (
    "stage_note: you have already stayed on the answered stage once, so it is done whatever "
    "they said. Ask stage_ask now, in their words, never bare. If stage_if_earlier_missing is "
    "given and nothing usable was said at that stage, ask that instead. Report stage as your "
    "step. If your last message offered one of their options, they are answering that, so use "
    "the one they chose in what you ask. If they say they still did not understand, say in a "
    "clause that the next question may help, then ask stage_ask. Only a branch in "
    "answered_if_unclear that is not "
    "marked uses your extra turn, or one of the client's lines, may keep you on the answered "
    "stage, and then use its reply as written"
)


def _move_on_lines(
    framework: Framework, phase: str, style: str, holds: int, *, rephrase: bool = False
) -> list[str]:
    """A turn that moves on: the stage they have just answered, then the one to ask.

    The answered stage's question and its readiness are withheld, so there is nothing to ask
    twice, and so is any branch that only asks it again. The body check stages go in full: its
    branches are the client's routing and not a way of asking again. `holds` is how many extra
    turns the answered stage has already used.
    """
    answered = framework.stages.get(phase) or {}
    lines = [f"answered: {phase}"]
    if answered.get("purpose"):
        lines.append(f"answered_purpose: {answered['purpose']}")
    if rephrase:
        # Only this stage's own question, so the model can say it again and nothing else.
        ask = (answered.get("ask") or {}).get(style)
        if ask:
            lines.append(f"answered_ask: {ask}")
        if answered.get("ask_simpler"):
            lines.append(f"answered_ask_simpler: {answered['ask_simpler']}")
        lines.append("asked_again: yes")
        branches = [e for e in answered.get("if_unclear") or [] if not e.get("start_only")]
        if branches:
            lines.append(f"answered_if_unclear: {_branch_lines(branches, style, mark_counted=True)}")
        lines.append(_REPHRASE_NOTE)
        return lines
    if answered.get("picks_from_options") and holds == 0:
        lines.append("answered_picks_options: yes")
    if holds:
        lines.append("hold_used: yes")
    branches = [e for e in answered.get("if_unclear") or [] if not e.get("start_only")]
    if branches:
        lines.append(f"answered_if_unclear: {_branch_lines(branches, style, mark_counted=True)}")
    to_ask = framework.phases[framework.phase_index(phase) + 1]
    lines.extend(_stage_lines("stage", framework, to_ask, style, to_ask=to_ask not in SOMATIC_STAGES))
    if to_ask == "somatic_checkin":
        lines.append(_CONCLUDE_USED_NOTE if holds else _CONCLUDE_NOTE)
    elif holds:
        lines.append(_HOLD_USED_NOTE)
    else:
        lines.append(_PICKS_NOTE if answered.get("picks_from_options") else _MOVE_ON_NOTE)
    return lines


def _stage_lines(
    prefix: str, framework: Framework, phase: str, style: str, *, to_ask: bool = False
) -> list[str]:
    """One stage's full guidance - current or next - resolved to one conversation style.

    Purpose, listening cues, readiness and boundaries are clinical rather than tonal and do
    not vary; `ask` is the one leaf a style changes, so only the resolved style's variant is
    sent rather than all three. A stage that is about to be asked (`to_ask`) leaves out its
    readiness and its branches, which only matter once it has been answered, and carries the
    question to use when an earlier answer was never given.
    """
    stage = framework.stages.get(phase)
    if not stage:
        return [f"{prefix}: {phase}"]

    lines = [f"{prefix}: {phase}"]
    for field in ("purpose", "listen_for") if to_ask else ("purpose", "listen_for", "ready_when"):
        if stage.get(field):
            lines.append(f"{prefix}_{field}: {stage[field]}")
    if stage.get("boundaries"):
        lines.append(f"{prefix}_boundaries: " + "; ".join(stage["boundaries"]))
    if stage.get("if_unclear") and not to_ask:
        lines.append(f"{prefix}_if_unclear: {_branch_lines(stage['if_unclear'], style)}")
    missing = stage.get("if_earlier_missing")
    if missing and to_ask:
        lines.append(
            f"{prefix}_if_earlier_missing: if nothing usable was said at {missing['needs']}: "
            f"{repairs.reply_for(missing, style)}"
        )
    ask = (stage.get("ask") or {}).get(style)
    if ask:
        lines.append(f"{prefix}_ask: {ask}")
    panic = stage.get("panic")
    if panic:
        # DBT STOP's second branch: the lines above are for an action about to happen.
        lines.append(f"{prefix}_when_panicked: {panic_guidance(panic, style)}")
    return lines


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
