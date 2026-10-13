# ABOUTME: One user message from arrival to stored reply: context, one model call, writes.
# ABOUTME: Everything it writes lands in the caller's transaction, or none of it does.

from __future__ import annotations

import dataclasses
import logging
import uuid
from dataclasses import dataclass, field

import asyncpg

from mani.auth.jwt import Claims
from mani.chat import context, repairs, reply_checks, safety
from mani.chat.greeting import (
    CHAT_MORE_LABEL,
    EXPLAIN_LABELS,
    GO_TO_LIBRARY_LABEL,
    OPENERS,
    STYLE_OPTIONS,
    greeting,
)
from mani.chat.techniques import OFFERING
from mani.config import get_settings
from mani.db import (
    exercises as exercises_db,
    llm_calls,
    messages as messages_db,
    profiles,
    threads,
)
from mani.errors import ErrorCategory, ServiceError
from mani.llm import client, schema
from mani.llm.schema import LibrarySection, Moment, Reply, SmartPrompt
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

def _handoff() -> list[SmartPrompt]:
    return [
        SmartPrompt(label=CHAT_MORE_LABEL),
        SmartPrompt(label=GO_TO_LIBRARY_LABEL, library=LibrarySection.HOME.value),
    ]


def _awaiting_place(history: list[Message]) -> bool:
    """Whether Mani's last reply asked where in the body they feel it, and it is unanswered."""
    last = next((m for m in reversed(history) if m.role is MessageRole.MANI), None)
    return bool(last and any(
        str(o.get("label", "")) in repairs.PLACE_LABELS for o in (last.prompt_options or [])
    ))


def _body_route(
    fixed: repairs.Repaired,
    body: str | None,
    tapped: SmartPrompt | None,
    technique: TechniqueState | None,
    framework: Framework,
    history: list[Message],
    style: str,
) -> repairs.Repaired:
    """The body route's turn, from the branch the reply reports (spec 0003's transition table). A
    tapped place decides by itself. The two choices, Chat More and Go to Library, come with a
    decline or an action they already know, and on the turn the framework retires unless they were
    just shown; never from reading the reply's words."""
    if technique is None:
        at = "retiring"
    else:
        at = "closing" if technique.phase == framework.closing else technique.phase
    if tapped is not None and tapped.label in repairs.PLACE_LABELS and _awaiting_place(history):
        body = repairs.PLACE_LABELS[tapped.label]
    if body is not None and not repairs.body_answer_fits(body, at, style):
        fixed = dataclasses.replace(fixed, notes=fixed.notes + [f"ignored body {body} at {at}"])
        body = None
    handoff = False
    if body is not None:
        step = repairs.body_reply(body, at, framework.stages, style, fixed.text)
        fixed = dataclasses.replace(
            fixed,
            text=step.text,
            prompts=[SmartPrompt(label=label) for label in step.labels],
            framework_id=framework.id if technique else None,
            phase=step.phase if technique else None,
        )
        handoff = step.handoff
    elif at == "closing" and fixed.phase == "somatic_checkin":
        # The client's flow (2026-09-24): the body check-in is fixed content, sent word for word.
        script = ((framework.stages.get("somatic_checkin") or {}).get("ask") or {}).get(style)
        if script:
            fixed = dataclasses.replace(fixed, text=repairs.with_the_check_in(fixed.text, script))
    if at == "retiring":
        handoff = not _offered_handoff(history)
    return dataclasses.replace(fixed, prompts=_handoff()) if handoff else fixed


def _stage_in_force(
    framework: Framework | None,
    technique: TechniqueState | None,
    *,
    accepted_this_turn: bool,
) -> reply_checks.StageInForce | None:
    """The stage this reply starts from, as [ctx] shows it: the first after the offer on the turn
    they say yes, otherwise the stage in force."""
    if framework is None or technique is None:
        return None
    if accepted_this_turn:
        index = framework.phase_index(OFFERING) + 1
        asked = False
    elif technique.outcome is TechniqueOutcome.ACCEPTED and technique.phase:
        index = framework.phase_index(technique.phase)
        asked = True
    else:
        return None
    if not 0 < index < len(framework.phases):
        return None
    return reply_checks.StageInForce(framework.id, framework.phases[index], asked)


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
    # The draft's stage ledger, as rows. Only with AI_DEBUG_MODE, like the reasoning.
    ledger: list[dict] | None = None
    # What the reply missed that code cannot fix (reply_checks.misses), for the logs and the
    # scenario check; never sent to a client.
    checks: list[str] = field(default_factory=list)
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
    reported: str | None,
    outcome: TechniqueOutcome | None,
    live: TechniqueState | None,
    starting: str | None,
) -> str | None:
    """Which framework this turn's outcome belongs to, when there is one to record.

    The one starting this turn, by a tap or a yes; the offer that was live, for a decline, since
    once the person says no there is no technique left to report; otherwise the one the model
    reported for the stage it asks.
    """
    if outcome is None:
        return None
    if starting:
        return starting
    if outcome is TechniqueOutcome.DECLINED and live is not None:
        return live.framework_id
    return reported


def _offer_answer(
    moment: Moment, tapped: SmartPrompt | None, reply: Reply, *, guarded: bool
) -> str | None:
    """How they answered the open offer. A tap on its buttons decides by itself; otherwise it is
    the model's offer_answer, never read on a safety concern."""
    if moment is Moment.OFFER_OPEN and tapped is not None:
        if tapped.decline:
            return "no"
        if tapped.label.strip().lower() in EXPLAIN_LABELS:
            return "asked"
    return None if guarded else reply.offer_answer


def _answered_offer(
    fixed: repairs.Repaired,
    answer: str | None,
    framework: Framework | None,
    style: str,
    their_words: str | None,
) -> repairs.Repaired:
    """The client's text for an answer to the open offer: what it involves when they asked, with
    the offer again, and their Keep chatting question on a no. A yes and anything else keep the
    model's own text."""
    if framework is None:
        return fixed
    if answer == "asked":
        return dataclasses.replace(
            fixed,
            text=repairs.explanation(framework, style),
            prompts=repairs.offer_buttons(framework.id, explained=True),
        )
    if answer == "no":
        said = repairs.keep_chatting(framework, style, their_words)
        if said is None:
            return dataclasses.replace(fixed, notes=fixed.notes + ["keep chatting unusable: no their_words"])
        return dataclasses.replace(fixed, text=said)
    return fixed


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

    # One turn at a time per conversation, held until this turn's transaction ends. A second
    # message sent while the first is still waiting on the model (a person re-sending after a
    # long wait, a double tap) waits here and then reads the first reply. Without it both turns
    # read the same history and asked the same question twice (2026-10-09).
    await conn.execute(
        "select pg_advisory_xact_lock(hashtextextended($1, 1))", f"thread:{thread_id}"
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
        and not _awaiting_place(history)
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
    # is not running, so it is not the live row.
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

    # Mani's last reply offered and they typed rather than tapped. How they answered is the
    # model's offer_answer, so the decision waits for the reply.
    deferred = offer is not None and tapped is None and outcome is TechniqueOutcome.OFFERED

    # The deterministic screen runs on every turn, before the model is asked anything. It
    # costs nothing and cannot be skipped for budget reasons. Crisis short-circuits the model
    # call entirely; concern only holds the framework and any offer, so the model still answers.
    assessment = safety.screen(content)
    if assessment.level is safety.Level.CRISIS:
        return await _handle_crisis(
            conn, ctx, content,
            reason=f"safety screen: {assessment.category.value if assessment.category else 'unspecified'}",
            reply_text=safety.protocol_for(assessment.category),
            tapped=tapped, client_message_id=client_message_id, settings=settings,
            updates=updates,
        )

    # Which framework fits is the model's call, from the Framework Index; code owns only when an
    # offer may come. repairs.apply still checks whatever is offered.
    running_framework = config.registry.get(technique.framework_id) if technique else None

    wants_title = (
        ctx.thread.message_count >= TITLE_AFTER_MESSAGES and not ctx.thread.title
    )
    conversation_style = context.resolve_style(ctx)
    if not ctx.thread.conversation_style:
        # They typed past the greeting's style buttons, so the profile or the default speaks.
        logger.info("thread %s chose no style; composing in %s", ctx.thread.id, conversation_style)
    system = composer.compose(
        config,
        ctx.profile,
        style=conversation_style,
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
        framework_starting=accepted_this_turn,
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

    window = context.offer_window(ctx)
    # The reply's shape is chosen from the database: while no offer may be made there is no offer
    # field, so the model cannot offer early, and an answer to an offer exists only while one is
    # open or was declined.
    moment = context.moment(
        technique, outcome, retiring_framework_id, _awaiting_place(history), running_framework,
        concern=assessment.blocks_framework,
    )
    declined_row = (
        technique is None and ctx.technique is not None
        and ctx.technique.outcome is TechniqueOutcome.DECLINED
    )
    reply_shape = schema.reply_for(
        moment,
        may_offer=window != "not_yet",
        declined_row=declined_row,
        on_closing=bool(
            running_framework and technique and technique.phase == running_framework.closing
        ),
        slots=repairs.slots_for(
            config.registry, conversation_style,
            technique.framework_id if moment is Moment.OFFER_OPEN else None,
        ),
    )
    call = await client.complete(
        [{"role": "system", "content": system.text}]
        + _conversation(history)
        + [{"role": "user", "content": prefix + for_model}],
        reply_shape,
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
    reply = schema.as_reply(call.value)
    framework_going = ctx.technique is not None and ctx.technique.outcome is TechniqueOutcome.ACCEPTED
    # Every reply before an offer asks one question, so the conversation keeps moving. Not while
    # the questions run (each stage asks its own), not on a safety concern, and not when the draft
    # itself chose a shape that asks nothing, which is how it answers someone who only wants to be heard.
    needs_question = not framework_going and not assessment.blocks_framework
    last_mani_text = next((m.content for m in reversed(history) if m.role is MessageRole.MANI), None)
    if reply.heading_toward:
        # Read by the steering evals and by anyone asking why a question went where it did:
        # the id only, never a word of what the person said.
        logger.info("thread %s heading toward %s", ctx.thread.id, reply.heading_toward)
    if reply.stages_known:
        # Which stages the model judged already answered: ids and verdicts only, never their words.
        logger.info(
            "thread %s stages known: %s", ctx.thread.id,
            ", ".join(f"{e.stage}={'met' if e.met else 'open'}" for e in reply.stages_known),
        )

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

    # A concern, from the screen or the model, comes before anything a reply field could do: no
    # client text is rendered from them and no row changes because of them (AC-12).
    guarded = assessment.blocks_framework or model_concern
    answer = _offer_answer(moment, tapped, reply, guarded=guarded)
    if moment is Moment.OFFER_OPEN and not (guarded and tapped is None):
        if answer == "yes":
            outcome = TechniqueOutcome.ACCEPTED
            accepted_this_turn = True
            offered_now.append(technique.framework_id)
        elif answer != "asked":
            # Anything but a yes or a question about it is Keep chatting (muhammad, 2026-09-24),
            # held here rather than left to the model, which kept asking again.
            outcome = TechniqueOutcome.DECLINED
    elif declined_row and answer == "yes":
        # They came back and asked for the one they turned down: that is a yes, cooldown or
        # not, since the cooldown only keeps Mani from asking again.
        technique = ctx.technique
        outcome = TechniqueOutcome.ACCEPTED
        accepted_this_turn = True
        offered_now.append(technique.framework_id)

    # The step is written after the text, so where it disagrees with the draft's own ledger it is
    # the label that is wrong; code sets it rather than asking the model again.
    in_force = None if guarded else _stage_in_force(
        config.registry.get(technique.framework_id) if technique else None,
        technique, accepted_this_turn=accepted_this_turn,
    )
    stage_framework = config.registry.get(in_force.framework_id) if in_force else None
    if stage_framework is not None:
        stepped = reply_checks.with_ledger_step(reply, stage_framework, in_force)
        if stepped is not reply:
            logger.info(
                "thread %s step %s set to %s from its own ledger",
                ctx.thread.id, reply.state.step, stepped.state.step,
            )
            reply = stepped

    fixed = repairs.apply(
        reply,
        config.registry,
        moment=moment,
        may_offer=window != "not_yet",
        # Only the framework they have just finished is off the table. One they said no to
        # may come back once the cooldown has passed (muhammad, 2026-09-24).
        finished_framework_id=ctx.technique.framework_id if _finished(ctx.technique) else None,
        current_framework_id=(
            technique.framework_id
            if technique and outcome is not TechniqueOutcome.DECLINED
            else None
        ),
        current_phase=technique.phase if technique else None,
        accepted_this_turn=accepted_this_turn,
        framework_running=outcome is TechniqueOutcome.ACCEPTED,
        conversation_style=conversation_style,
        wants_title=wants_title,
        guarded=guarded,
        nickname=ctx.profile.nickname if ctx.profile else None,
        # The greeting says their name by design; the model's own replies count from there.
        name_said_before=bool(
            ctx.profile and ctx.profile.nickname
            and any(ctx.profile.nickname in m.content
                    for m in [m for m in history if m.role is MessageRole.MANI][1:])
        ),
        clarification_already_used=context.clarification_used(history),
    )
    if moment is Moment.OFFER_OPEN and not guarded:
        fixed = _answered_offer(
            fixed, answer, config.registry.get(technique.framework_id), conversation_style,
            reply.their_words,
        )
    if guarded:
        # A concern pauses the framework rather than ending it: nothing this reply reports
        # about a stage is applied, and it may not open a new one. The stored state is left
        # exactly as it was, so the framework resumes from there once the concern has passed.
        fixed = dataclasses.replace(fixed, framework_id=None, phase=None, prompts=[])
    if moment is Moment.BODY and not guarded:
        fixed = _body_route(
            fixed, reply.body, tapped, technique,
            config.registry.get(technique.framework_id if technique else retiring_framework_id),
            history, conversation_style,
        )
    if fixed.notes:
        logger.info("repaired reply on thread %s: %s", ctx.thread.id, "; ".join(fixed.notes))

    offered = next((p.technique for p in fixed.prompts if p.technique), None)
    checks = reply_checks.misses(
        reply,
        offered=offered,
        offer_dropped=fixed.offer_dropped,
        offer_due=window == "due" and not assessment.blocks_framework and not deferred,
        needs_question=needs_question,
        last_mani_text=last_mani_text,
    )
    if checks:
        logger.info("thread %s reply checks: %s", ctx.thread.id, "; ".join(checks))
    # What the model judged this turn, as the closed values only: never a slot, which holds their words.
    logger.info(
        "thread %s moment %s: offer_answer %s, body %s, offered %s",
        ctx.thread.id, moment.value, answer, reply.body, offered,
    )
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
    starting = None
    if accepted_this_turn:
        starting = tapped.technique if tapped and tapped.technique else technique.framework_id
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
    elif (decided := _decided_framework(fixed.framework_id, outcome, technique, starting)) is not None:
        updates.retire_technique = False
        updates.technique = TechniqueState(
            thread_id=ctx.thread.id,
            framework_id=decided,
            outcome=outcome,
            # A framework starting this turn sits at the offer until the reply names a stage.
            phase=(
                None if outcome is TechniqueOutcome.DECLINED
                else fixed.phase or (OFFERING if starting else None)
            ),
            at_message_count=(
                technique.at_message_count
                if technique and outcome is not TechniqueOutcome.DECLINED
                else count_after
            ),
            library_offered_since=False,
        )
        if accepted_this_turn:
            updates.offer_frameworks.append(decided)

    if library_offer is not None:
        updates.library_offered = True
    if fixed.style is not None:
        updates.style = ResponseStyle(shape=fixed.style.shape)
    if fixed.title:
        updates.title = fixed.title

    await threads.apply(conn, ctx.thread.id, user_id, updates)

    exercise = None
    if retiring_framework_id is not None:
        said = [m.content for m in history if m.role is MessageRole.USER][-2:] + [content]
        exercise = await _offer_exercise(
            conn, retiring_framework_id, config, model, routing, user_id, ctx.thread.id,
            reasoning_effort=parameters.get("reasoning_effort"),
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
        checks=checks,
        ledger=(
            reply_checks.ledger_view(
                reply, config.registry.get(reply.state.technique) if reply.state else running_framework,
            )
            if settings.ai_debug_mode and reply.stages_known
            else None
        ),
    )


async def _offer_exercise(
    conn: asyncpg.Connection,
    framework_id: str,
    config,
    model: str,
    routing: dict | None,
    user_id: str,
    thread_id: uuid.UUID,
    *,
    reasoning_effort: str | None,
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
        reasoning_effort=reasoning_effort,
        said=said,
        current_issue=current_issue,
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
