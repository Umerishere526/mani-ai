# ABOUTME: The hidden [ctx] block prefixed to the user's message for one turn only.
# ABOUTME: Built fresh from database state and never stored, so history cannot replay it.

from __future__ import annotations

import re

from mani.chat.greeting import CHAT_MORE_LABEL
from mani.chat.techniques import OFFERING, ledger_stages_of
from mani.db.threads import TurnContext
from mani.models.rows import (
    Framework,
    LedgerEntry,
    Message,
    MessageRole,
    StageStatus,
    TechniqueOutcome,
)
from mani.prompts.composer import tried_line
from mani.prompts.replies import Replies
from mani.prompts.tuning import Tuning

# The greeting, the style they tapped, and that style's opener.
OPENING_MESSAGES = 3


# Every key a [ctx] line may carry. Each one's meaning is said once, in response_format.md's `ctx`
# section, and a test ties the two together in both directions, so the code sends only keys and
# values and never a sentence of instruction.
CTX_KEYS = frozenset({
    "conversation_style", "safety", "recent_crisis", "conversation_phase",
    "clarification_lines", "question_focus", "offer_waiting",
    "after_framework_questions", "cooldown_passed", "since_last", "this_thread",
    "library_pending", "current_phase", "history", "recent_styles", "recent_openers",
    "ruled_out", "framework_starting", "active_framework",
    "framework_stages", "stage", "stage_ledger",
})


def _line(key: str, value: object) -> str:
    """One [ctx] line. A key the prompt does not explain is refused, so none can reach the model."""
    if key not in CTX_KEYS:
        raise ValueError(f"[ctx] key {key!r} is not in CTX_KEYS")
    return f"{key}: {value}"


def _opener(text: str, words: int) -> str:
    """The first couple of words of a reply, lowercased - enough to name a repeated opening
    without exposing the reply itself in [ctx]."""
    return " ".join(text.split()[:words]).lower()

def _ledger_value(stages: list[str], ledger: dict[str, LedgerEntry]) -> str:
    """Every ledger stage in order with its status, a stage the ledger has no entry for as missing."""
    return ", ".join(
        f"{stage} {ledger[stage].status if stage in ledger else StageStatus.MISSING}"
        for stage in stages
    )


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


def _chat_more_offered(history: list[Message]) -> bool:
    """Whether a framework has ended in the history window: a reply of Mani's offered Chat More.

    A framework ends on the reply that offers it. Once that reply has scrolled out of the history
    window the conversation has moved on, and the questions that follow it are no longer offered.
    """
    return any(
        str(option.get("label", "")).lower() == CHAT_MORE_LABEL.lower()
        for message in history
        if message.role is MessageRole.MANI
        for option in message.prompt_options or []
    )


def clear_cooldown_for(outcome: TechniqueOutcome, tuning: Tuning) -> int:
    return (
        tuning.offers.cooldown_after_complete
        if outcome is TechniqueOutcome.ACCEPTED
        else tuning.offers.clear_cooldown_after_decline
    )


def _their_messages(ctx: TurnContext) -> int:
    """How many messages the person has sent. The reply to their Nth is written at 3 + 2(N - 1)."""
    return (ctx.thread.message_count - OPENING_MESSAGES) // 2 + 1


def cooldown_passed(ctx: TurnContext, tuning: Tuning) -> bool:
    """Whether an offer may be made yet: [ctx] tells the model, which keeps to it."""
    technique = ctx.technique
    if technique is None:
        return _their_messages(ctx) >= tuning.offers.clear_offer_after
    return ctx.thread.message_count - technique.at_message_count >= clear_cooldown_for(
        technique.outcome, tuning
    )


def resolve_style(ctx: TurnContext, default_style: str) -> str:
    """The conversation style this turn, named in [ctx].

    The conversation's own choice wins over the profile's, which is the point of having
    both: onboarding sets a default, and a thread may differ from it without changing it.
    """
    if ctx.thread.conversation_style:
        return ctx.thread.conversation_style.value
    if ctx.profile and ctx.profile.support_style:
        return ctx.profile.support_style.value
    return default_style


def build(
    ctx: TurnContext,
    *,
    framework: Framework | None = None,
    history: list[Message] | None = None,
    safety_concern: bool = False,
    offer_waiting: bool = False,
    framework_starting: bool = False,
    ruled_out: list[str] | None = None,
    replies: Replies,
    tuning: Tuning,
) -> str:
    """Format the metadata header for this turn.

    Every value is read from the composed turn snapshot, so the block describes what the
    database holds rather than what an in-memory copy was mutated to mid-request. `framework` and
    `history` are what the framework content and the caller's own history add - both optional, so a
    turn with neither still formats exactly as before.

    `framework` is the one already active; its current stage goes in by id, with what is known of
    each stage before the last, since the model reads what each stage asks from the framework's
    Stages line in the index, and what the ending stages ask from the mani_base prompt's `ending`
    section.

    `history` is the same window the caller already loads for the model's own conversation
    view - nothing new is fetched for it. Only Mani's own messages in it become recent_openers;
    the person's messages are read here but never surfaced back to the model as an "opener".

    `ruled_out` is the frameworks what they have said rules out. It is told to the model while no
    framework runs.
    """
    technique = ctx.technique
    style = resolve_style(ctx, tuning.offers.default_style)
    # Named first because the model writes every stage question in it, and named
    # `conversation_style` rather than `style` because `recent_styles` three lines down means
    # the response shape, which is a different thing entirely.
    lines: list[str] = [_line("conversation_style", style)]
    if safety_concern:
        # The deterministic screen heard something that may be a risk. The framework waits:
        # no stage question to relay, no offer to make, until the person is safe to go on.
        lines.append(_line("safety", "concern"))
    if ctx.recent_crisis:
        lines.append(_line("recent_crisis", "yes"))

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
    lines.append(_line("conversation_phase", phase))
    if not running:
        lines.append(_line("clarification_lines", " | ".join(replies.clarification_lines)))
    if not running:
        # What the question is about while no stage decides it (muhammad, 2026-09-24): said
        # here, next to the message, because the style rule in the long prompt alone did not hold.
        focus = "feeling_then_way_through" if style == "direct" else "feelings"
        lines.append(_line("question_focus", focus))
    if offer_waiting:
        # Mani's last reply was an offer, and they typed rather than tapped.
        lines.append(_line("offer_waiting", "yes"))
    if not safety_concern and _chat_more_offered(history or []):
        questions = " | ".join(replies.after_framework_questions)
        lines.append(_line("after_framework_questions", questions))

    # The offer's timing is told to the model, which keeps to it.
    passed = cooldown_passed(ctx, tuning)
    lines.append(_line("cooldown_passed", "yes" if passed else "no"))
    if technique is not None:
        since_last = ctx.thread.message_count - technique.at_message_count
        lines.append(_line("since_last", since_last))
        lines.append(_line("this_thread", f"{technique.framework_id} ({technique.outcome})"))
        if (
            technique.outcome is TechniqueOutcome.ACCEPTED
            and not technique.library_offered_since
        ):
            lines.append(_line("library_pending", "yes"))
        if technique.phase:
            lines.append(_line("current_phase", technique.phase))

    if ctx.summary and ctx.summary.techniques_tried:
        lines.append(_line("history", tried_line(ctx.summary.techniques_tried)))

    if ctx.recent_styles:
        styles = " → ".join(s.shape for s in ctx.recent_styles)
        lines.append(_line("recent_styles", styles))

    # A separate signal from recent_styles: that is the abstract shape, this is the
    # literal words a reply opened with - two replies can vary in shape while still starting
    # the same way, which is what "recent_styles" alone cannot catch.
    mani_replies = [m.content for m in (history or []) if m.role is MessageRole.MANI]
    windows = tuning.windows
    openers = [
        _opener(text, windows.recent_openers_words)
        for text in mani_replies[-windows.recent_openers_window:]
        if text.strip()
    ]
    if openers:
        quoted = ", ".join(f'"{o}"' for o in openers)
        lines.append(_line("recent_openers", quoted))

    if ruled_out and not running and not safety_concern:
        lines.append(_line("ruled_out", ", ".join(ruled_out)))

    if running:
        if framework_starting:
            # They have just said yes. What they told Mani before this counts toward the first
            # stage; response_format.md says how to use it.
            lines.append(_line("framework_starting", "yes"))
        lines.append(_line("active_framework", framework.id))
        lines.append(_line("framework_stages", ", ".join(framework.phases)))
        phase = technique.phase
        index = framework.phase_index(phase)
        if framework_starting and phase == OFFERING and index + 1 < len(framework.phases):
            # The ledger is empty on the turn they say yes: the first stage is the one to judge.
            phase = framework.phases[index + 1]
        stages = ledger_stages_of(framework)
        # What is known of each stage is told while the questions run and while an offer waits to be
        # answered; from the last own phase on it is frozen and no longer asked.
        if phase in stages or (
            technique.phase == OFFERING
            and (offer_waiting or framework_starting or technique.outcome is TechniqueOutcome.ACCEPTED)
        ):
            lines.append(_line("stage_ledger", _ledger_value(stages, technique.stage_ledger)))
        lines.append(_line("stage", phase))

    return "[ctx]\n" + "\n".join(lines) + "\n[/ctx]\n\n"
