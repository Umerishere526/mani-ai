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
from mani.chat import context, crisis, repairs, router, safety
from mani.chat.greeting import (
    CHAT_MORE_LABEL,
    GO_TO_LIBRARY_LABEL,
    OPENERS,
    STYLE_OPTIONS,
    EXPLAIN_LABELS,
    KEEP_CHATTING_LABEL,
    TELL_ME_MORE,
    TRY_IT_LABEL,
    greeting,
)
from mani.config import get_settings
from mani.db import (
    exercises as exercises_db,
    llm_calls,
    messages as messages_db,
    profiles,
    summaries,
    threads,
)
from mani.errors import ErrorCategory, ServiceError
from mani.llm import client
from mani.llm.schema import LibrarySection, Reply, SmartPrompt
from mani.models.rows import (
    Exercise,
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

# The router narrows once there is enough to narrow from. Below this, one or two messages
# is not a pattern - it is the start of a conversation.
ROUTER_MIN_EXCHANGES = 2

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
    if (
        technique is not None
        and technique.outcome is TechniqueOutcome.ACCEPTED
        and config.registry.is_final(technique.framework_id, technique.phase)
    ):
        retiring_framework_id = technique.framework_id
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
    if tapped and offer and tapped.label.strip().lower() in EXPLAIN_LABELS:
        return await _explain_offer(conn, ctx, content, offer, config, client_message_id)
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

    # The router narrows the field it is not the caller's job to decide; the model still
    # confirms whatever it offers, and repairs.apply still validates that choice against the
    # registry. No model call, so a false or missing shortlist costs relevance, never safety.
    shortlist: list[router.Signal] = []
    candidate = None
    if (
        technique is None
        and assessment.level is safety.Level.NONE
        and (
            ctx.thread.message_count // 2 >= ROUTER_MIN_EXCHANGES
            # An imminent action is the one case not worth waiting two exchanges on.
            or router.urgent(user_texts)
        )
    ):
        shortlist = router.shortlist(user_texts, config.registry.activations)
        if shortlist and router.is_confident(shortlist):
            candidate = config.registry.get(shortlist[0].framework_id)

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

    active_framework = config.registry.get(technique.framework_id) if technique else None
    prefix = context.build(
        ctx, shortlist=shortlist, framework=active_framework, candidate=candidate,
        history=history, safety_concern=assessment.blocks_framework, offer_waiting=deferred,
    )
    for_model = (
        f'User tapped the button: "{tapped.label}".'
        if tapped
        else context.disarm(content)
    )

    # Checked here, right before the only paid step, so the safety screen and every free
    # reply (style opener, "Tell me about this") come first and are never refused.
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
        routing=routing,
        user_id=user_id,
        thread_id=ctx.thread.id,
        prompt_version_id=None,
    )
    reply = call.value

    # Crisis is read straight off the first reply, before any repair can drop the field
    # while rewriting something else.
    if reply.crisis is not None:
        return await _handle_crisis(
            conn, ctx, content,
            reason=reply.crisis.reason,
            reply_text=crisis.CRISIS_REPLY,
            tapped=tapped, client_message_id=client_message_id, settings=settings,
            updates=updates, llm_call_id=call.call_id,
        )

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

    fixed = repairs.apply(
        reply,
        config.registry,
        # Everything they have said in this thread, not only this turn: a capsule may mirror
        # a feeling they named four messages ago, and mani_base.md asks for exactly that.
        said=" ".join(user_texts),
        # Only the framework they have just finished is off the table. One they said no to
        # may come back once the cooldown has passed (muhammad, 2026-09-24).
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
        cooldown_passed=context.cooldown_passed(ctx) and outcome is not TechniqueOutcome.DECLINED,
        conversation_style=context.resolve_style(ctx),
        wants_title=wants_title,
    )
    if assessment.blocks_framework:
        # A concern pauses the framework rather than ending it: nothing this reply reports
        # about a stage is applied, and it may not open a new one. The stored state is left
        # exactly as it was, so the framework resumes from there once the concern has passed.
        paused = [p.technique for p in fixed.prompts if p.technique]
        fixed = dataclasses.replace(
            fixed,
            framework_id=None,
            phase=None,
            prompts=[p for p in fixed.prompts if not p.technique],
            notes=fixed.notes
            + ([f"dropped a technique offered on a safety-concern turn: {', '.join(paused)}"]
               if paused else []),
        )
    if fixed.notes:
        logger.info("repaired reply on thread %s: %s", ctx.thread.id, "; ".join(fixed.notes))
    if technique is not None and config.registry.is_final(technique.framework_id, fixed.phase):
        # The check-in reply asks about their body, and they answer before choosing - unless
        # they had already described it, and this reply mirrors that and asks what next.
        without_handoff = [
            p for p in fixed.prompts
            if p.library is None and p.label.strip().lower() not in _HANDOFF_LABELS
        ]
        fixed = dataclasses.replace(
            fixed,
            prompts=_handoff() if _ASKS_WHAT_NEXT.search(fixed.text) else without_handoff,
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
        updates.style = ResponseStyle(shape=fixed.style.shape, voice=fixed.style.voice)
    if fixed.title:
        updates.title = fixed.title

    await threads.apply(conn, ctx.thread.id, user_id, updates)

    exercise = None
    if retiring_framework_id is not None:
        exercise = await _offer_exercise(
            conn, retiring_framework_id, config, model, routing, user_id, ctx.thread.id
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
    routing: dict | None,
    user_id: str,
    thread_id: uuid.UUID,
) -> Exercise | None:
    """The exercise that follows a just-completed framework, chosen by a bound tool call.

    A second, small model call - real tool-calling, not the turn's structured reply - and
    only reached here because a framework just finished. Skipped entirely, at zero cost,
    when the catalog has nothing for this framework yet - true for every framework today.
    """
    candidates = await exercises_db.list_for_framework(conn, framework_id)
    if not candidates:
        return None

    framework = config.registry.get(framework_id)
    chosen_id = await client.choose_exercise(
        [
            {"id": str(c.id), "title": c.title, "subtitle": c.subtitle or ""}
            for c in candidates
        ],
        framework.name if framework else framework_id,
        model=model,
        purpose=llm_calls.Purpose.EXERCISE_SELECT,
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


async def _explain_offer(
    conn: asyncpg.Connection,
    ctx: threads.TurnContext,
    content: str,
    offer: SmartPrompt,
    config: cache.Config,
    client_message_id: uuid.UUID | str | None,
) -> Turn:
    """Answer "Tell me about this" with the client's description of it, and offer it again.

    Fixed wording, so no model call. The description is the framework's `summary`, written by
    the client; the per-style explanation is the fallback for a framework without one. The
    offer stays open: its row is untouched, and the new buttons carry the same technique, so
    tapping "Try it" next accepts it as usual.
    """
    framework = config.registry.get(offer.technique)
    reply = (framework.summary if framework and framework.summary
             else TELL_ME_MORE[context.resolve_style(ctx)])
    buttons = [
        SmartPrompt(label=TRY_IT_LABEL, technique=offer.technique),
        SmartPrompt(label=KEEP_CHATTING_LABEL, decline=True),
    ]
    pair = await messages_db.create_pair(
        conn, ctx.thread.id, content, reply,
        selected_prompt=content.strip(),
        prompt_options=[b.model_dump(mode="json", exclude_none=True) for b in buttons],
        client_message_id=client_message_id,
    )
    return Turn(
        message_id=pair.mani_message_id, content=reply, created_at=pair.created_at,
        prompts=buttons, title=ctx.thread.title,
    )


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
