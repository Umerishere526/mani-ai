# ABOUTME: One user message from arrival to stored reply: context, one model call, writes.
# ABOUTME: Everything it writes lands in the caller's transaction, or none of it does.

from __future__ import annotations

import dataclasses
import logging
import re
import uuid
from dataclasses import dataclass, field

import asyncpg

from mani.auth.jwt import Claims
from mani.chat import context, repairs, router, safety, semantic_router
# `offer` is a local variable in send() for the offer awaiting an answer, so the module that
# decides whether to make one is imported under a name that cannot be shadowed by it.
from mani.chat import offer as offer_policy
from mani.chat.greeting import (
    CHAT_MORE_LABEL,
    EXPLAIN_LABEL,
    GO_TO_LIBRARY_LABEL,
    OPENERS,
    STYLE_OPTIONS,
    greeting,
)
from mani.chat.techniques import SOMATIC_STAGES, STUCK_BRANCH, Registry
from mani.config import get_settings
from mani.db import (
    exercises as exercises_db,
    llm_calls,
    messages as messages_db,
    outcomes,
    profiles,
    summaries,
    threads,
)
from mani.errors import ErrorCategory, ServiceError
from mani.llm import client
from mani.llm.schema import LibrarySection, Reply, SmartPrompt
from mani.models.rows import (
    Exercise,
    Framework,
    Message,
    MessageRole,
    ResponseStyle,
    SupportStyle,
    TechniqueOutcome,
    TechniqueState,
    Thread,
)
from mani.prompts import cache, composer

logger = logging.getLogger(__name__)

# Title generation is asked for once the thread has a real exchange behind it. The
# reference tested `message_count == 3` exactly, so a single crisis turn - which writes
# one message rather than two - moved the count past 3 and the thread was never titled.
TITLE_AFTER_MESSAGES = 3

# How many new messages accumulate before the rolling summary is refreshed. Tied to the
# history window rather than set beside it: any value above the window leaves messages that
# have scrolled out of the history the model sees and are not yet in the summary either.
SUMMARY_THRESHOLD = messages_db.CONTEXT_WINDOW

_HANDOFF_LABELS = {CHAT_MORE_LABEL.lower(), GO_TO_LIBRARY_LABEL.lower()}

# The client's two questions that end a framework: what next once the check-in is answered,
# and the same choice when they decline it.
_ASKS_WHAT_NEXT = re.compile(
    r"what would you like to do (next|now)|keep chatting or go to the library", re.IGNORECASE
)


def _handoff() -> list[SmartPrompt]:
    return [
        SmartPrompt(label=CHAT_MORE_LABEL),
        SmartPrompt(label=GO_TO_LIBRARY_LABEL, library=LibrarySection.HOME.value),
    ]


def _awaiting_place(history: list[Message]) -> bool:
    """Whether Mani's last reply asked where in the body they feel it, and it is unanswered."""
    last = next((m for m in reversed(history) if m.role is MessageRole.MANI), None)
    return bool(last and any(
        str(o.get("label", "")) == repairs.PLACE_LABELS[0] for o in (last.prompt_options or [])
    ))


def _body_route_step(
    fixed: repairs.Repaired,
    framework_id: str,
    stages: dict,
    style: str,
    content: str,
    previous_phase: str | None,
    awaiting_place: bool,
) -> repairs.Repaired:
    """The turns around the one body question (spec 0011, AC-10, AC-11): where they feel it, then
    the practice for that place.

    The reply that ends the questions goes straight to the practice when their answer already
    named a place; otherwise the check-in block asks where. After that question a place gets its
    practice, and an answer naming none gets one plainer try with the same buttons. "Nothing", a
    decline, or a second answer naming no place ends the route with the client's decline line and
    the two choices, set here rather than left to the model's wording, so nobody is asked a third
    time or left with nothing to tap.
    """
    first_answer = previous_phase == "somatic_checkin"
    second_answer = previous_phase == "somatic_practice" and awaiting_place
    ending_turn = previous_phase not in SOMATIC_STAGES and fixed.phase == "somatic_checkin"
    if not (first_answer or second_answer or ending_turn):
        return fixed
    stage = stages.get("somatic_practice") or {}
    safety_reply = next(
        (repairs.reply_for(b, style) for b in stage.get("if_unclear") or [] if "pain" in b.get("when", "")),
        None,
    )
    if safety_reply and safety_reply in fixed.text:
        return fixed
    place = repairs.place_answer(content)
    practice = repairs.practice_for(stage, place, style) if place else None
    if ending_turn:
        if practice is None:
            # The check-in block asks where.
            return fixed
        bridge = repairs.without_questions(fixed.text)
        text, labels = practice
        text = "\n\n".join(part for part in (bridge, text) if part)
    elif practice is not None:
        text, labels = practice
    elif repairs.declines_or_acts(content) or repairs.feels_nothing(content) or second_answer:
        decline = repairs.decline_reply(stages.get("somatic_checkin") or {}, style)
        return dataclasses.replace(
            fixed,
            text=decline or fixed.text,
            framework_id=framework_id,
            phase="somatic_practice",
            prompts=_handoff(),
        )
    elif repairs.practice_in(stage, fixed.text, style):
        text, labels = fixed.text, []
    else:
        script = (stage.get("ask") or {}).get(style)
        if not script:
            return fixed
        text = repairs.with_the_check_in(repairs.first_sentence(fixed.text), script)
        labels = list(repairs.PLACE_LABELS)
    return dataclasses.replace(
        fixed,
        text=text,
        framework_id=framework_id,
        phase="somatic_practice",
        prompts=[SmartPrompt(label=label) for label in labels],
    )


def _offered_handoff(history: list[Message]) -> bool:
    """Whether Mani's last reply already put the two choices in front of them."""
    last = next((m for m in reversed(history) if m.role is MessageRole.MANI), None)
    return bool(last and any(
        str(o.get("label", "")).lower() in _HANDOFF_LABELS for o in (last.prompt_options or [])
    ))


@dataclass(frozen=True)
class Turn:
    """What the endpoint sends back."""

    message_id: uuid.UUID | None
    content: str
    created_at: object
    prompts: list[SmartPrompt] = field(default_factory=list)
    title: str | None = None
    crisis_detected: bool = False
    crisis_blocks_chat: bool = True
    was_duplicate: bool = False
    needs_summary: bool = False
    llm_call_id: uuid.UUID | None = None
    # Present only when AI_DEBUG_MODE is on; never sent to an ordinary client.
    reasoning: str | None = None
    # Set only on the turn a framework completes, and only when the catalog has a
    # matching exercise. A row model, not the wire shape - the router builds ExerciseOut
    # (and signs the audio URL) when it serializes this.
    exercise: Exercise | None = None


def find_tapped_prompt(history: list[Message], content: str) -> SmartPrompt | None:
    """Whether this message is a tap on a button Mani offered last turn.

    There is no button id on the wire, so a tap is a text match against the options on
    the most recent Mani message that carried any. The reference matched against the
    most recent Mani message *full stop*, so a plain reply in between made every later
    accept or decline evaluate a stale offer.
    """
    typed = content.strip().lower()
    if not typed:
        return None

    for option in _last_offered(history):
        label = str(option.get("label", "")).strip().lower()
        if label and label == typed:
            return SmartPrompt.model_validate(option)
    return None


def chosen_style(history: list[Message], content: str) -> SupportStyle | None:
    """The style this message picks, when it is a tap on one of the greeting's style buttons.

    Read from the stored options rather than through SmartPrompt: `style` is a greeting-only
    key the model is never asked for, so it is not part of the reply schema at all.
    """
    typed = content.strip().lower()
    for option in _last_offered(history):
        if option.get("style") and str(option.get("label", "")).strip().lower() == typed:
            return SupportStyle(option["style"])
    return None


def pending_offer(history: list[Message]) -> SmartPrompt | None:
    """The technique button still awaiting an answer, if there is one."""
    for option in _last_offered(history):
        if option.get("technique"):
            return SmartPrompt.model_validate(option)
    return None


def _last_offered(history: list[Message]) -> list[dict]:
    """The buttons under Mani's most recent message, which may be none."""
    for message in reversed(history):
        if message.role is MessageRole.MANI:
            return message.prompt_options or []
    return []


def _decided_framework(
    reported: str | None, outcome: TechniqueOutcome | None, live: TechniqueState | None
) -> str | None:
    """Which framework this turn's outcome belongs to, when there is one to record.

    Normally the one the model reported. A decline is the exception: once the person says no
    there is no technique left to report, so state: null is the model following the schema,
    and the decline belongs to the offer that was live.
    """
    if outcome is None:
        return None
    if reported:
        return reported
    if outcome is TechniqueOutcome.DECLINED and live is not None:
        return live.framework_id
    return None


def _finished(technique: TechniqueState | None) -> bool:
    """A framework they completed: accepted, with its phase cleared on retirement."""
    return bool(technique and technique.outcome is TechniqueOutcome.ACCEPTED and not technique.phase)


def stuck_offer_candidate(
    ctx: threads.TurnContext,
    registry: Registry,
    history: list[Message],
    user_texts: list[str],
) -> Framework | None:
    """The framework whose offer lines go into [ctx] on the turn right after Mani asked "Are you
    feeling stuck?", so a yes can be met in its words. None while a framework is offered or
    running, when no offer is allowed, or when their words rule it out."""
    mani_texts = [m.content for m in history if m.role is MessageRole.MANI]
    stuck_id = router.stuck_framework(registry.activations)
    technique = ctx.technique
    if stuck_id is None or not router.asked_the_check(mani_texts[-1:]):
        return None
    if technique is not None and technique.outcome is not TechniqueOutcome.DECLINED:
        return None
    if router.vetoes(registry.activations.get(stuck_id) or {}, user_texts):
        return None
    if context.offer_refusal(ctx, history) is not None:
        return None
    return registry.get(stuck_id)


def _separates_as_text(registry: Registry, separates: tuple[str, str]) -> str:
    """What two plausible frameworks are each for, in plain words.

    The model is never given a framework id to ask about - it is given the difference, so the
    question it asks sounds like a person wondering, not a system narrowing a list.
    """
    parts = []
    for framework_id in separates:
        framework = registry.get(framework_id)
        activation = (registry.activations or {}).get(framework_id) or {}
        central = " ".join((activation.get("central_indication") or "").split())
        if central:
            parts.append(central.rstrip("."))
        elif framework is not None:
            parts.append(framework.name)
    return " ... or ... ".join(parts)


# How many things to put in front of the model on an assessment turn. More than this and the
# list reads as a questionnaire to work through rather than a choice of what matters most.
MAX_TO_FIND_OUT = 5


def _to_find_out(registry: Registry, shortlist: tuple[str, ...]) -> tuple[str, ...]:
    """What the nearest sets of questions still need to know, in the frameworks' own words.

    Ordered by the shortlist, so the likeliest framework's needs come first, and de-duplicated
    across them: several frameworks want the event that set it off, and it is one question.
    Nothing is scripted here - these are what to find out, not what to say.
    """
    seen: set[str] = set()
    wanted: list[str] = []
    for framework_id in shortlist:
        activation = (registry.activations or {}).get(framework_id) or {}
        for item in activation.get("to_find_out") or []:
            key = " ".join(item.lower().split())
            if key not in seen:
                seen.add(key)
                wanted.append(" ".join(item.split()))
    return tuple(wanted[:MAX_TO_FIND_OUT])


def _conversation(history: list[Message]) -> list[dict[str, str]]:
    return [
        {
            "role": "user" if m.role is MessageRole.USER else "assistant",
            "content": context.disarm(m.content) if m.role is MessageRole.USER else m.content,
        }
        for m in history
    ]


async def send(
    conn: asyncpg.Connection,
    claims: Claims,
    thread_id: uuid.UUID | str,
    content: str,
    client_message_id: uuid.UUID | str | None = None,
) -> Turn:
    """Run one turn. The connection is already scoped to the caller and in a transaction."""
    settings = get_settings()
    user_id = claims.user_id

    if client_message_id is not None:
        # Held until this turn's transaction ends. A retry arriving while the first request
        # is still waiting on the model blocks here, then finds the stored pair below -
        # instead of passing the check alongside it, paying for a second generation, and
        # colliding on the unique key.
        await conn.execute(
            "select pg_advisory_xact_lock(hashtextextended($1, 0))",
            f"{user_id}:{client_message_id}",
        )
        existing = await messages_db.find_pair_by_client_id(
            conn, user_id, client_message_id
        )
        if existing is not None:
            user_message, reply_message = existing
            if str(user_message.thread_id) != str(thread_id):
                # The key is per person, not per conversation: answering here would hand
                # back a reply from a different chat and write nothing to this one.
                raise ServiceError(
                    f"client_message_id {client_message_id} already used in thread "
                    f"{user_message.thread_id}",
                    ErrorCategory.CONFLICT,
                    user_message="That message was already sent in another conversation.",
                )
            thread = await threads.get(conn, thread_id, user_id)
            return Turn(
                message_id=reply_message.id if reply_message else None,
                content=reply_message.content if reply_message else "",
                created_at=reply_message.created_at if reply_message else None,
                prompts=[
                    SmartPrompt.model_validate(p)
                    for p in (reply_message.prompt_options or [])
                ]
                if reply_message
                else [],
                title=thread.title if thread else None,
                crisis_detected=bool(thread and thread.crisis_detected),
                crisis_blocks_chat=settings.crisis_blocks_chat,
                was_duplicate=True,
            )

    ctx = await threads.load_turn_context(conn, thread_id, user_id)
    if ctx is None:
        raise ServiceError(
            f"thread {thread_id} not found for user {user_id}",
            ErrorCategory.NOT_FOUND,
            user_message="That conversation is not available.",
        )

    if ctx.thread.crisis_detected and settings.crisis_blocks_chat:
        raise ServiceError(
            f"thread {thread_id} is locked by a crisis flag",
            ErrorCategory.FORBIDDEN,
            user_message="This conversation is paused. Please reach out for support.",
        )

    config = await cache.load()
    history = await messages_db.recent_for_context(conn, thread_id, user_id)
    updates = threads.ThreadUpdates()

    style = chosen_style(history, content)
    if style is not None:
        return await _open_in_style(conn, ctx, content, style, client_message_id)

    technique = ctx.technique
    # A technique that reached its last phase and was accepted is finished. The row is
    # retired rather than removed, and the snapshot keeps it with its phase cleared, so
    # this turn's [ctx] reports the cooldown the completion just started instead of
    # reporting that nothing has ever run.
    retiring_framework_id: str | None = None
    # On the turn that retires a framework, the place whose practice Mani's last reply gave, if it
    # gave one: this turn's message is then how they feel after it (spec 0010, AC-7, AC-8).
    practiced_place: str | None = None
    if (
        technique is not None
        and technique.outcome is TechniqueOutcome.ACCEPTED
        and config.registry.is_final(technique.framework_id, technique.phase)
        and not _awaiting_place(history)
    ):
        retiring_framework_id = technique.framework_id
        last_reply = next((m.content for m in reversed(history) if m.role is MessageRole.MANI), None)
        practiced_place = repairs.practice_place(
            config.registry.get(retiring_framework_id).stages.get("somatic_practice") or {},
            last_reply,
            context.resolve_style(ctx),
        )
        updates.retire_technique = True
        ctx = dataclasses.replace(
            ctx, technique=technique.model_copy(update={"phase": None})
        )
        technique = None

    # From here on `technique` means the framework that is live on this turn: offered and
    # awaiting an answer, or accepted and mid-way. A row that is finished (phase cleared) or
    # declined stays in the snapshot, because [ctx] measures the cooldown from it - but it
    # is not running, so it must not strip technique buttons or keep the router switched off.
    if technique is not None and (
        technique.phase is None
        or technique.outcome not in (TechniqueOutcome.OFFERED, TechniqueOutcome.ACCEPTED)
    ):
        technique = None

    tapped = find_tapped_prompt(history, content)
    offer = pending_offer(history)
    offered_now = list(ctx.techniques_offered)
    outcome = technique.outcome if technique else None
    accepted_this_turn = False

    if tapped and tapped.technique and tapped.technique in config.registry:
        outcome = TechniqueOutcome.ACCEPTED
        accepted_this_turn = True
        offered_now.append(tapped.technique)
    elif (
        tapped
        and tapped.decline
        and offer
        and outcome is TechniqueOutcome.OFFERED
    ):
        outcome = TechniqueOutcome.DECLINED

    # Free text answering a live offer cannot be read here; the model reports it in
    # state.accepted, so the decision waits. The reference resolved it as a decline,
    # which silently shortened the cooldown on every ambiguous turn.
    deferred = offer is not None and tapped is None and outcome is TechniqueOutcome.OFFERED

    # The deterministic screen runs on every turn, before the model is asked anything. It
    # costs nothing and cannot be skipped for budget reasons. Crisis short-circuits the model
    # call entirely; concern only suppresses the router below, so the model still answers.
    assessment = safety.screen(content)
    if assessment.level is safety.Level.CRISIS:
        return await _handle_crisis(
            conn, ctx, content,
            reason=f"safety screen: {assessment.category.value if assessment.category else 'unspecified'}",
            reply_text=safety.protocol_for(assessment.category),
            tapped=tapped, client_message_id=client_message_id, settings=settings,
            updates=updates,
        )

    # Read by the router below and by the capsule repair further down, which needs everything
    # they have said rather than only this turn.
    user_texts = [m.content for m in history if m.role is MessageRole.USER] + [content]

    # An action about to happen is the one case decided before the model is asked: DBT STOP's
    # own offer lines go into [ctx], since waiting a turn may be too late. Every other choice is
    # the model's (spec 0010).
    urgent = router.urgent(user_texts)
    candidate = (
        config.registry.get(router.URGENT_FRAMEWORK)
        if urgent and technique is None and assessment.level is safety.Level.NONE
        else None
    )
    stuck_offer = (
        stuck_offer_candidate(ctx, config.registry, history, user_texts)
        if candidate is None and assessment.level is safety.Level.NONE
        else None
    )
    stuck_candidate = stuck_offer is not None
    if stuck_offer is not None:
        candidate = stuck_offer

    # Why no new offer may stand this turn, told to the model and enforced on its reply.
    refusal = context.offer_refusal(
        ctx, history, urgent=urgent, safety_concern=assessment.blocks_framework
    )

    # Routing on meaning, and the offer decided in code rather than by the model. Behind a flag:
    # with it off the model chooses, exactly as before.
    decision: offer_policy.Decision | None = None
    if settings.semantic_router:
        running_now = technique is not None and outcome is TechniqueOutcome.ACCEPTED
        # "yeah" has no routing signal, and embedding it produces a confident-looking vector
        # for nothing, so routing is skipped on a tap, a reply asking only to be heard, and
        # under any concern. A short message is skipped only when it answers a question Mani
        # asked: "I am depressed" is three words and is the whole reason they are here, and
        # treating it as an answer left the conversation unroutable (muhammad, 2026-10-06).
        # Their first message answers nothing: the only question behind it is the greeting's,
        # which asks how they want to be spoken to, not what is going on. From their second
        # message on, a short reply is an answer to what Mani just asked and carries no
        # routing signal of its own.
        answering_a_question = (
            context.classify_reply(content) == "short" and context.their_messages(history) > 1
        )
        routing_result = (
            semantic_router.route(user_texts)
            if not running_now
            and assessment.level is safety.Level.NONE
            and not assessment.blocks_framework
            and tapped is None
            and context.classify_reply(content) != "heard"
            and not answering_a_question
            else semantic_router.NO_MATCH
        )
        vetoed_ids = frozenset(
            framework_id
            for framework_id, activation in config.registry.activations.items()
            if router.vetoes(activation, user_texts)
        )
        decision = offer_policy.decide(
            routing_result,
            style=context.resolve_style(ctx),
            their_messages=context.their_messages(history),
            cooldown_passed=refusal is None,
            safety_concern=assessment.blocks_framework,
            their_last=context.classify_reply(content) if not tapped else None,
            framework_running=running_now,
            accepted_this_turn=accepted_this_turn,
            finishing=False,
            vetoed=vetoed_ids,
            clarified_already=context.asked_which_fits(history),
            # Where a conversation that never resolves to a framework goes, from the content:
            # the file that sets `stuck_offer` (ABCDE).
            fallback=router.stuck_framework(config.registry.activations),
        )
        logger.info(
            "thread %s routed %s, decided %s (%s)",
            ctx.thread.id, routing_result.status.value, decision.action.value, decision.why,
        )
        if decision.offers and decision.framework_id and refusal is None:
            candidate = config.registry.get(decision.framework_id)
        elif decision.separates:
            decision = dataclasses.replace(
                decision,
                separates_as_text=_separates_as_text(config.registry, decision.separates),
            )
        elif decision.action is offer_policy.Action.ASSESS:
            decision = dataclasses.replace(
                decision,
                to_find_out=_to_find_out(config.registry, decision.shortlist),
            )
    # They asked to hear more about the offer waiting for them: a tap on Tell me more, or a
    # question typed past it. The explanation then stands alone with two choices.
    explaining = (
        config.registry.get(offer.technique)
        if offer is not None and (
            (tapped is not None and tapped.label.strip().lower() == EXPLAIN_LABEL.lower())
            or (deferred and "?" in content)
        )
        else None
    )
    wants_title = (
        ctx.thread.message_count >= TITLE_AFTER_MESSAGES and not ctx.thread.title
    )
    system = composer.compose(
        config,
        ctx.profile,
        should_generate_title=wants_title,
        offered=offered_now,
        summary=ctx.summary,
        memory=ctx.memory,
    )
    model, parameters, routing = composer.model_settings(config)

    # They are passing the question over rather than answering it. Read before the model is
    # asked, so the reply is written knowing the step is being left rather than pressed again.
    skipped = bool(
        technique is not None
        and outcome is TechniqueOutcome.ACCEPTED
        and technique.phase not in SOMATIC_STAGES
        # Read from the words alone, so a "Skip this one" button already stored on an open
        # thread still skips when tapped.
        and repairs.skips_the_step(content)
    )

    # They asked Mani something, typed: answered first, whether it came past a waiting offer or
    # in the middle of the questions, where it holds the step without spending its one more
    # attempt (spec 0011, AC-2, AC-19).
    their_question = bool(
        tapped is None
        and "?" in content
        # "What do you mean?" asks for the question again, which has its own path.
        and not context.asks_to_hear_again(content)
        and (
            (explaining is not None)
            or (
                technique is not None
                and outcome is TechniqueOutcome.ACCEPTED
                and technique.phase not in SOMATIC_STAGES
                and not accepted_this_turn
                and not skipped
            )
        )
    )

    active_framework = config.registry.get(technique.framework_id) if technique else None
    prefix = context.build(
        ctx, framework=active_framework, candidate=candidate,
        history=history, safety_concern=assessment.blocks_framework, offer_waiting=deferred,
        framework_starting=accepted_this_turn, stuck_candidate=stuck_candidate,
        refusal=refusal, explaining=explaining, decision=decision, skipped=skipped,
        their_question=their_question,
        answering_practice=practiced_place is not None,
        # A tap is a choice among Mani's own buttons, not words to read.
        their_last=None if tapped else context.classify_reply(content),
        asked_again=None if tapped else context.asks_to_hear_again(content),
    )
    for_model = (
        f'User tapped the button: "{tapped.label}".'
        if tapped
        else context.disarm(content)
    )

    # Checked here, right before the only paid step, so the safety screen and the free style
    # opener come first and are never refused.
    if settings.daily_message_limit:
        sent = await messages_db.count_from_user_since(conn, user_id, hours=24)
        if sent >= settings.daily_message_limit:
            raise ServiceError(
                f"user {user_id} reached the daily limit of {settings.daily_message_limit}",
                ErrorCategory.RATE_LIMITED,
                retryable=True,
                user_message="You've reached today's message limit. Please come back tomorrow.",
            )

    call = await client.complete(
        [{"role": "system", "content": system.text}]
        + _conversation(history)
        + [{"role": "user", "content": prefix + for_model}],
        Reply,
        model=model,
        purpose=llm_calls.Purpose.CHAT,
        temperature=parameters.get("temperature", client.DEFAULT_TEMPERATURE),
        max_tokens=parameters.get("maxTokens", client.DEFAULT_MAX_TOKENS),
        reasoning_effort=parameters.get("reasoning_effort"),
        routing=routing,
        user_id=user_id,
        thread_id=ctx.thread.id,
        prompt_version_id=None,
    )
    reply = call.value

    # The model's own crisis judgment no longer locks the thread: a small model over-fires it
    # on ordinary distress, pain or injury. Only the deterministic screen (safety.screen, above)
    # locks. A model-reported crisis is kept as a non-locking concern - logged, and the framework
    # held off this turn - so a genuine novel phrasing still gets careful handling without
    # cutting off the conversation the person came for.
    flagged = reply.crisis is not None
    flag_kind = safety.flag_kind(reply.crisis.category) if reply.crisis is not None else None
    # Only a flag that is not `other` pauses anything; `other` is a reply with no flag.
    model_concern = flagged and safety.flag_pauses(reply.crisis.category)
    if flagged:
        # The kind only: the model's `reason` is a summary of what the person said.
        logger.info("model flagged a safety concern on thread %s: %s", ctx.thread.id, flag_kind)

    if deferred:
        if reply.state is not None and reply.state.accepted is True:
            outcome = TechniqueOutcome.ACCEPTED
            accepted_this_turn = True
            if offer.technique and offer.technique in config.registry:
                offered_now.append(offer.technique)
        else:
            # Carrying on past the offer is Keep chatting (muhammad, 2026-09-24), held here
            # rather than left to the model, which kept asking again. The one exception is a
            # question the reply answers by making the offer again: they asked about it.
            asked_about_it = "?" in content and any(p.technique for p in reply.prompts or [])
            if not asked_about_it or (reply.state is not None and reply.state.accepted is False):
                outcome = TechniqueOutcome.DECLINED
    elif (
        technique is None
        and ctx.technique is not None
        and ctx.technique.outcome is TechniqueOutcome.DECLINED
        and reply.state is not None
        and reply.state.accepted is True
        and reply.state.technique == ctx.technique.framework_id
    ):
        # They came back and asked for the one they turned down: that is a yes, cooldown or
        # not, since the cooldown only keeps Mani from asking again.
        technique = ctx.technique
        outcome = TechniqueOutcome.ACCEPTED
        accepted_this_turn = True
        offered_now.append(technique.framework_id)

    vetoed = repairs.ruled_out(reply, user_texts, config.registry)
    fixed = repairs.apply(
        reply,
        config.registry,
        # Only the framework they have just finished is off the table.
        already_offered=[ctx.technique.framework_id] if _finished(ctx.technique) else [],
        # A declined offer is no longer pending, so re-showing it is a new offer, and a new
        # offer waits out the cooldown like any other.
        current_framework_id=(
            technique.framework_id
            if technique and outcome is not TechniqueOutcome.DECLINED
            else None
        ),
        current_phase=technique.phase if technique else None,
        selected_label=tapped.label if tapped else None,
        accepted_this_turn=accepted_this_turn,
        framework_running=outcome is TechniqueOutcome.ACCEPTED,
        # The reply that takes a no never carries the next offer, however long the last one
        # stood open.
        offer_allowed=(
            refusal is None and vetoed is None and outcome is not TechniqueOutcome.DECLINED
        ),
        conversation_style=context.resolve_style(ctx),
        wants_title=wants_title,
        last_mani_text=next((m.content for m in reversed(history) if m.role is MessageRole.MANI), None),
        explaining=explaining is not None,
        current_holds=technique.holds if technique else 0,
        asked_again=False if tapped else context.asks_to_hear_again(content),
        current_ending=technique.ending if technique else None,
        skipped=skipped,
        their_question=their_question,
        # When code decided the offer it is added or dropped here rather than being the
        # model's to make: that is the whole point of deciding it in code.
        offer_decided=decision is not None,
        required_offer=(
            decision.framework_id
            if decision is not None and decision.offers and refusal is None
            else None
        ),
    )
    framework_running = outcome is TechniqueOutcome.ACCEPTED
    if assessment.blocks_framework or model_concern:
        # A concern pauses the framework rather than ending it: nothing this reply reports
        # about a stage is applied, and it may not open a new one. The stored state is left
        # exactly as it was, so the framework resumes from there once the concern has passed.
        paused = [p.technique for p in fixed.prompts if p.technique]
        pause_note = []
        if framework_running:
            pause_note = [
                f"framework paused: screen {assessment.category.value if assessment.category else assessment.level.value}"
                if assessment.blocks_framework
                else f"framework paused: concern {flag_kind}"
            ]
        fixed = dataclasses.replace(
            fixed,
            framework_id=None,
            phase=None,
            prompts=[p for p in fixed.prompts if not p.technique],
            notes=fixed.notes
            + ([f"dropped a technique offered on a safety-concern turn: {', '.join(paused)}"]
               if paused else [])
            + pause_note,
        )
    elif flagged and framework_running:
        fixed = dataclasses.replace(
            fixed, notes=fixed.notes + ["concern flagged as other, framework continued"]
        )
    if technique is not None and not (assessment.blocks_framework or model_concern):
        fixed = _body_route_step(
            fixed,
            technique.framework_id,
            config.registry.get(technique.framework_id).stages,
            context.resolve_style(ctx),
            content,
            technique.phase,
            _awaiting_place(history),
        )
    if fixed.phase == "somatic_checkin" and fixed.framework_id is not None:
        # The one body question, where they feel it, is fixed content sent word for word after
        # Mani's bridge, with the place buttons (spec 0011, AC-10). Set before the hand-off
        # filter below, which keeps them.
        stage = config.registry.get(fixed.framework_id).stages.get("somatic_checkin") or {}
        script = (stage.get("ask") or {}).get(context.resolve_style(ctx))
        if script:
            fixed = dataclasses.replace(
                fixed,
                text=repairs.with_the_check_in(fixed.text, script),
                prompts=[SmartPrompt(label=label) for label in repairs.PLACE_LABELS],
            )
    if fixed.notes:
        logger.info("repaired reply on thread %s: %s", ctx.thread.id, "; ".join(fixed.notes))
    # How they say they feel after the practice, only on the turn that answers it and with no
    # concern raised on it.
    felt_after = (
        repairs.known_value(reply.felt_after, repairs.FELT_AFTER)
        if practiced_place is not None and not (assessment.blocks_framework or model_concern)
        else None
    )
    if practiced_place is not None and felt_after is None:
        logger.info("thread %s answered the practice with no outcome reported", ctx.thread.id)
    decision = turn_decision(
        reply, fixed, config.registry,
        refusal=refusal,
        vetoed=vetoed,
        concern=assessment.blocks_framework or model_concern,
        declined=outcome is TechniqueOutcome.DECLINED,
        running=framework_running,
        step_from=technique.phase if technique else None,
    )
    decision["felt_after"] = felt_after
    # Ids and codes only, never their words.
    logger.info("thread %s decision %s", ctx.thread.id, decision)
    await log_decision(call.call_id, decision)
    if technique is not None and (
        config.registry.is_final(technique.framework_id, fixed.phase)
        or fixed.phase == "somatic_checkin"
    ):
        # The two somatic stages carry buttons by one rule: a reply that has moved to the two
        # choices - the practice done, or the check-in skipped or declined - shows Chat More /
        # Go to Library; the check-in question and the practice itself keep their own prompts and
        # never a leaked hand-off.
        without_handoff = [
            p for p in fixed.prompts
            if p.library is None and p.label.strip().lower() not in _HANDOFF_LABELS
        ]
        fixed = dataclasses.replace(
            fixed,
            prompts=_handoff() if _ASKS_WHAT_NEXT.search(fixed.text) else without_handoff,
        )
    if retiring_framework_id is not None and repairs.comes_back(content):
        # The client's words for a feeling that returns after the practice, sent as written.
        returning = repairs.returning_reply(
            config.registry.get(retiring_framework_id).stages.get("somatic_practice") or {},
            context.resolve_style(ctx),
        )
        if returning:
            fixed = dataclasses.replace(fixed, text=returning)
    # It did not help, so Mani says so and stops, with the two choices and no question. When
    # they asked something of their own, the model's answer stands, its questions taken out.
    not_helped = (
        retiring_framework_id is not None
        and felt_after in repairs.NOT_HELPED
        and not repairs.comes_back(content)
    )
    if not_helped:
        answered = repairs.without_questions(fixed.text) if "?" in content else ""
        fixed = dataclasses.replace(
            fixed, text=answered or repairs.NOT_HELPED_LINE, prompts=_handoff()
        )
    if (
        retiring_framework_id is not None
        and content.strip().lower() not in _HANDOFF_LABELS
        and not _offered_handoff(history)
    ):
        # The reply that ends a framework offers the client's two choices, always and
        # exactly. Left to the model they came back mislabeled or missing. Skipped when
        # they have already chosen one, or were just offered both.
        fixed = dataclasses.replace(fixed, prompts=_handoff())
    if not fixed.text.strip():
        # Nothing left to say once leaked metadata was stripped. Refused here as retryable,
        # rather than by the messages_content_not_empty constraint as an opaque 500.
        raise ServiceError(
            f"reply on thread {ctx.thread.id} was empty after repair",
            ErrorCategory.LLM_UNAVAILABLE,
            retryable=True,
            user_message="Mani had trouble responding. Please try again.",
        )

    pair = await messages_db.create_pair(
        conn,
        ctx.thread.id,
        content,
        fixed.text,
        selected_prompt=tapped.label if tapped else None,
        prompt_options=[p.model_dump(mode="json", exclude_none=True) for p in fixed.prompts]
        or None,
        client_message_id=client_message_id,
    )

    if felt_after is not None and not pair.was_duplicate:
        await outcomes.record(
            conn,
            user_id=user_id,
            thread_id=ctx.thread.id,
            message_id=pair.user_message_id,
            framework_id=retiring_framework_id,
            conversation_style=context.resolve_style(ctx),
            ending=ctx.technique.ending or "resolved",
            body_place=practiced_place,
            outcome=felt_after,
        )

    count_after = ctx.thread.message_count + 2
    new_offer = next((p for p in fixed.prompts if p.technique), None)
    library_offer = next((p for p in fixed.prompts if p.library), None)

    if new_offer is not None:
        updates.retire_technique = False
        updates.technique = TechniqueState(
            thread_id=ctx.thread.id,
            framework_id=new_offer.technique,
            outcome=TechniqueOutcome.OFFERED,
            phase=fixed.phase or "offering",
            at_message_count=count_after,
            # An offer made on the turn after "Are you feeling stuck?" starts at the stuck
            # questions once accepted.
            known=(
                {STUCK_BRANCH: "yes"}
                if stuck_offer is not None and new_offer.technique == stuck_offer.id
                else {}
            ),
        )
        updates.offer_frameworks.append(new_offer.technique)
    elif (decided := _decided_framework(fixed.framework_id, outcome, technique)) is not None:
        updates.retire_technique = False
        updates.technique = TechniqueState(
            thread_id=ctx.thread.id,
            framework_id=decided,
            outcome=outcome,
            phase=None if outcome is TechniqueOutcome.DECLINED else fixed.phase,
            at_message_count=(
                technique.at_message_count
                if technique and outcome is not TechniqueOutcome.DECLINED
                else count_after
            ),
            library_offered_since=False,
            holds=fixed.holds,
            # The stuck flag and the ending stay with the framework they belong to.
            known=technique.known if technique and technique.framework_id == decided else {},
            ending=fixed.ending if outcome is TechniqueOutcome.ACCEPTED else None,
        )
        if accepted_this_turn:
            updates.offer_frameworks.append(decided)
    elif accepted_this_turn and tapped and tapped.technique:
        updates.technique = TechniqueState(
            thread_id=ctx.thread.id,
            framework_id=tapped.technique,
            outcome=TechniqueOutcome.ACCEPTED,
            phase="offering",
            at_message_count=count_after,
        )
        updates.offer_frameworks.append(tapped.technique)

    if library_offer is not None:
        updates.library_offered = True
    if fixed.style is not None:
        updates.style = ResponseStyle(shape=fixed.style.shape)
    if fixed.title:
        updates.title = fixed.title

    await threads.apply(conn, ctx.thread.id, user_id, updates)

    exercise = None
    # Nothing more is handed over when the practice did not help, or when none was given
    # (spec 0011, AC-14).
    if retiring_framework_id is not None and practiced_place is not None and not not_helped:
        said = [m.content for m in history if m.role is MessageRole.USER][-2:] + [content]
        exercise = await _offer_exercise(
            conn, retiring_framework_id, config, model, parameters, routing, user_id,
            ctx.thread.id,
            said=said, current_issue=ctx.summary.current_issue if ctx.summary else None,
        )

    summarized = ctx.summary.summarized_message_count if ctx.summary else 0
    return Turn(
        message_id=pair.mani_message_id,
        content=fixed.text,
        created_at=pair.created_at,
        prompts=fixed.prompts,
        title=fixed.title or ctx.thread.title,
        crisis_detected=False,
        crisis_blocks_chat=settings.crisis_blocks_chat,
        was_duplicate=pair.was_duplicate,
        # Both sides of the comparison are thread message counts. The reference compared
        # a thread count against a running total of summarized messages, so the trigger
        # fired on two different units and drifted further apart with every summary.
        needs_summary=count_after - summarized >= SUMMARY_THRESHOLD,
        llm_call_id=call.call_id,
        exercise=exercise,
        reasoning=reply.reasoning if settings.ai_debug_mode else None,
    )


async def _offer_exercise(
    conn: asyncpg.Connection,
    framework_id: str,
    config,
    model: str,
    parameters: dict,
    routing: dict | None,
    user_id: str,
    thread_id: uuid.UUID,
    *,
    said: list[str],
    current_issue: str | None,
) -> Exercise | None:
    """The exercise that follows a just-completed framework, chosen by a bound tool call.

    A second, small model call - real tool-calling, not the turn's structured reply - and
    only reached here because a framework just finished. Every active exercise is a
    candidate, the framework's own first, and the pick sees what the person said. Skipped
    entirely, at zero cost, when the catalog is empty.
    """
    linked = await exercises_db.list_for_framework(conn, framework_id)
    linked_ids = {c.id for c in linked}
    candidates = linked + [
        c for c in await exercises_db.list_active(conn) if c.id not in linked_ids
    ]
    if not candidates:
        return None

    framework = config.registry.get(framework_id)
    chosen_id = await client.choose_exercise(
        [
            {
                "id": str(c.id), "title": c.title, "subtitle": c.subtitle or "",
                "type": c.type or "", "category": c.category,
            }
            for c in candidates
        ],
        framework.name if framework else framework_id,
        model=model,
        purpose=llm_calls.Purpose.EXERCISE_SELECT,
        said=said,
        current_issue=current_issue,
        # A model that thinks first needs room for it as well as for the tool call; the pick
        # falls back to the first candidate when no call is made.
        max_tokens=parameters.get("exerciseMaxTokens", client.DEFAULT_EXERCISE_MAX_TOKENS),
        reasoning_effort=parameters.get("reasoning_effort"),
        routing=routing,
        user_id=user_id,
        thread_id=thread_id,
    )
    return next((c for c in candidates if str(c.id) == chosen_id), candidates[0])


# FastAPI's own documented order is response sent -> background tasks run -> yield
# dependencies' exit code, which is where UserConn's transaction actually commits. So this
# background task starts running *before* the message it wants to reference is guaranteed
# visible to another connection - confirmed live: attach_message raised a foreign key
# violation on every turn. A short, bounded retry is the fix, not a bigger one: the commit
# in question happens within milliseconds of the background task starting, once at all.
LINK_RETRY_ATTEMPTS = 5
LINK_RETRY_DELAY_SECONDS = 0.05


async def link_call(call_id: uuid.UUID, message_id: uuid.UUID) -> None:
    """Point a recorded model call at the message it produced.

    admin.llm_calls carries a foreign key to public.messages, and the turn that wrote the
    message has not necessarily committed yet when this runs - see the note above. A
    failure after every retry costs a forensic link, not a delivered reply, so it is logged
    and swallowed rather than raised.
    """
    import asyncio

    from mani.db import pool

    for attempt in range(1, LINK_RETRY_ATTEMPTS + 1):
        try:
            async with pool.as_admin() as conn:
                await llm_calls.attach_message(conn, call_id, message_id)
            return
        except asyncpg.PostgresError:
            if attempt == LINK_RETRY_ATTEMPTS:
                logger.exception(
                    "failed to link llm call %s to message %s after %d attempts",
                    call_id, message_id, LINK_RETRY_ATTEMPTS,
                )
                return
            await asyncio.sleep(LINK_RETRY_DELAY_SECONDS)


def turn_decision(
    reply: Reply,
    fixed: repairs.Repaired,
    registry: Registry,
    *,
    refusal: str | None,
    vetoed: str | None,
    concern: bool,
    declined: bool,
    running: bool,
    step_from: str | None,
) -> dict:
    """What the call log keeps of a turn's decisions (spec 0010, AC-10): the framework the reply
    offered and, when its offer was removed, why; and the step it moved from and to. Ids and
    codes only, never the person's words, and never an id outside the registry, which is the
    model's own text."""
    drafted = next((p.technique for p in reply.prompts or [] if p.technique), None)
    kept = next((p.technique for p in fixed.prompts if p.technique), None)
    refused = None
    if drafted is not None and kept is None:
        refused = (
            "unknown" if drafted not in registry
            else "safety_concern" if concern
            else refusal
            or ("vetoed" if vetoed else None)
            or ("cooling_down" if declined else None)
            or ("running" if running else None)
            or "another_question"
        )
    return {
        "offered": drafted if drafted in registry else None,
        "refused": refused,
        "step_from": step_from,
        # A step only for an offer that stands or a framework that runs.
        "step_to": fixed.phase if running or kept is not None else None,
        "ending": fixed.ending,
        "felt_after": None,
    }


async def log_decision(call_id: uuid.UUID | None, decision: dict) -> None:
    """Keep a turn's decisions on its call row. The row was written and committed by
    client.complete, so no wait is needed; a failure costs a trace, never the reply, so it is
    logged and swallowed."""
    from mani.db import pool

    if call_id is None:
        return
    try:
        async with pool.as_admin() as conn:
            await llm_calls.attach_decision(conn, call_id, decision)
    except asyncpg.PostgresError:
        logger.exception("failed to keep the decision of llm call %s", call_id)


async def _open_in_style(
    conn: asyncpg.Connection,
    ctx: threads.TurnContext,
    content: str,
    style: SupportStyle,
    client_message_id: uuid.UUID | str | None,
) -> Turn:
    """Record the chosen style and answer with that style's opening question.

    The client spec gives the opener word for word, so there is nothing to generate: no
    model call, and the style holds for the rest of the conversation from this turn on.
    """
    reply = OPENERS[style.value]
    pair = await messages_db.create_pair(
        conn, ctx.thread.id, content, reply,
        selected_prompt=content.strip(), client_message_id=client_message_id,
    )
    await threads.apply(
        conn, ctx.thread.id, ctx.thread.user_id, threads.ThreadUpdates(conversation_style=style)
    )
    return Turn(
        message_id=pair.mani_message_id,
        content=reply,
        created_at=pair.created_at,
        title=ctx.thread.title,
    )


async def _handle_crisis(
    conn: asyncpg.Connection,
    ctx: threads.TurnContext,
    content: str,
    *,
    reason: str,
    reply_text: str,
    tapped: SmartPrompt | None,
    client_message_id: uuid.UUID | str | None,
    settings,
    updates: threads.ThreadUpdates,
    llm_call_id: uuid.UUID | None = None,
) -> Turn:
    """Store the turn, flag the thread, and answer with something a person can read.

    The reference stored only the user's message and returned an empty string, so the
    screen went blank at the one moment it mattered most. Called from two places: the
    deterministic safety screen, before any model call, and the model's own judgment,
    reported through the reply schema - either way the thread locks the same way.

    No exercise is handed over here. The thread is about to lock one way, so an exercise
    would reach someone who cannot ask a single question about it.
    """
    logger.warning("crisis signal on thread %s", ctx.thread.id)

    pair = await messages_db.create_pair(
        conn,
        ctx.thread.id,
        content,
        reply_text,
        selected_prompt=tapped.label if tapped else None,
        client_message_id=client_message_id,
    )
    await threads.mark_crisis(conn, ctx.thread.id, reason, pair.user_message_id)
    # A crisis turn is still a turn: whatever it already decided has to land. Today that is
    # a framework that completed on this very turn - without this the row keeps its phase
    # with outcome 'accepted', so the database claims a technique is still mid-flight on a
    # thread nobody can return to.
    await threads.apply(conn, ctx.thread.id, ctx.thread.user_id, updates)

    return Turn(
        message_id=pair.mani_message_id,
        content=reply_text,
        created_at=pair.created_at,
        prompts=[],
        title=ctx.thread.title,
        crisis_detected=True,
        crisis_blocks_chat=settings.crisis_blocks_chat,
        llm_call_id=llm_call_id,
    )


async def start_thread(
    conn: asyncpg.Connection, claims: Claims, title: str | None = None
) -> tuple[Thread, bool]:
    """Open a conversation, writing Mani's opening line only on a genuinely new one.

    Returns (thread, created). A reused thread already has its greeting, and
    create_greeting refuses a second one anyway.
    """
    thread, created = await threads.create_or_reuse(conn, claims.user_id, title)
    if created:
        profile = await profiles.get(conn, claims.user_id)
        returning = await _has_earlier_thread(conn, claims.user_id, thread.id)
        await messages_db.create_greeting(
            conn, thread.id, greeting(profile.nickname if profile else None, returning),
            prompt_options=STYLE_OPTIONS,
        )
    return thread, created


async def _has_earlier_thread(
    conn: asyncpg.Connection, user_id: str, exclude: uuid.UUID
) -> bool:
    return bool(
        await conn.fetchval(
            "select exists (select 1 from public.threads "
            "where user_id = $1 and id <> $2)",
            user_id, exclude,
        )
    )


async def summary_snapshot(
    conn: asyncpg.Connection, thread_id: uuid.UUID | str, user_id: str
) -> tuple[list[Message], object | None]:
    """The messages a summary run should read, and the summary it is updating."""
    existing = await summaries.get(conn, thread_id)
    page = await messages_db.list_for_thread(conn, thread_id, user_id, limit=200)
    return list(reversed(page.messages)), existing
