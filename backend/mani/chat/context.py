# ABOUTME: The hidden [ctx] block prefixed to the user's message for one turn only.
# ABOUTME: Built fresh from database state and never stored, so history cannot replay it.

from __future__ import annotations

import re

from mani.chat import repairs
from mani.chat.greeting import AFTER_FRAMEWORK_QUESTIONS, CLARIFICATION_QUESTIONS, CHAT_MORE_LABEL
from mani.chat.safety import normalize
from mani.db.threads import TurnContext
from mani.models.rows import ENDING_STAGES, Framework, Message, MessageRole, TechniqueOutcome

# How many messages must pass before a technique may be offered again.
# After "Keep chatting", three of Mani's replies before it may check again - the same
# framework or a different one, whichever fits now (muhammad, 2026-09-24).
COOLDOWN_AFTER_DECLINE = 6

# No fixed count: a framework is offered as soon as it fits, from the person's first message
# (muhammad, 2026-10-10). When it has not offered by then the closest fit is due, with Keep
# chatting beside it: by the fourth message in Direct, which gets to the heart of it sooner, by
# the sixth in Supportive and Reflective, which may take more turns to hear the person out.
# Counted in the person's own messages.
CLOSEST_FIT_AFTER = 4
CLOSEST_FIT_AFTER_GENTLE = 6
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


def cooldown_passed(ctx: TurnContext) -> bool:
    """Whether a confident offer may be made yet: [ctx] reports it, repairs.apply enforces it.
    The first offer never waits; only one after an earlier offer does."""
    technique = ctx.technique
    if technique is None:
        return True
    return ctx.thread.message_count - technique.at_message_count >= clear_cooldown_for(
        technique.outcome
    )


def closest_fit_ok(ctx: TurnContext, *, urgent: bool = False) -> bool:
    """Whether the closest fit may be offered when nothing fits well."""
    technique = ctx.technique
    if technique is None:
        return urgent or _their_messages(ctx) >= _closest_fit_after(ctx)
    return ctx.thread.message_count - technique.at_message_count >= cooldown_for(
        technique.outcome
    )


def closest_fit_due(ctx: TurnContext) -> bool:
    """The first offer has not come in the turns this style allows: the closest fit is owed now."""
    return ctx.technique is None and _their_messages(ctx) >= _closest_fit_after(ctx)


def _closest_fit_after(ctx: TurnContext) -> int:
    """The person's message by which the closest fit is owed, in the style in force."""
    return CLOSEST_FIT_AFTER if resolve_style(ctx) == "direct" else CLOSEST_FIT_AFTER_GENTLE


def with_rewrite_notes(prefix: str, reasons: list[str]) -> str:
    """The same [ctx] block with a line per reason the draft cannot stand, so the model writes it
    again. Said in the block the model already reads."""
    lines = "\n".join(
        [f"rewrite: {reason}" for reason in reasons] + _meaning("rewrite", reasons)
    )
    return prefix.replace("\n[/ctx]", f"\n{lines}\n[/ctx]", 1)


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


# What each line of the block means, sent under the line itself and only for the value it has
# this turn: a vague reply carries the vague guidance and nothing about being heard. Keeping the
# meaning beside the value is also what keeps the two from drifting apart, which they did while
# the meanings lived in response_format.md (2026-10-08).
_FIT_PLAINLY = "Offer it plainly, the way you would one that fits exactly."
_MEANING: dict[str, str | dict[str, str]] = {
    "conversation_style": {
        "direct": (
            "Direct, for the whole conversation. Clear, concise and focused, never cold, abrupt, "
            "transactional or interrogative. Most replies are just the question; never open by "
            "restating what they said. A few plain words of your own come first only after "
            "something painful or new. Get to the heart of it quickly, so the right set of "
            "questions can come as soon as it fits."
        ),
        "supportive": (
            "Supportive, for the whole conversation. Warm, understanding and encouraging. A brief "
            "word in your own words that shows you are with them, never their sentence handed "
            "back, then a gentle question. Take the turns this needs."
        ),
        "reflective": (
            "Reflective, for the whole conversation. Help them look at what sits behind what they "
            "said, so the understanding is their own. Reflect the meaning when it opens "
            "something, never their words. Take the turns this needs."
        ),
    },
    "conversation_phase": {
        "understanding": (
"nothing has been offered yet. Your questions come from listening, the way a "
            "specialist listens. In reasoning, first write what they have told you, then choose "
            "the one part of it that matters most to them, the part they gave the most weight or "
            "said last. If you do not know what happened in that part, ask once, in a few words. "
            "Once you do, stop asking what happened and ask about something real and present in "
            "it that they have not said yet, in their words: what they have noticed since, or how "
            "they are with it today. Never ask for something their message already answers, "
            "including why they think something when they said what led them to it. Never a hypothetical such as what would it mean or what would it be like if. "
            "Asking how something they said is affecting them is fine, in their words. Never tell "
            "them what they feel. One short question, about ten words, "
            "one thing at a time, in plain everyday words, no harder than the last. No two-part "
            "questions, no menu of choices, no advice and no suggestion hidden in a question. "
            "What they say about how it is for them shows which set fits. As soon as one fits, "
            "offer it."
        ),
        "framework": "the questions are running, so follow the stage.",
        "talking": (
            "an offer was declined or the questions finished, so talk with them, following "
            "what they say."
        ),
    },
    "question_focus": {
        "the heart of it": (
            "ask about the one part that matters most to them: what they have noticed since, or "
            "how they are with it now, in a few plain words, never what they already said. Never dig for more facts about the "
            "event or the other people in it."
        ),
        "how it is for them": (
            "ask gently how they are with that one part today, in their words, so they can find "
            "the word for it themselves, never what made them think it. Once their concern is "
            "clear, never ask what is at stake."
        ),
        "what sits behind it": (
            "ask what sits behind that one part, why it matters to them or what it says to them, "
            "in plain words, never what made them think it. Never ask what is at stake, and never "
            "the same question twice in other words."
        ),
    },
    "clarification_available": {
        "yes": (
            "if several distinct things have come up and you cannot tell which matters most, "
            "you may ask one of the client's two lines, word for word, \"Do I have this right?\" "
            "or \"What would you like us to focus on today?\" Then follow their answer. Once "
            "asked, never again."
        ),
    },
    "offer_waiting": {
        "yes": (
            "your last reply offered and they typed instead of tapping. If they said yes, set "
            "state.accepted to true and begin. If they asked what it involves, answer and offer "
            "again. Anything else is Keep chatting, so set state.accepted to false, follow them, "
            "and offer nothing in this reply."
        ),
    },
    "cooldown_passed": {
        "yes": "an offer may be made in this reply, if one fits.",
        "no": "offer nothing in this reply.",
    },
    "since_last": "how many messages have passed since the last offer.",
    "closest_fit": {
        "due": (
            "you have talked for several replies without offering, so offer the set that fits best "
            f"now. {_FIT_PLAINLY}"
        ),
        "ok": f"you may offer the set that fits best. {_FIT_PLAINLY}",
    },
    "this_thread": (
        "what was last offered in this conversation and how it went. One they declined may come "
        "back once the cooldown has passed, if it still fits. One they just finished may not. "
        "If they ask for one they declined, that is a yes at any time, so begin it and report "
        "state.accepted as true."
    ),
    "history": "what was tried earlier in this conversation, and whether it helped.",
    "library_pending": {"yes": "offer the Library before anything new."},
    "current_phase": "the stage the questions are on, as last recorded.",
    "safety": {
        "concern": (
            "something they said may mean they are not safe. No stage question and no offer. "
            "Stay with what they said, gently and plainly, and leave room for more. The "
            "questions will wait."
        ),
    },
    "recent_crisis": {
        "yes": (
            "another conversation of theirs was flagged recently. You know only that. Go gently "
            "and slowly, and do not mention it unless they do."
        ),
    },
    "recent_styles": "the shapes of your last few replies. A shape may come back.",
    "recent_openers": (
        "the first words of your last few replies. Do not open your new reply the same way."
    ),
    "offer": (
        "the offering stage of the set for pausing before an action they are about to take, in the "
        "lines below. Use them to judge whether it fits. offer_ask is the permission question "
        "added after your part, so never write it yourself. It is the backend's pick from their "
        "words, so if what they described fits another set better by Telling them apart, offer "
        "that one instead."
    ),
    "framework_starting": {
        "yes": "they just said yes. stage_note says how to use what they already told you.",
    },
    "active_framework": (
        "the set of questions running, with its stages in order. Then the stage you are on and, "
        "unless it is the last, the one after, each with its purpose, what to listen for, when "
        "it is done, its boundaries and what to do if unclear. The stages after those are listed "
        "as later_stage, each with only when it is done and its question. Each ask is a model "
        "question already in this style, so ask what it asks, in their words, about their "
        "situation, never word for word."
    ),
    "later_stage": (
        "a stage after the next one, shown only so you can tell whether what they have already "
        "told you meets it. When it does, skip it too."
    ),
    "after_framework_question": (
        "they kept chatting after the questions ended and are still on the same issue. Reflect "
        "what they said, then ask this question word for word."
    ),
    "rewrite": (
        "your last draft could not stand, for the reason given. Write the reply again so it no "
        "longer does that."
    ),
}


def _meaning(key: str, value: object) -> list[str]:
    """The line that says what `key` means for the value it has this turn, if it has one."""
    meaning = _MEANING.get(key)
    if isinstance(meaning, dict):
        meaning = meaning.get(str(value))
    return [f"  means: {meaning}"] if meaning else []


def _line(key: str, value: object) -> list[str]:
    """A key, its value, and what that value means for this turn."""
    return [f"{key}: {value}", *_meaning(key, value)]


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
) -> str:
    """Format the metadata header for this turn.

    Every value is read from the composed turn snapshot, so the block describes what the
    database holds rather than what an in-memory copy was mutated to mid-request. `framework`,
    `candidate` and `recent_mani_replies` are what the framework content and the caller's own
    history add - all optional, so a turn with none of them still
    formats exactly as before.

    `framework` is the one already active; its current and next stage go in full. `candidate`
    is the framework code picks for the model, the one for an imminent action - its offer line
    goes in, so the offer draws on authored language rather than being improvised from the
    Framework Index's one-liner alone. Never both at once: a framework is
    either running or being considered, not both.

    `history` is the same window the caller already loads for the model's own conversation
    view - nothing new is fetched for it. Only Mani's own messages in it become recent_openers;
    the person's messages are read here but never surfaced back to the model as an "opener".
    """
    technique = ctx.technique
    # Named first because every stage_ask and offer_ask below is resolved from it, and named
    # `conversation_style` rather than `style` because `recent_styles` three lines down means
    # the response shape, which is a different thing entirely.
    lines: list[str] = _line("conversation_style", resolve_style(ctx))
    if safety_concern:
        # The deterministic screen heard something that may be a risk. The framework waits:
        # no stage question to relay, no offer to make, until the person is safe to go on.
        lines += _line("safety", "concern")
    if ctx.recent_crisis:
        lines += _line("recent_crisis", "yes")

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
    lines += _line("conversation_phase", phase)
    if not running and not clarification_used(history):
        lines += _line("clarification_available", "yes")
    if not running:
        # What the question is about while no stage decides it (muhammad, 2026-09-24): said
        # here, next to the message, because the style rule in the long prompt alone did not hold.
        focus = _QUESTION_FOCUS[resolve_style(ctx)]
        lines += _line("question_focus", focus)
    if offer_waiting:
        # Mani's last reply was an offer, and they typed rather than tapped.
        lines += _line("offer_waiting", "yes")
    question = None if safety_concern else _after_framework_question(history or [])
    if question:
        lines += _line("after_framework_question", question)

    # Told to the model as it is enforced: a first offer used to read "yes" here whatever the
    # count, and the code then dropped what the model had been told it could do.
    lines += _line("cooldown_passed", "yes" if cooldown_passed(ctx) else "no")
    if not safety_concern and not running:
        if closest_fit_due(ctx):
            lines += _line("closest_fit", "due")
        elif closest_fit_ok(ctx, urgent=urgent):
            lines += _line("closest_fit", "ok")
    if technique is not None:
        since_last = ctx.thread.message_count - technique.at_message_count
        lines += _line("since_last", since_last)
        lines += _line("this_thread", f"{technique.framework_id} ({technique.outcome})")
        if (
            technique.outcome is TechniqueOutcome.ACCEPTED
            and not technique.library_offered_since
        ):
            lines += _line("library_pending", "yes")
        if technique.phase:
            lines += _line("current_phase", technique.phase)

    if ctx.summary and ctx.summary.techniques_tried:
        tried = ", ".join(
            f"{t.name} ({'helpful' if t.helpful else 'not helpful'})"
            for t in ctx.summary.techniques_tried
        )
        lines += _line("history", tried)

    if ctx.recent_styles:
        styles = " → ".join(s.shape for s in ctx.recent_styles)
        lines += _line("recent_styles", styles)

    # A separate signal from recent_styles: that is the abstract shape, this is the
    # literal words a reply opened with - two replies can vary in shape while still starting
    # the same way, which is what "recent_styles" alone cannot catch.
    mani_replies = [m.content for m in (history or []) if m.role is MessageRole.MANI]
    openers = [
        _opener(text) for text in mani_replies[-RECENT_OPENERS_WINDOW:] if text.strip()
    ]
    if openers:
        quoted = ", ".join(f'"{o}"' for o in openers)
        lines += _line("recent_openers", quoted)

    if candidate is not None and not safety_concern and cooldown_passed(ctx):
        # The client's description is not here: the backend adds it to the offer, and a
        # model given the text copied it, so offers showed it twice.
        offer = _stage_lines("offer", candidate, "offering", resolve_style(ctx))
        lines += [offer[0], *_meaning("offer", "offering"), *offer[1:]]

    if running:
        style = resolve_style(ctx)
        if framework_starting:
            # They have just said yes. What they told Mani before this counts toward the first
            # stage; the note below says how to use it.
            lines += _line("framework_starting", "yes")
        lines += _line("active_framework", framework.id)
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
        lines.append(f"stage_note: {_stage_note(framework, style, starting=framework_starting)}")
        if 0 <= index < len(framework.phases) - 1:
            lines.extend(
                _stage_lines("next_stage", framework, framework.phases[index + 1], style)
            )
            later = [p for p in framework.phases[index + 2 :]]
            later = later[: next((i for i, p in enumerate(later) if p in ENDING_STAGES), len(later))]
            for position, phase in enumerate(later):
                lines.extend(_later_stage_lines(framework, phase, style, explain=position == 0))

    return "[ctx]\n" + "\n".join(lines) + "\n[/ctx]\n\n"


# A stage their words already answer is left unasked, with no check and no mention, and so are the
# stages after it that they answer too (muhammad, 2026-10-09). Which stages those are is the model's
# reading of each stage's ready_when, so the guidance for the stages after the next is in the block.
_WALK_THE_STAGES = (
    "Go through the stages in order, starting with this one. A stage that what they have already "
    "told you, here or in the Conversation Context, meets by its stage_ready_when is skipped "
    "without a word: never ask it, never check it with them, never say it is done. Do the same "
    "for the next stage and for each later_stage, until you reach one that is not met. Ask that "
    "stage's question, built from what they said in their own words so that it asks for the "
    "missing thing, and report that stage in state.step even when it is several ahead. Write "
    "this walk in stages_known first: for each stage, what they already said for it in their "
    "short words, and its status. known is not asked. partial asks only for the gap. confirm "
    "states what you have and asks whether it is right, only where the stage's own lines say to. "
    "missing is asked. The question asks only for what the stage's known does not hold yet, so it "
    "is precise: never ask again for a part they gave. Never say a stage's letter or name, and "
    "never say a stage was skipped or is done. Ask the question in your own tone, as the "
    "conversation flows, so it reads as the next natural thing to ask."
)

# A stage is a step, not an exam: it never needs complete or certain answers, and a person asked
# the same thing a third time feels interrogated (live, 2026-10-08: five times running).
_TWO_TRIES = (
    "If you have already asked for this stage's thing twice, take what they gave you and move to "
    "the next stage, unless stage_ready_when says to stay."
)

# Mani keeps the chosen style inside a framework: the stage decides what is asked, the style
# decides how it sounds.
_IN_STYLE = {
    "direct": "You are still Mani in Direct here: lead, keep it short and clear, and move them on.",
    "supportive": (
        "You are still Mani in Supportive here: warm and understanding, with no excessive "
        "reassurance, no repeated validation and no extra questions. Respond to what is "
        "meaningful in what they said, never their sentence handed back, then ask gently."
    ),
    "reflective": (
        "You are still Mani in Reflective here: help them look at what sits behind their answer, "
        "and reflect its meaning only when that opens something."
    ),
}

# What each style's question is about while no stage decides it. All three are about how one part
# is for the person (muhammad, 2026-10-09); the three differ in how far each reaches into it, so the
# styles do not ask the same question (Loli's test, 2026-10-09: two of them shared one).
_QUESTION_FOCUS = {
    "direct": "the heart of it",
    "supportive": "how it is for them",
    "reflective": "what sits behind it",
}


def _stage_note(framework: Framework, style: str, *, starting: bool) -> str:
    """How to take the stage in force: walk past what they already answered, then ask."""
    said = (
        "They have just said yes, so what they told you before it counts toward every stage. "
        if starting
        else "Put the question in terms of what they have told you, in their words; never send it bare. "
    )
    never = f"{framework.closing} is never skipped. " if framework.closing else ""
    return f"{said}{_WALK_THE_STAGES} {never}{_TWO_TRIES} {_IN_STYLE[style]}"


def _later_stage_lines(
    framework: Framework, phase: str, style: str, *, explain: bool
) -> list[str]:
    """A stage after the next: when it is met and the question that asks for it. What the lines
    mean is said once, on the first."""
    stage = framework.stages.get(phase) or {}
    lines = _line("later_stage", phase) if explain else [f"later_stage: {phase}"]
    if stage.get("ready_when"):
        lines.append(f"later_stage_ready_when: {stage['ready_when']}")
    if ask := (stage.get("ask") or {}).get(style):
        lines.append(f"later_stage_ask: {ask}")
    return lines


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
