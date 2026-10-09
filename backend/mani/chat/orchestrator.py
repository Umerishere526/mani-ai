# ABOUTME: One user message from arrival to stored reply: context, one model call, writes.
# ABOUTME: Everything it writes lands in the caller's transaction, or none of it does.

from __future__ import annotations

import dataclasses
import logging
import uuid
from dataclasses import dataclass, field

import asyncpg

from mani.auth.jwt import Claims
from mani.chat import context, guards, ledger, offer as offers, safety, vetoes
from mani.chat.greeting import CHAT_MORE_LABEL, GO_TO_LIBRARY_LABEL, greeting, style_options
from mani.chat.techniques import ENDING_PHASES, OFFERING
from mani.config import get_settings
from mani.db import (
    exercises as exercises_db,
    llm_calls,
    messages as messages_db,
    profiles,
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
from mani.prompts import cache, calls, composer
from mani.prompts.replies import Replies

logger = logging.getLogger(__name__)


def _handoff() -> list[SmartPrompt]:
    return [
        SmartPrompt(label=CHAT_MORE_LABEL),
        SmartPrompt(label=GO_TO_LIBRARY_LABEL, library=LibrarySection.HOME.value),
    ]


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
    # Set only on the turn a framework's ending closes with a choice, and only when the
    # catalog has a matching exercise. A row model, not the wire shape - the router builds ExerciseOut
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


def explained_offer(history: list[Message], content: str) -> tuple[str, str] | None:
    """The tapped label and the offered framework, when this message is a tap on Tell me more.

    Read from the stored options, like `chosen_style`: `more` is a key only the code writes.
    """
    typed = content.strip().lower()
    for option in _last_offered(history):
        label = str(option.get("label", ""))
        if option.get("more") and label.strip().lower() == typed:
            offer = pending_offer(history)
            return (label, offer.technique) if offer else None
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

    # Before anything else about the turn, so a broken `replies` or `tuning` row is reported first.
    config = await cache.load()
    tuning = config.tuning
    ctx = await threads.load_turn_context(conn, thread_id, user_id, tuning.windows.style_window)
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

    history = await messages_db.recent_for_context(
        conn, thread_id, user_id, tuning.windows.context_window
    )
    updates = threads.ThreadUpdates()

    style = chosen_style(history, content)
    if style is not None:
        return await _open_in_style(conn, ctx, content, style, config.replies, client_message_id)
    # The style [ctx] names this turn, so the seeded offer and Tell me more speak in it too.
    style_now = context.resolve_style(ctx, tuning.offers.default_style)
    explained = explained_offer(history, content)
    if explained is not None and explained[1] in config.registry:
        label, framework_id = explained
        return await _explain_offer(
            conn, ctx, content, label, config.registry.get(framework_id), config.replies,
            style_now, client_message_id, settings,
        )

    technique = ctx.technique
    # An ending the model has not closed by the cap is finished here, before the call, so this
    # turn's [ctx] shows nothing running. The row is retired rather than removed, and the
    # snapshot keeps it with its phase cleared, so this turn's [ctx] reports the cooldown the
    # completion just started instead of reporting that nothing has ever run. No Library offer
    # is owed after it, so the snapshot says that too.
    capped = (
        technique is not None
        and technique.outcome is TechniqueOutcome.ACCEPTED
        and technique.phase in ENDING_PHASES
        and technique.ending_from is not None
        and (ctx.thread.message_count - technique.ending_from) // 2
        >= tuning.windows.ending_turn_cap
    )
    if capped:
        logger.info(
            "thread %s retired its framework at the ending cap of %d turns",
            ctx.thread.id, tuning.windows.ending_turn_cap,
        )
        updates.retire_technique = True
        ctx = dataclasses.replace(ctx, technique=technique.model_copy(update={
            "phase": None, "ending_from": None, "library_offered_since": True,
        }))
        technique = None

    # From here on `technique` means the framework that is live on this turn: offered and
    # awaiting an answer, or accepted and mid-way. A row that is finished (phase cleared) or
    # declined stays in the snapshot, because [ctx] measures the cooldown from it - but it
    # is not running, so it must not strip technique buttons.
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
    # The framework the person said yes to this turn, which is the stored row's unless they tapped
    # another one.
    accepted_framework = technique.framework_id if technique else None

    if tapped and tapped.technique and tapped.technique in config.registry:
        outcome = TechniqueOutcome.ACCEPTED
        accepted_this_turn = True
        accepted_framework = tapped.technique
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
    # call entirely; concern only holds back a framework, so the model still answers.
    assessment = safety.screen(content)
    if assessment.level is safety.Level.CRISIS:
        if (
            technique is not None
            and technique.outcome is TechniqueOutcome.ACCEPTED
            and config.registry.ending_open(technique.framework_id, technique.phase)
        ):
            # No model call means no `ending`, and the thread is about to lock one way, so a
            # framework in its ending is ended here or never.
            updates.retire_technique = True
        return await _handle_crisis(
            conn, ctx, content,
            reason=f"safety screen: {assessment.category.value if assessment.category else 'unspecified'}",
            reply_text=safety.protocol_for(assessment.category),
            tapped=tapped, client_message_id=client_message_id, settings=settings,
            updates=updates,
        )

    # Read by the grief veto below: everything they have said in the context window rather than
    # only this turn.
    user_texts = [m.content for m in history if m.role is MessageRole.USER] + [content]

    # What they said rules a framework out (early grief for Behavioral Activation). Told to the
    # model in [ctx], so it is never offered.
    ruled_out = vetoes.ruled_out(config.registry.vetoes, user_texts)

    wants_title = (
        ctx.thread.message_count >= tuning.windows.title_after_messages and not ctx.thread.title
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
        ctx, framework=active_framework,
        history=history, safety_concern=assessment.blocks_framework, offer_waiting=deferred,
        framework_starting=accepted_this_turn, ruled_out=ruled_out,
        replies=config.replies, tuning=tuning,
    )
    for_model = (
        f"tapped: {tapped.label}"
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
    # After the daily limit, so a person who reached it is told so rather than shown a
    # config error, and before the call, so a row with no level spends nothing.
    effort = calls.effort_for(config.require("mani_base"), "mani_base")

    call = await client.complete(
        [{"role": "system", "content": system.text}]
        + _conversation(history)
        + [{"role": "user", "content": prefix + for_model}],
        Reply,
        model=model,
        purpose=llm_calls.Purpose.CHAT,
        temperature=parameters.get("temperature", client.DEFAULT_TEMPERATURE),
        max_tokens=parameters.get("maxTokens", client.DEFAULT_MAX_TOKENS),
        reasoning_effort=effort,
        routing=routing,
        user_id=user_id,
        thread_id=ctx.thread.id,
        retry_malformed=False,
    )
    reply = call.value
    if reply.heading_toward:
        # Read by the steering evals and by anyone asking why a question went where it did:
        # the id only, never a word of what the person said.
        logger.info("thread %s heading toward %s", ctx.thread.id, reply.heading_toward)

    # The model's own crisis judgment no longer locks the thread: a small model over-fires it
    # on ordinary distress, pain or injury. Only the deterministic screen (safety.screen, above)
    # locks. A model-reported crisis is kept as a non-locking concern - logged, and the framework
    # held off this turn - so a genuine novel phrasing still gets careful handling without
    # cutting off the conversation the person came for.
    model_concern = reply.crisis is not None
    if model_concern:
        logger.info(
            "model reported a safety concern on thread %s: %s",
            ctx.thread.id, reply.crisis.reason,
        )

    if deferred:
        if reply.state is not None and reply.state.accepted is True:
            outcome = TechniqueOutcome.ACCEPTED
            accepted_this_turn = True
            if offer.technique and offer.technique in config.registry:
                accepted_framework = offer.technique
                offered_now.append(offer.technique)
        else:
            # Carrying on past the offer is Keep Chatting (muhammad, 2026-09-24), held here
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
        accepted_framework = technique.framework_id
        offered_now.append(technique.framework_id)

    checked = guards.check(
        reply,
        config.registry,
        # A declined offer is no longer pending, so it is not the framework this turn is in.
        current_framework_id=(
            technique.framework_id
            if technique and outcome is not TechniqueOutcome.DECLINED
            else None
        ),
        current_phase=technique.phase if technique else None,
        accepted_this_turn=accepted_this_turn,
        framework_running=outcome is TechniqueOutcome.ACCEPTED,
        declined=outcome is TechniqueOutcome.DECLINED,
        retiring=capped,
        wants_title=wants_title,
        shapes=config.reply_shapes,
        ending_open=(
            technique is not None
            and outcome is TechniqueOutcome.ACCEPTED
            and config.registry.ending_open(technique.framework_id, technique.phase)
        ),
    )
    concerned = assessment.blocks_framework or model_concern
    if concerned:
        # A concern pauses the framework rather than ending it: nothing this reply reports
        # about a stage or an ending is applied, and it may not open a new one. The stored
        # state is left exactly as it was, so the framework resumes from there once the
        # concern has passed.
        paused = any(p.technique for p in checked.prompts)
        checked = dataclasses.replace(
            checked,
            framework_id=None,
            phase=None,
            ending=None,
            prompts=guards.without_offer(checked.prompts),
            notes=checked.notes + (["dropped the offer: a safety concern"] if paused else []),
        )
    running_state: TechniqueState | None = None
    if outcome is TechniqueOutcome.ACCEPTED and not concerned:
        running_state, checked = _running_state(
            config.registry, ctx, reply, checked, technique,
            framework_id=accepted_framework if accepted_this_turn else (
                technique.framework_id if technique else None
            ),
            accepted_this_turn=accepted_this_turn, count_after=ctx.thread.message_count + 2,
        )
    retiring = capped or checked.ending is not None
    if retiring or any(
        config.registry.ending_open(framework_id, phase)
        for framework_id, phase in (
            (technique.framework_id if technique else None, technique.phase if technique else None),
            (checked.framework_id, checked.phase),
        )
    ):
        # The ending carries no buttons from the model; the two choices below are written by
        # the code, and only on a kept `choice`.
        if checked.prompts:
            checked = dataclasses.replace(
                checked, prompts=[], notes=checked.notes + ["dropped the buttons: the ending"]
            )
    if technique is None:
        # The offer rule is told, not enforced, so this is how an offer before the cooldown shows
        # up: ids and a flag only, never a word of what was said.
        passed = "yes" if context.cooldown_passed(ctx, tuning) else "no"
        for offered in dict.fromkeys(p.technique for p in checked.prompts if p.technique):
            logger.info(
                "offer on thread %s: %s cooldown_passed: %s", ctx.thread.id, offered, passed,
            )
    if checked.notes:
        logger.info("checked reply on thread %s: %s", ctx.thread.id, "; ".join(checked.notes))
    if checked.ending is guards.Ending.CHOICE:
        # The two choices are written here and only here, so a library button the model sent
        # can never silence library_pending.
        checked = dataclasses.replace(checked, prompts=_handoff())
    stored_options = [p.model_dump(mode="json", exclude_none=True) for p in checked.prompts]
    offered = next((p.technique for p in checked.prompts if p.technique), None)
    if offered is not None:
        # Every check that can stop an offer has run, so the one left is an offer. The model chose
        # that and which set; its own line leads and the seeded offer's words and buttons follow.
        # No style is recorded, because the shape it reported describes a reply, not a bridge line.
        seeded, stored_options = offers.offer(
            config.replies, config.registry.get(offered), style_now
        )
        checked = dataclasses.replace(
            checked,
            text="\n\n".join(part for part in (checked.text, seeded) if part),
            prompts=[SmartPrompt.model_validate(option) for option in stored_options],
            style=None,
        )
    if not checked.text:
        # Nothing to say. Refused here as retryable, rather than by the
        # messages_content_not_empty constraint as an opaque 500.
        raise ServiceError(
            f"reply on thread {ctx.thread.id} was empty",
            ErrorCategory.LLM_UNAVAILABLE,
            retryable=True,
            user_message="Mani had trouble responding. Please try again.",
        )

    pair = await messages_db.create_pair(
        conn,
        ctx.thread.id,
        content,
        checked.text,
        selected_prompt=tapped.label if tapped else None,
        prompt_options=stored_options or None,
        client_message_id=client_message_id,
    )

    count_after = ctx.thread.message_count + 2
    new_offer = next((p for p in checked.prompts if p.technique), None)

    if retiring:
        # Retirement wins over every branch below: the state a reply reports, or an offer's
        # row, would be written over it and the framework would be running again.
        updates.retire_technique = True
    elif new_offer is not None:
        updates.retire_technique = False
        updates.technique = TechniqueState(
            thread_id=ctx.thread.id,
            framework_id=new_offer.technique,
            outcome=TechniqueOutcome.OFFERED,
            phase=checked.phase or "offering",
            at_message_count=count_after,
        )
        updates.offer_frameworks.append(new_offer.technique)
    elif running_state is not None:
        updates.retire_technique = False
        updates.technique = running_state
        if accepted_this_turn:
            updates.offer_frameworks.append(running_state.framework_id)
    elif (decided := _decided_framework(checked.framework_id, outcome, technique)) is not None:
        updates.retire_technique = False
        # Carried from the stored row, never moved forward and never cleared by a step back,
        # so the cap cannot be reset by stepping between the last own phase and the ending.
        ending_from = technique.ending_from if technique else None
        if ending_from is None and checked.phase in ENDING_PHASES:
            ending_from = count_after
        updates.technique = TechniqueState(
            thread_id=ctx.thread.id,
            framework_id=decided,
            outcome=outcome,
            # An offer they have not answered stays on the offering phase; the code, not the model's
            # step, decides every stage after it.
            phase=None if outcome is TechniqueOutcome.DECLINED else checked.phase or OFFERING,
            at_message_count=(
                technique.at_message_count
                if technique and outcome is not TechniqueOutcome.DECLINED
                else count_after
            ),
            library_offered_since=False,
            ending_from=None if outcome is TechniqueOutcome.DECLINED else ending_from,
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

    if retiring:
        # No Library offer is owed once the ending is over, whether or not it was offered.
        updates.library_offered = True
    if checked.style is not None:
        updates.style = ResponseStyle(shape=checked.style.shape)
    if checked.title:
        updates.title = checked.title

    await threads.apply(conn, ctx.thread.id, user_id, updates)

    exercise = None
    if checked.ending is guards.Ending.CHOICE:
        said = [m.content for m in history if m.role is MessageRole.USER][-2:] + [content]
        exercise = await _offer_exercise(
            conn, technique.framework_id, config, user_id, ctx.thread.id,
            said=said, current_issue=ctx.summary.current_issue if ctx.summary else None,
        )

    summarized = ctx.summary.summarized_message_count if ctx.summary else 0
    return Turn(
        message_id=pair.mani_message_id,
        content=checked.text,
        created_at=pair.created_at,
        prompts=checked.prompts,
        title=checked.title or ctx.thread.title,
        crisis_detected=False,
        crisis_blocks_chat=settings.crisis_blocks_chat,
        was_duplicate=pair.was_duplicate,
        # Both sides of the comparison are thread message counts. The reference compared
        # a thread count against a running total of summarized messages, so the trigger
        # fired on two different units and drifted further apart with every summary.
        needs_summary=count_after - summarized >= tuning.windows.context_window,
        llm_call_id=call.call_id,
        exercise=exercise,
        reasoning=reply.reasoning if settings.ai_debug_mode else None,
    )


def _running_state(
    registry,
    ctx: threads.TurnContext,
    reply: Reply,
    checked: guards.Checked,
    technique: TechniqueState | None,
    *,
    framework_id: str | None,
    accepted_this_turn: bool,
    count_after: int,
) -> tuple[TechniqueState | None, guards.Checked]:
    """The row a turn writes while a framework runs, and the checked reply with the phase it records.

    Before the framework's last own phase the stage comes from the ledger: what the reply reports of
    each stage over what was stored, and the stage asked is the first not known. On the turn they say
    yes the ledger starts empty, so the reply judges every stage against all they said before the
    offer. From the last own phase on the ledger is as stored and the reported step moves through the
    ending. None when the framework is not one the registry holds.
    """
    if framework_id is None or framework_id not in registry:
        return None, checked
    stored_phase = technique.phase if technique else None
    accepting = accepted_this_turn or stored_phase == OFFERING
    notes = list(checked.notes)
    stored = technique.stage_ledger if technique else {}

    if not accepting and registry.ending_open(framework_id, stored_phase):
        stage_ledger = stored
        phase = checked.phase or stored_phase
    else:
        stage_ledger = ledger.with_reported(
            {} if accepting else ledger.stored_stages(registry, framework_id, stored),
            checked.stages, notes,
        )
        phase = registry.stage_from_ledger(framework_id, stage_ledger)
        if checked.stages is None:
            notes.append("no stages reported on a running turn")
        step = reply.state.step if reply.state and checked.framework_id else None
        if not accepting and step in registry.ledger_stages(framework_id) and step != phase:
            notes.append("the reported step differs from the stage the ledger gives")

    # Carried from the stored row, never moved forward and never cleared by a step back, so the
    # cap cannot be reset by stepping between the last own phase and the ending.
    ending_from = technique.ending_from if technique else None
    if ending_from is None and phase in ENDING_PHASES:
        ending_from = count_after
    state = TechniqueState(
        thread_id=ctx.thread.id,
        framework_id=framework_id,
        outcome=TechniqueOutcome.ACCEPTED,
        phase=phase,
        at_message_count=technique.at_message_count if technique else count_after,
        library_offered_since=False,
        ending_from=ending_from,
        stage_ledger=stage_ledger,
    )
    return state, dataclasses.replace(checked, phase=phase, notes=notes)


async def _offer_exercise(
    conn: asyncpg.Connection,
    framework_id: str,
    config,
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
    entirely, at zero cost, when the catalog is empty. Its instruction, model and thinking
    level are the `exercise_select` row's; a row that is missing or names no level skips the
    pick and offers the first candidate, so a reply already built never fails over it.
    """
    linked = await exercises_db.list_for_framework(conn, framework_id)
    linked_ids = {c.id for c in linked}
    candidates = linked + [
        c for c in await exercises_db.list_active(conn) if c.id not in linked_ids
    ]
    if not candidates:
        return None

    try:
        prompt = config.require("exercise_select")
        effort = calls.effort_for(prompt, "exercise_select")
    except ServiceError as refused:
        logger.warning("exercise pick skipped, offering the first candidate: %s", refused)
        return candidates[0]
    parameters = prompt.model_parameters

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
        prompt.content,
        model=prompt.model_id or get_settings().default_chat_model,
        purpose=llm_calls.Purpose.EXERCISE_SELECT,
        reasoning_effort=effort,
        said=said,
        current_issue=current_issue,
        temperature=parameters.get("temperature", client.DEFAULT_TEMPERATURE),
        max_tokens=parameters.get("maxTokens", client.EXERCISE_MAX_TOKENS),
        routing=prompt.routing,
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


async def _open_in_style(
    conn: asyncpg.Connection,
    ctx: threads.TurnContext,
    content: str,
    style: SupportStyle,
    replies: Replies,
    client_message_id: uuid.UUID | str | None,
) -> Turn:
    """Record the chosen style and answer with that style's opening question.

    The client spec gives the opener word for word, so there is nothing to generate: no
    model call, and the style holds for the rest of the conversation from this turn on.
    """
    reply = replies.openers[style.value]
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


async def _explain_offer(
    conn: asyncpg.Connection,
    ctx: threads.TurnContext,
    content: str,
    label: str,
    framework: Framework,
    replies: Replies,
    style: str,
    client_message_id: uuid.UUID | str | None,
    settings,
) -> Turn:
    """Answer Tell me more from the `replies` row and the offered framework's row.

    No model call, and the offer stays exactly as it was: still waiting on its offering phase, with
    the two buttons that answer it.
    """
    reply, options = offers.told_more(replies, framework, style)
    pair = await messages_db.create_pair(
        conn, ctx.thread.id, content, reply,
        selected_prompt=label, prompt_options=options, client_message_id=client_message_id,
    )
    return Turn(
        message_id=pair.mani_message_id,
        content=reply,
        created_at=pair.created_at,
        prompts=[SmartPrompt.model_validate(option) for option in options],
        title=ctx.thread.title,
        crisis_blocks_chat=settings.crisis_blocks_chat,
        was_duplicate=pair.was_duplicate,
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
    screen went blank at the one moment it mattered most. Called from one place: the
    deterministic safety screen, before any model call. The model's own crisis judgment
    does not come here; it is kept as a concern that does not lock the thread.

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
    # a framework in its ending, retired by `send` because no model call means no `ending` -
    # without this the row keeps its phase with outcome 'accepted', so the database claims a
    # technique is still mid-flight on a thread nobody can return to.
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
        replies = (await cache.load()).replies
        profile = await profiles.get(conn, claims.user_id)
        returning = await _has_earlier_thread(conn, claims.user_id, thread.id)
        await messages_db.create_greeting(
            conn, thread.id, greeting(replies, profile.nickname if profile else None, returning),
            prompt_options=style_options(replies),
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
