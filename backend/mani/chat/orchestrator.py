# ABOUTME: One user message from arrival to stored reply: context, one model call, writes.
# ABOUTME: Everything it writes lands in the caller's transaction, or none of it does.

from __future__ import annotations

import dataclasses
import logging
import uuid
from dataclasses import dataclass, field

import asyncpg

from mani.auth.jwt import Claims
from mani.chat import body as body_route, context, converse, picture, repairs, reply_checks, safety, understanding, walk
from mani.chat.greeting import (
    EXPLAIN_LABELS,
    OPENERS,
    STYLE_OPTIONS,
    greeting,
)
from mani.chat.techniques import OFFERING
from mani.config import get_settings
from mani.db import (
    llm_calls,
    messages as messages_db,
    profiles,
    threads,
)
from mani.errors import ErrorCategory, ServiceError
from mani.llm import client, schema
from mani.llm.schema import LibrarySection, Moment, Reply, SmartPrompt
from mani.models.rows import (
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

def _prompts(buttons: list[body_route.Button]) -> list[SmartPrompt]:
    return [
        SmartPrompt(label=b.label, library=LibrarySection.HOME.value if b.library else None) for b in buttons
    ]


def _body_route(
    fixed: repairs.Repaired,
    value: str | None,
    options: str | None,
    tapped: SmartPrompt | None,
    technique: TechniqueState | None,
    framework: Framework,
    area: str | None,
) -> tuple[repairs.Repaired, body_route.Step | None]:
    """The body check-in's turn: the client's script for the answer at this step. A tapped button decides
    by itself; a typed answer is the value the reply read from it. Anywhere an answer does not fit, the
    reply stands as the model wrote it. `area` is the place the question before the first step asked about."""
    at = body_route.RETIRING if technique is None else technique.phase
    if tapped is not None and (decided := body_route.tapped_value(at, tapped.label, framework.stages)):
        value = decided
    if at == body_route.RETIRING and value != "finish":
        # Keep Chatting, tapped or typed: the model's own continuation, with its possibilities under the question.
        fixed = dataclasses.replace(fixed, text=repairs.under(fixed.text, options))
    if value is None:
        return fixed, None
    step = body_route.step(
        at, value, framework.stages,
        physical_response=technique.physical_response if technique else None, area=area,
    )
    if step is None:
        return dataclasses.replace(fixed, notes=fixed.notes + [f"ignored body {value} at {at}"]), None
    return dataclasses.replace(
        fixed,
        text=step.text if step.text is not None else fixed.text,
        prompts=_prompts(step.buttons),
        framework_id=framework.id if technique else None,
        phase=step.phase if technique else None,
    ), step


def _feelings(understood: dict[str, str]) -> str:
    """The feelings they named before the framework."""
    return understood.get("feeling", "")


def _case_words(understood: dict[str, str]) -> str:
    """What they feel and the case they confirmed, in their words: what a flagged stage's question carries."""
    return " ".join(understood.get(key, "") for key in ("feeling", "case"))


def _walked(
    fixed: repairs.Repaired,
    reply: Reply,
    framework: Framework,
    stored: dict[str, dict],
    *,
    start: bool,
    in_force: str | None,
    style: str,
    thread_id: uuid.UUID,
    feeling: str | None,
    seen_before: dict | None = None,
    seen_after: dict | None = None,
) -> tuple[repairs.Repaired, walk.Walked]:
    """The walk's turn: what they said merged into the store, the stages already passed brought up to date with
    what the picture of them gained (`seen_before` to `seen_after`), the step taken, and the reply that opens the
    stage reached, from the reply's judgement of that stage in next_stage. Code decides all of it."""
    if start:
        walked = walk.start(framework, reply.stage_updates, reply.next_stage)
    else:
        walked = walk.advance(
            framework, stored, reply.stage_updates, reply.stage_answer,
            in_force=in_force, report=reply.next_stage,
        )
        synced, sync_notes = walk.from_picture(framework, walked.entries, seen_before, seen_after, in_force=in_force)
        walked = dataclasses.replace(walked, entries=synced, notes=walked.notes + sync_notes)
    text, notes = walk.reply_text(
        framework, walked, text=fixed.text, style=style, thread_id=thread_id,
        feeling=feeling if start else None, options=reply.options,
    )
    return dataclasses.replace(
        fixed, text=text, framework_id=framework.id, phase=walked.phase,
        notes=fixed.notes + walked.notes + notes,
    ), walked


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
    # The stage store after this turn, as rows. Only with AI_DEBUG_MODE, like the reasoning.
    ledger: list[dict] | None = None
    # Each content stage's id and stored status after this turn, and whether the reply is on it, for
    # the scenario check; never their words, and never sent to a client.
    stage_trace: list[dict] | None = None
    # What the reply missed that code cannot fix (reply_checks.misses), for the logs and the
    # scenario check; never sent to a client.
    checks: list[str] = field(default_factory=list)
    # What Mani understands of them after this turn. Sent to a client only with AI_DEBUG_MODE.
    understanding: dict | None = None
    # When Mani's latest check was made, after this turn (spec 0006). Sent only with AI_DEBUG_MODE.
    check_at_message_count: int | None = None


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


def _name_said_before(ctx: threads.TurnContext, history: list[Message], window) -> bool:
    """Whether Mani already said their name. The greeting says it by design; the model's own replies count
    from there. The greeting is the first message in view only while nothing has left the window."""
    return bool(
        ctx.profile and ctx.profile.nickname
        and any(ctx.profile.nickname in m.content
                for m in [m for m in history if m.role is MessageRole.MANI][0 if window.dropped else 1:])
    )


async def _converse(
    conn: asyncpg.Connection,
    ctx: threads.TurnContext,
    *,
    for_model: str,
    content: str,
    tapped: SmartPrompt | None,
    history: list[Message],
    window,
    config: cache.Config,
    conversation_style: str,
    wants_title: bool,
    client_message_id: uuid.UUID | str | None,
    settings,
    updates: threads.ThreadUpdates,
    declined: Framework | None = None,
) -> Turn:
    """One turn of Mani's own conversation, when no framework, offer or check is open: the conversation
    prompt, the transcript and their message, and a note saying what the conversation cannot show. The
    reply's text is what Mani says, its check included; code only decides whether a check is stored, and,
    after they stepped out of `declined`, whether asking for it again offers it with its buttons."""
    allowed = converse.check_allowed(ctx)
    system = composer.compose_conversation(
        config, ctx.profile, should_generate_title=wants_title,
        summary=ctx.summary if window.dropped else None, memory=ctx.memory,
    )
    model, parameters, routing = composer.model_settings(config, "voice")
    note = converse.note(
        conversation_style, allowed=allowed, due=understanding.ready(ctx.thread.understanding),
        wants_title=wants_title, understood=ctx.thread.understanding, recent_crisis=ctx.recent_crisis,
        stepped_out_of=declined.name if declined else None, asked=converse.asked_before(history),
    )
    call = await client.complete(
        [{"role": "system", "content": system.text}]
        + _conversation(history)
        + [{"role": "user", "content": for_model}, {"role": "system", "content": note}],
        schema.ConversationReply,
        model=model,
        purpose=llm_calls.Purpose.CHAT,
        temperature=parameters.get("temperature", client.DEFAULT_TEMPERATURE),
        max_tokens=parameters.get("maxTokens", client.DEFAULT_MAX_TOKENS),
        reasoning_effort=parameters.get("reasoning_effort"),
        routing=routing,
        user_id=ctx.thread.user_id,
        thread_id=ctx.thread.id,
        prompt_version_id=None,
    )
    reply = call.value
    # As on every other turn, the model's own crisis judgment does not lock the thread (the deterministic
    # screen does); it holds the check and keeps what is understood as it was.
    guarded = reply.crisis is not None
    if guarded:
        logger.info("model reported a safety concern on thread %s: %s", ctx.thread.id, reply.crisis.reason)
    check_written = not guarded and converse.checked(reply, allowed=allowed)
    their_messages = [m.content for m in history if m.role is MessageRole.USER] + [content]
    understood = (
        ctx.thread.understanding if guarded
        else converse.understood_after(
            ctx.thread.understanding, reply, check_written=check_written, their_messages=their_messages,
        )
    )
    if understood != ctx.thread.understanding:
        updates.understanding = understood
    if check_written:
        updates.check_at_message_count = ctx.thread.message_count + 2
    logger.info(
        "thread %s conversation turn: heart %s, check allowed %s, checked %s, helping %s",
        ctx.thread.id, reply.heart, allowed, check_written, bool(understood.get(converse.HELPING)),
    )

    fixed = repairs.apply(
        Reply(text=reply.text, title=reply.title),
        config.registry,
        moment=Moment.CHATTING,
        confirmed=False,
        conversation_style=conversation_style,
        wants_title=wants_title,
        nickname=ctx.profile.nickname if ctx.profile else None,
        name_said_before=_name_said_before(ctx, history, window),
        chat_text=not guarded,
    )
    if fixed.notes:
        logger.info("repaired reply on thread %s: %s", ctx.thread.id, "; ".join(fixed.notes))
    # Counted, never fixed: a question asked again, or a reply that asks nothing before the check.
    checks = reply_checks.misses(
        Reply(text=reply.text),
        offered=None,
        offer_dropped=None,
        needs_question=not guarded and not check_written,
        last_mani_text=next((m.content for m in reversed(history) if m.role is MessageRole.MANI), None),
    )
    if checks:
        logger.info("thread %s reply checks: %s", ctx.thread.id, "; ".join(checks))
    if not fixed.text.strip():
        raise ServiceError(
            f"reply on thread {ctx.thread.id} was empty after repair",
            ErrorCategory.LLM_UNAVAILABLE,
            retryable=True,
            user_message="Mani had trouble responding. Please try again.",
        )

    prompts: list[SmartPrompt] = []
    if declined is not None and reply.back_to_framework and not guarded and not check_written:
        # They asked to go back to the set they stepped out of: it is offered again, Try it starts it.
        prompts = repairs.offer_buttons(declined.id, explained=True)
        updates.retire_technique = False
        updates.technique = TechniqueState(
            thread_id=ctx.thread.id, framework_id=declined.id, outcome=TechniqueOutcome.OFFERED,
            phase=OFFERING, at_message_count=ctx.thread.message_count + 2,
        )
        updates.offer_frameworks.append(declined.id)
        updates.reset_outcomes = True
    pair = await messages_db.create_pair(
        conn, ctx.thread.id, content, fixed.text,
        selected_prompt=tapped.label if tapped else None,
        prompt_options=[p.model_dump(mode="json", exclude_none=True) for p in prompts] or None,
        client_message_id=client_message_id,
    )
    if fixed.title:
        updates.title = fixed.title
    await threads.apply(conn, ctx.thread.id, ctx.thread.user_id, updates)

    summarized = ctx.summary.summarized_message_count if ctx.summary else 0
    return Turn(
        message_id=pair.mani_message_id,
        content=fixed.text,
        created_at=pair.created_at,
        prompts=prompts,
        title=fixed.title or ctx.thread.title,
        crisis_detected=False,
        crisis_blocks_chat=settings.crisis_blocks_chat,
        was_duplicate=pair.was_duplicate,
        needs_summary=window.dropped > summarized,
        llm_call_id=call.call_id,
        checks=checks,
        understanding=understood,
        check_at_message_count=(
            updates.check_at_message_count
            if updates.check_at_message_count is not None
            else ctx.thread.check_at_message_count
        ),
    )


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
    # The whole thread within the budget: the model sees what they said earlier, instead of a store
    # guessing it ahead of time (2026-10-13).
    window = await messages_db.for_context(
        conn, thread_id, user_id, budget_chars=settings.context_budget_chars,
    )
    history = window.messages
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
    # is not running, so it is not the live row.
    technique = context.live(technique)

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
        # Only once messages have left the window, so it never repeats what the model reads raw.
        summary=ctx.summary if window.dropped else None,
        memory=ctx.memory,
    )
    model, parameters, routing = composer.model_settings(config)

    # The framework this turn starts, when that is known before the reply: a Try it tap, or a yes
    # whose turn was guarded, which left the row accepted at the offer. A typed yes sets it below.
    starting: str | None = None
    if accepted_this_turn:
        starting = tapped.technique
    elif technique is not None and outcome is TechniqueOutcome.ACCEPTED and technique.phase == OFFERING:
        starting = technique.framework_id
    declined_row = (
        technique is None and ctx.technique is not None
        and ctx.technique.outcome is TechniqueOutcome.DECLINED
    )
    active_framework = config.registry.get(technique.framework_id) if technique else None
    prefix = context.build(
        ctx, framework=active_framework,
        history=history, safety_concern=assessment.blocks_framework, offer_waiting=deferred,
        starting=starting is not None,
        # A typed yes to the open offer, or asking for the set they declined, starts it.
        yes_framework=(
            active_framework if deferred
            else config.registry.get(ctx.technique.framework_id) if declined_row
            else None
        ),
        # Where the questions ended, for the turn that answers the closing choices.
        landed_on=(
            walk.landed_on(finished, ctx.technique.stages_known.get(retiring_framework_id) or {})
            if retiring_framework_id and (finished := config.registry.get(retiring_framework_id)) else None
        ),
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

    # The reply's shape is chosen from the database: the offer field exists only on the answer to
    # Mani's check, so the model cannot offer before they confirm its understanding, and an answer
    # to an offer exists only while one is open or was declined (spec 0006).
    moment = context.moment(
        technique, outcome, retiring_framework_id,
        concern=assessment.blocks_framework, check_open=context.check_open(ctx),
    )
    if moment is Moment.CHATTING:
        # No framework, offer or check is open: Mani's own conversation, in the client's cadence. After they
        # stepped out of a framework, it can be offered again when they ask for it.
        return await _converse(
            conn, ctx, for_model=for_model, content=content, tapped=tapped, history=history, window=window,
            config=config, conversation_style=conversation_style, wants_title=wants_title,
            client_message_id=client_message_id, settings=settings, updates=updates,
            declined=config.registry.get(ctx.technique.framework_id) if declined_row else None,
        )
    if moment is Moment.IN_STAGES:
        # A turn on a framework's stages speaks in the same voice as the chat; the stage arrives in [ctx].
        system = composer.compose_framework(
            config, ctx.profile, should_generate_title=wants_title,
            summary=ctx.summary if window.dropped else None, memory=ctx.memory,
        )
        model, parameters, routing = composer.model_settings(config, "voice")
    reply_shape = schema.reply_for(
        moment,
        declined_row=declined_row,
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
    if reply.stage_updates:
        # Which stages the reply reports words for: ids and statuses only, never their words.
        logger.info(
            "thread %s stage updates: %s", ctx.thread.id,
            ", ".join(f"{u.stage}={u.status}" for u in reply.stage_updates),
        )
    if reply.next_stage:
        logger.info("thread %s next stage judged %s", ctx.thread.id, reply.next_stage.status)

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
    if (
        reply.stage_answer == "stop" and not guarded and starting is None
        and outcome is TechniqueOutcome.ACCEPTED and technique is not None
        and running_framework is not None
        and technique.phase in walk.content_stages(running_framework)
    ):
        # Only they can end the questions: a clear wish to stop leaves the framework as declined, so
        # it comes back only if they ask for it again. Not knowing never ends it.
        outcome = TechniqueOutcome.DECLINED
    if moment is Moment.OFFER_OPEN and not (guarded and tapped is None):
        if answer == "yes":
            outcome = TechniqueOutcome.ACCEPTED
            accepted_this_turn = True
            starting = technique.framework_id
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
        starting = technique.framework_id
        offered_now.append(technique.framework_id)

    # Nothing a concern turn reports is kept, so what they understand stays as stored. Mani's check is made only
    # in its own conversation (_converse); here the picture and the heart of it are merged.
    understood = ctx.thread.understanding
    if not guarded:
        understood = understanding.merge(ctx.thread.understanding, reply.picture, reply.heart)
    if retiring_framework_id is not None:
        # The framework that just finished worked through this reading. The next check waits for a fresh one, so
        # Mani never checks again straight away on the case it has just finished.
        understood = {key: value for key, value in understood.items() if key not in ("heart", converse.HELPING)}
    if understood != ctx.thread.understanding:
        updates.understanding = understood
    # A clear yes to the check is the only way to an offer (spec 0006, AC-1, AC-4). Only ABCDE and Thought Reframe
    # are offered, and only for what they tell themselves: a yes about something really happening turns the
    # conversation to helping instead (muhammad, 2026-10-27).
    real_situation = (understood.get(picture.KEY) or {}).get("problem_type") == "situation"
    confirmed = (
        moment is Moment.CHECK_OPEN and not guarded and starting is None
        and reply.check_answer == "yes" and not real_situation
    )
    if moment is Moment.CHECK_OPEN and not guarded and reply.check_answer == "yes" and real_situation:
        understood = {**understood, converse.HELPING: True}
        updates.understanding = understood

    fixed = repairs.apply(
        reply,
        config.registry,
        moment=moment,
        confirmed=confirmed,
        conversation_style=conversation_style,
        wants_title=wants_title,
        guarded=guarded,
        nickname=ctx.profile.nickname if ctx.profile else None,
        # The greeting says their name by design; the model's own replies count from there. The
        # greeting is the first message in view only while nothing has left the window.
        name_said_before=_name_said_before(ctx, history, window),
        feeling=understood.get("feeling"),
        # Mani's own text before a framework, which may carry an options line under it.
        chat_text=(
            moment in (Moment.CHATTING, Moment.CHECK_OPEN, Moment.OFFER_OPEN)
            and starting is None and not guarded
        ),
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
    # The walk runs on the turn a framework starts and on each of its stages, never on a guarded
    # turn: that leaves the store and the phase exactly as they were (AC-10).
    stored_all = ctx.technique.stages_known if ctx.technique else {}
    walking = (
        config.registry.get(starting or technique.framework_id)
        if not guarded and outcome is TechniqueOutcome.ACCEPTED else None
    )
    walked = None
    if walking is not None and (starting or technique.phase in walk.content_stages(walking)):
        fixed, walked = _walked(
            fixed, reply, walking, stored_all.get(walking.id) or {},
            start=starting is not None, in_force=None if starting else technique.phase,
            style=conversation_style, thread_id=ctx.thread.id,
            feeling=understood.get("feeling"),
            seen_before=ctx.thread.understanding.get(picture.KEY), seen_after=understood.get(picture.KEY),
        )
        if not starting:
            # Whether the questions are still helping: stalls counted when nothing new came, and an offer to step
            # out remembered for their answer (muhammad, 2026-10-27).
            fit = reply.framework_fit
            if fit and fit != "helping":
                logger.info("thread %s framework not helping: %s", ctx.thread.id, fit)
            walked = dataclasses.replace(walked, entries=walk.after_turn(
                stored_all.get(walking.id) or {}, walked.entries, technique.phase, moved=walked.phase != technique.phase,
                shift=(understood.get(picture.KEY) or {}).get("shift"),
                offered_exit=fit is not None and fit != "helping",
            ))
        if walked.entries != (stored_all.get(walking.id) or {}):
            updates.stages_known = {**stored_all, walking.id: walked.entries}
        if walked.phase == body_route.CHECK:
            # The last stage was answered: the client's body check-in begins with its first step, asking
            # about a place when what they said before the framework points to one.
            check = body_route.check_for(_feelings(understood), walking.stages)
            text, buttons = body_route.entry(fixed.text, walking.stages, check)
            fixed = dataclasses.replace(
                fixed, text=text, prompts=_prompts(buttons),
                phase=body_route.CHECK if check else body_route.BODY,
            )
    if moment is Moment.BODY and not guarded:
        route = config.registry.get(technique.framework_id if technique else retiring_framework_id)
        asked = (
            body_route.check_for(_feelings(ctx.thread.understanding), route.stages)
            if technique and technique.phase == body_route.CHECK else None
        )
        fixed, step = _body_route(
            fixed, reply.body, reply.options, tapped, technique, route, asked.area if asked else None,
        )
        if step is not None:
            updates.physical_response = step.physical_response
            updates.conversation_effect = step.conversation_effect
    if fixed.notes:
        logger.info("repaired reply on thread %s: %s", ctx.thread.id, "; ".join(fixed.notes))

    offered = next((p.technique for p in fixed.prompts if p.technique), None)
    asked = (walked.reached or walked.phase) if walked is not None else None
    carries_case = asked is not None and bool((walking.stages.get(asked) or {}).get("carries_case"))
    checks = reply_checks.misses(
        reply,
        offered=offered,
        offer_dropped=fixed.offer_dropped,
        needs_question=needs_question,
        last_mani_text=last_mani_text,
        reach_unjudged=walked is not None and walked.unjudged,
        case=_case_words(understood) if carries_case else None,
    )
    if checks:
        logger.info("thread %s reply checks: %s", ctx.thread.id, "; ".join(checks))
    # What the model judged this turn, as the closed values only: never a slot, which holds their words.
    logger.info(
        "thread %s moment %s: check_answer %s, heart %s, offer_answer %s, body %s, stage_answer %s, offered %s",
        ctx.thread.id, moment.value, reply.check_answer, reply.heart, answer, reply.body, reply.stage_answer, offered,
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
    new_offer = next((p for p in fixed.prompts if p.technique), None)

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
        updates.reset_outcomes = True
    elif (decided := _decided_framework(fixed.framework_id, outcome, technique, starting)) is not None:
        updates.retire_technique = False
        updates.technique = TechniqueState(
            thread_id=ctx.thread.id,
            framework_id=decided,
            outcome=outcome,
            # A framework whose start was guarded sits at the offer, and the next turn starts it.
            phase=(
                None if outcome is TechniqueOutcome.DECLINED
                else fixed.phase or (OFFERING if starting else None)
            ),
            at_message_count=(
                technique.at_message_count
                if technique and outcome is not TechniqueOutcome.DECLINED
                else count_after
            ),
        )
        if accepted_this_turn:
            updates.offer_frameworks.append(decided)

    if fixed.style is not None:
        updates.style = ResponseStyle(shape=fixed.style.shape)
    if fixed.title:
        updates.title = fixed.title

    await threads.apply(conn, ctx.thread.id, user_id, updates)

    summarized = ctx.summary.summarized_message_count if ctx.summary else 0
    ledger = walk.ledger_view(walking, walked.entries, walked.phase) if walked else None
    return Turn(
        message_id=pair.mani_message_id,
        content=fixed.text,
        created_at=pair.created_at,
        prompts=fixed.prompts,
        title=fixed.title or ctx.thread.title,
        crisis_detected=False,
        crisis_blocks_chat=settings.crisis_blocks_chat,
        was_duplicate=pair.was_duplicate,
        # A summary is needed only for messages that have left the model's view and that no summary
        # covers yet. Both sides are thread message counts.
        needs_summary=window.dropped > summarized,
        llm_call_id=call.call_id,
        understanding=understood,
        check_at_message_count=(
            updates.check_at_message_count
            if updates.check_at_message_count is not None
            else ctx.thread.check_at_message_count
        ),
        reasoning=reply.reasoning if settings.ai_debug_mode else None,
        checks=checks,
        ledger=ledger if settings.ai_debug_mode else None,
        stage_trace=(
            [{"stage": r["stage"], "status": r["status"], "asking": r["asking"]} for r in ledger]
            if ledger is not None else None
        ),
    )


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
