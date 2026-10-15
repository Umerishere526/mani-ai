# ABOUTME: The hidden [ctx] block prefixed to the user's message for one turn only.
# ABOUTME: Built fresh from database state and never stored, so history cannot replay it.

from __future__ import annotations

import re

from mani.chat import repairs
from mani.chat.greeting import AFTER_FRAMEWORK_QUESTIONS, CLARIFICATION_QUESTIONS, CHAT_MORE_LABEL
from mani.chat.safety import normalize
from mani.db.threads import TurnContext
from mani.llm.schema import WorkingRead
from mani.models.rows import ENDING_STAGES, Framework, Message, MessageRole, TechniqueOutcome

# How many messages must pass before a technique may be offered again. After "Keep chatting"
# no offer comes in that reply or the two after it - the same framework or a different one,
# whichever fits then (muhammad, 2026-09-24). After a finished framework the wait is longer.
# The first offer never waits.
COOLDOWN_AFTER_DECLINE = 4
COOLDOWN_AFTER_COMPLETE = 45

# How many replies may ask one stage before the questions move on, whatever was answered. A
# stage is a step, not an exam: a person who cannot answer it is never asked it a third time.
MAX_STAGE_ASKS = 2

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
# How many of Mani's own recent questions are shown back to it. The model cannot count what it
# has asked, so asking the same thing in new words ran for several turns (2026-10-13: 33 of 36
# scripted conversations); seen in front of it, a question already asked is not asked again.
RECENT_QUESTIONS_WINDOW = 4


def _opener(text: str) -> str:
    """The first couple of words of a reply, lowercased - enough to name a repeated opening
    without exposing the reply itself in [ctx]."""
    return " ".join(text.split()[:RECENT_OPENERS_WORDS]).lower()

def _closing_question(text: str) -> str | None:
    """The last question a reply asked, as written, or None when it asked nothing."""
    asked = re.findall(r"[^.!?\n]*\?", text)
    return " ".join(asked[-1].split()) if asked else None


# How much of what they said back is shown beside each question: enough to carry the answer, not
# their whole message again.
ANSWER_SNIPPET_CHARS = 90


def _asked_and_answered(history: list[Message]) -> list[str]:
    """Mani's last few closing questions, each followed by what they typed in reply. The newest
    question has no reply in `history`: it is the message being answered this turn, which the
    model already has in front of it. A question answered with a button shows no answer: what
    they typed after the tap answers the next question, not this one."""
    pairs: list[str] = []
    for position, message in enumerate(history):
        question = _closing_question(message.content) if message.role is MessageRole.MANI else None
        if not question:
            continue
        reply = next((m for m in history[position + 1 :] if m.role is MessageRole.USER), None)
        typed = reply if reply and not reply.selected_prompt else None
        said = disarm(" ".join(typed.content.split()))[:ANSWER_SNIPPET_CHARS] if typed else None
        pairs.append(f'{question} (they said: "{said}")' if said else question)
    return pairs[-RECENT_QUESTIONS_WINDOW:]


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
    """Whether an offer may be made yet: the first never waits; after Keep chatting none comes
    in that reply or the two after it. [ctx] reports it, repairs.apply enforces it."""
    technique = ctx.technique
    if technique is None:
        return True
    return ctx.thread.message_count - technique.at_message_count >= cooldown_for(
        technique.outcome
    )


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
_MEANING: dict[str, str | dict[str, str]] = {
    "conversation_style": {
        "direct": (
            "Direct, for the whole conversation. Clear, concise and focused, never cold, abrupt, "
            "transactional or interrogative. A short line of your own that shows you got the "
            "point, then the question, never their sentence handed back. Get to the heart of it."
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
            "nothing has been offered yet. Work out what is going on for them. In reasoning, "
            "write what they have told you, then what you think is underneath if they have given "
            "you enough to build on, then the one thing it would help most to know next. Ask the "
            "one question a thoughtful listener would ask here, about the situation, the feeling, "
            "what it means to them, or what they do or hope for, whichever you know least. When "
            "they have said almost nothing, ask one gentle open question and make no guess yet. "
            "Say what you make of it before you ask only once you have something to say, as a "
            "possibility, and put a choice between two readings only when both come from what "
            "they said and the answer would tell you something you need. Never ask for something "
            "their message already answers, never a hypothetical such as what would it mean, and "
            "never tell them what they feel as a fact. A set that fits is offered only when "
            "another question would not change what you understand, and that is your next_move, "
            "never a count of messages."
        ),
        "framework": "the questions are running, so follow the stage.",
        "talking": (
            "an offer was declined or the questions finished, so talk with them, following "
            "what they say."
        ),
    },
    "question_focus": {
        "the heart of it": (
            "your open question is about what they want and what is in their way: what they would "
            "want to be different, or what they have already tried. Plain and short, never more "
            "facts about the event for their own sake."
        ),
        "how it is for them": (
            "your open question is about how this particular thing is for them: what it has "
            "changed in their days or their work, or what they make of how the other person acts. "
            "Gently, in their words, about the particulars. Never a general how is this affecting "
            "you, which the feeling they named already answers."
        ),
        "what sits behind it": (
            "your open question is about meaning: what the feeling says to them, or why it matters "
            "as much as it does. In plain words, and never the same question in other words."
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
        "yes": (
            "an offer may be made in this reply, when one fits and another question would not "
            "change what you understand."
        ),
        "no": "offer nothing in this reply.",
    },
    "since_last": "how many messages have passed since the last offer.",
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
    "working_read": (
        "what you made of them as of your last reply, slot by slot in the lines below. Whatever a "
        "read_ line holds is known: never ask for it again, in any words. read_feeling "
        "is their own word for how they feel, and it stays part of the read: tie it to what in "
        "their situation explains it when that helps, and bring it back when it does, not in every "
        "reply. read_since is how long it has gone on, as they said it; when it says not said, "
        "never assume it is recent and never add today or right now, and ask whether it is new or "
        "has been going on a while only when that would change the read. read_impact is what it "
        "is doing to them, read_response what they do about it and read_wants what they hope "
        "for, each only as they said it. A slot that is missing is something to listen for, "
        "never a question to put because it is empty: ask for one only when having it would "
        "change what you do next, one at a time, in plain words. read_underneath and "
        "read_unknown are yours and may be wrong. Take them further with what they just said, "
        "narrow them where they ruled a reading out, drop them where they said you are wrong. "
        "Never start a fresh read, and never open as though this turn were the first. When they "
        "answer with little, such as everything or I don't know, the read stays where it was, so "
        "go one layer under it rather than putting the same two readings to them again."
    ),
    "read_so_far": {
        "nothing yet": (
            "you have no read of them yet, so this is where you start. If what they have said is "
            "only a feeling or a few words, ask one gentle open question about what is behind it "
            "and make no guess. If they have told you a situation, a person or an event, you have "
            "something to build on and may say what you make of it, as a possibility."
        ),
    },
    "support_check": {
        "yes": (
            "you have a read of what is going on and have not yet asked whether they want to be "
            "heard or want help working it out. Ask it once, plainly and in your own words, when "
            "it fits, and set support to asked in that reply. Never again, and never when they "
            "have already said which."
        ),
    },
    "asked_and_answered": (
        "the questions you asked in your last few replies, newest last, each with what they said "
        "back. Each one is spent: do not ask it again, and do not ask it in other words, which is "
        "the same question. What they said back is known. Take it, and if they answered little or "
        "declined, go one layer under it to something you have not asked."
    ),
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
    "stage_asked": {
        "twice": (
            "you have asked this stage twice. Take what they gave you, even partial, loose or "
            "I don't know, and ask the next stage now."
        ),
    },
    "said_before_yes": (
        "what they told you before saying yes, in their words. Read every stage against it "
        "first: a stage it answers is said back as a possibility and checked, as stage_note "
        "says; a stage it partly answers asks only for the gap."
    ),
    "later_stage": (
        "a stage after the next one, shown only so you can tell whether what they have already "
        "told you answers it. When it does, that stage is checked with them when you reach it, "
        "one stage in a reply."
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
    if not running and not safety_concern and not (ctx.summary and ctx.summary.working_read):
        lines += _line("read_so_far", "nothing yet")
    # The client's focus line is for before Mani has any reading of them. Once it has one, the
    # line restarts the conversation instead of moving it on ("work and my life and everything"
    # was answered with "What would you like us to focus on today?", 2026-10-13).
    has_read = bool(ctx.summary and ctx.summary.working_read)
    if not running and not has_read and not clarification_used(history):
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
    offer_ok = cooldown_passed(ctx)
    lines += _line("cooldown_passed", "yes" if offer_ok else "no")
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

    if not safety_concern:
        lines += _read_lines(ctx.summary.working_read if ctx.summary else None)

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
    current = WorkingRead.stored(ctx.summary.working_read if ctx.summary else None)
    if (
        # Only once there is a picture and not just a topic: what it is doing to them. A
        # conclusion alone is not enough ("everything" is one), and neither is what they do about
        # it: "they make the changes" is a fact of the situation, and asking heard-or-help on it
        # cut the questions off on the third reply. On the first mention of a feeling the question
        # is an intake line, asked before Mani has anything to be helped or heard about.
        current and current.situation and current.impact
        and current.support == "not_asked" and not running and not safety_concern
    ):
        lines += _line("support_check", "yes")
    asked = _asked_and_answered(history or [])
    if asked and not running:
        lines += _line("asked_and_answered", " | ".join(asked))

    if candidate is not None and not safety_concern and offer_ok:
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
            said = _said_before_yes(history or [])
            if said:
                lines += _line("said_before_yes", said)
        lines += _line("active_framework", framework.id)
        lines.append(f"framework_stages: {', '.join(framework.phases)}")
        stage = _stage_lines("stage", framework, technique.phase, style)
        # The turn they say yes, a first stage their words already answer (by its ready_when) is
        # said back as a possibility and checked with them; otherwise its question is asked.
        index = framework.phase_index(technique.phase)
        if offer_waiting:
            # The offering stage's question is the offer they have just typed past.
            stage = [line for line in stage if not line.startswith("stage_ask:")]
        if framework_starting and technique.phase == "offering" and index + 1 < len(framework.phases):
            index += 1
            stage = _stage_lines("stage", framework, framework.phases[index], style)
        lines.extend(stage)
        if (
            not framework_starting
            and technique.stage_asks >= MAX_STAGE_ASKS
            and framework.may_skip(technique.phase)
        ):
            lines += _line("stage_asked", "twice")
        checks = (((framework.stages.get("offering") or {}).get("check") or {}).get(style)) or []
        if checks:
            lines.append(f"stage_check: {' | '.join(checks)}")
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


# A stage their words already answer is said back as a possibility and checked with them, one stage
# in a reply (muhammad, 2026-10-14). Which stages those are is the model's reading of each stage's
# ready_when, so the guidance for the stages after the next is in the block.
_WALK_THE_STAGES = (
    "Go through the stages in order, starting with this one. For each, work out what they have "
    "already told you for it, here, in the read_ lines or in the Conversation Context. A stage you "
    "have an answer for is not skipped and not asked for again: say what you understand for it, in "
    "your own plain words from what they said, as a possibility using the stage_confirm pattern, "
    "then check it with one of the stage_check lines, a different one each time, and set that "
    "stage's status to confirm. Never put it as settled and never as something you knew already. "
    "A stage you have nothing for is asked, built from what they said so that it asks for the "
    "missing thing, with status missing. Only ever one stage in a reply, the first not yet "
    "confirmed, and report it in state.step. Write this walk in stages_known first: for each "
    "stage, what they already said for it in their short words, and its status. known means they "
    "have confirmed it, so you go on to the next stage; confirm means you have an answer and are "
    "checking it now; partial asks only for the gap; missing is asked. The stage's own label is "
    "added for you ahead of your words, so never write it yourself. Never ask for a part they "
    "gave. Say it in your own tone, as the next natural thing to say."
)

# A stage is a step, not an exam: it never needs complete or certain answers, and a person asked
# the same thing a third time feels interrogated (live, 2026-10-08: five times running).
_TWO_TRIES = (
    "A loose or partial answer is enough: when what they gave touches this stage's thing, ask at "
    "most one more question for a fuller answer, then move on. If you have asked for this "
    "stage's thing twice, or they said they do not know, take what they gave you and move to the "
    "next stage."
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


def _read_lines(stored: str | None) -> list[str]:
    """The read carried from the last reply, one labelled line per slot, so the feeling they
    named and how long it has gone on are in front of the model every turn. A read stored
    before it had slots is shown as it was written. Disarmed: the slots hold their own words."""
    if not stored:
        return []
    read = WorkingRead.stored(stored)
    if read is None:
        return _line("working_read", disarm(" ".join(stored.split())))
    lines = _line("working_read", "carried from your last reply")
    slots = (
        ("read_situation", read.situation),
        ("read_feeling", ", ".join(read.feeling) if read.feeling else "none they named"),
        ("read_meaning", read.meaning),
        ("read_since", read.since or "not said"),
        ("read_impact", read.impact),
        ("read_response", read.response),
        ("read_wants", read.wants),
        ("read_support", {"not_asked": None, "asked": "asked, not answered yet"}.get(
            read.support, read.support)),
        ("read_underneath", read.underneath),
        ("read_unknown", read.unknown),
    )
    return lines + [f"{key}: {disarm(' '.join(str(value).split()))}" for key, value in slots if value]


# Their own messages before the yes, put beside the stages on the turn the questions start, so
# what they already said is judged against each stage rather than left far back in the history.
SAID_BEFORE_YES_MESSAGES = 6


def _said_before_yes(history: list[Message]) -> str:
    """Their last few messages before they said yes, oldest first, each disarmed like any of
    their words placed in the block.

    A tap is stored as a message whose content is the label, so the buttons they pressed are
    left out: "Direct" and "Try it" are not things the person said about their situation, and
    put beside the stages they read as if they were.
    """
    said = [
        disarm(" ".join(m.content.split()))
        for m in history
        if m.role is MessageRole.USER and m.content.strip() and not m.selected_prompt
    ]
    return " | ".join(said[-SAID_BEFORE_YES_MESSAGES:])


def _stage_note(framework: Framework, style: str, *, starting: bool) -> str:
    """How to take the stage in force: walk past what they already answered, then ask."""
    said = (
        "They have just said yes, so what they told you before it counts toward every stage. "
        if starting
        else "Put the question in terms of what they have told you, in their words; never send it bare. "
    )
    never = f"{framework.closing} is never skipped. " if framework.closing else ""
    said += (
        "The read_ lines are part of what they have already told you: read_situation answers an "
        "event, read_meaning a belief, and read_impact and read_response what followed from it. "
        "A stage they answer is checked with them and then gone on from, never asked for again. "
    )
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
    confirm = (stage.get("confirm") or {}).get(style)
    if confirm:
        lines.append(f"{prefix}_confirm: {confirm}")
    ask = (stage.get("ask") or {}).get(style)
    if ask:
        lines.append(f"{prefix}_ask: {ask}")
    return lines
