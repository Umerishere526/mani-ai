# ABOUTME: One user message from arrival to stored reply: context, one model call, writes.
# ABOUTME: Everything it writes lands in the caller's transaction, or none of it does.

from __future__ import annotations

import dataclasses
import logging
import uuid
from dataclasses import dataclass, field

import asyncpg

from mani.auth.jwt import Claims
from mani.chat import body as body_route, context, converse, picture, repairs, reply_checks, rewind, safety, understanding, walk
from mani.chat.greeting import (
    COPIED_BACK,
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
) -> tuple[repairs.Repaired, body_route.Step | None]:
    """The body check-in's turn: the client's script for the answer at this step. A tapped button decides
    by itself; a typed answer is the value the reply read from it. Anywhere an answer does not fit, the
    reply stands as the model wrote it."""
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
        physical_response=technique.physical_response if technique else None,
    )
    if step is None:
        return dataclasses.replace(fixed, notes=fixed.notes + [f"ignored body {value} at {at}"]), None
    text = fixed.text if step.text is None else step.text
    return dataclasses.replace(
        fixed,
        text=text,
        prompts=_prompts(step.buttons),
        framework_id=framework.id if technique else None,
        phase=step.phase if technique else None,
    ), step


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
    their_message: str = "",
) -> tuple[repairs.Repaired, walk.Walked]:
    """The walk's turn: what they said merged into the store, the stages already passed brought up to date with
    what the picture of them gained (`seen_before` to `seen_after`), the step taken, and the reply that opens the
    stage reached, from the reply's judgement of that stage in next_stage. Code decides all of it."""
    if start:
        walked = walk.start(framework, reply.stage_updates, reply.next_stage)
    else:
        answer = walk.held_by_question(reply.stage_answer, their_message)
        walked = walk.advance(
            framework, stored, reply.stage_updates, answer,
            in_force=in_force, report=reply.next_stage,
        )
        if answer != reply.stage_answer:
            walked = dataclasses.replace(
                walked, notes=walked.notes + [f"their message asks something: {reply.stage_answer} held as not_yet"],
            )
        if not walk.new_view(framework, in_force):
            synced, sync_notes = walk.from_picture(
                framework, walked.entries, seen_before, seen_after, in_force=in_force,
            )
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
    # What code decided this turn and why, for admin.turn_traces: ids, statuses, closed values and code's notes,
    # never their words (_trace). Sent to a client only with AI_DEBUG_MODE.
    trace: dict | None = None
    # The model's whole structured reply, which carries their words: kept only with AI_DEBUG_MODE, for
    # turn_traces.RAW_REPLY_DAYS.
    raw_reply: dict | None = None
    # What Mani reads of them once the reply is sent (read_understanding), on a chat turn only.
    read_after: "ReadAfter | None" = None


@dataclass
class ReadAfter:
    """The reading a chat turn asks for after its reply is sent: the call's messages and settings, and what the record
    needs to say whether the conversation presses toward the framework."""

    thread_id: uuid.UUID
    user_id: uuid.UUID
    messages: list[dict[str, str]]
    model: str
    parameters: dict
    routing: dict | None
    their_messages: list[str]


def _trace(**fields) -> dict:
    """A turn's trace with what is empty left out. Only ids, statuses, closed values, counts and code's own notes go
    in: never their words, which only the raw reply, kept in debug, carries."""
    return {key: value for key, value in fields.items() if value not in (None, "", [], {})}


def _stage_reports(reply) -> dict:
    """What the reply reported about the stages, without the words it reported for them."""
    return _trace(
        stage_answer=reply.stage_answer,
        stage_updates=[
            _trace(stage=u.stage, status=u.status, corrected=u.corrected, gap=u.gap) for u in reply.stage_updates or []
        ],
        next_stage=_trace(status=reply.next_stage.status, gap=reply.next_stage.gap) if reply.next_stage else None,
        framework_fit=reply.framework_fit,
    )


def _raw(reply, settings) -> dict | None:
    """The model's reply as it came back, only with AI_DEBUG_MODE."""
    return reply.model_dump(mode="json", exclude_none=True) if settings.ai_debug_mode else None


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
    reply's text is what Mani says. On a turn that may move to the set of questions, a reply that moves sends
    the client's offer, with no check before it (the client meeting, 2026-11-03); after they stepped out of
    `declined`, asking for it again offers it with its buttons."""
    allowed = converse.check_allowed(ctx)
    slots = repairs.slots_for(config.registry, conversation_style, None) if allowed else schema.Slots()
    system = composer.compose_conversation(
        config, ctx.profile, should_generate_title=wants_title,
        summary=ctx.summary if window.dropped else None, memory=ctx.memory,
    )
    model, parameters, routing = composer.model_settings(config)
    note = converse.note(
        conversation_style, allowed=allowed, due=understanding.ready(ctx.thread.understanding),
        wants_title=wants_title, understood=ctx.thread.understanding, recent_crisis=ctx.recent_crisis,
        # A correction at the offer is not stepping out of it: the note says so on its own line.
        stepped_out_of=(
            declined.name if declined and not ctx.thread.understanding.get(converse.CORRECTED) else None
        ),
        asked=context.asked_before(history), last_question=context.last_question(history),
        their_count=context.their_messages(ctx), latest=content,
        frameworks=composer.framework_index(config.registry) if allowed else None,
    )
    call = await client.complete(
        [{"role": "system", "content": system.text}]
        + _conversation(history)
        + [{"role": "user", "content": for_model}, {"role": "system", "content": note}],
        schema.conversation_reply_for(may_move=allowed, slots=slots),
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
    # The reply moves to the set of questions; its offer is made below, and nothing waits for a check's answer.
    moving = not guarded and converse.checked(reply, allowed=allowed)
    their_messages = [m.content for m in history if m.role is MessageRole.USER] + [content]
    understood = (
        ctx.thread.understanding if guarded
        else converse.replied(ctx.thread.understanding, reply, check_written=moving)
    )
    logger.info(
        "thread %s conversation turn: shape %s, move %s, needs info %s, insight %s, asks %s, heart %s, check allowed %s, "
        "moves to the set %s, toward framework %s",
        ctx.thread.id, reply.shape, reply.move, reply.needs_info, bool(reply.insight), "?" in reply.text, reply.heart,
        allowed, moving, bool(understood.get(converse.TOWARD)),
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
    offering: str | None = None
    dropped: str | None = None
    prompts: list[SmartPrompt] = []
    if moving:
        # The client's offer in place of a check (the client meeting, 2026-11-03). When it cannot be made, the
        # reply's own text goes and nothing is offered; the next turn may move again.
        said, buttons, offering, dropped = repairs.transition_offer(
            fixed.text, getattr(reply, "offer", None), getattr(reply, "heading_toward", None), config.registry,
            conversation_style,
            feeling=picture.core(understood.get(picture.KEY)).get("belief") or understood.get("feeling"),
        )
        if said is None:
            logger.info("thread %s offer unusable on the move to the set: %s", ctx.thread.id, dropped)
        else:
            fixed = dataclasses.replace(fixed, text=said)
            prompts = buttons
            logger.info("thread %s heading toward %s", ctx.thread.id, offering)
    if offering is not None:
        # Offered: a correction they made earlier is answered by this offer.
        understood = {key: value for key, value in understood.items() if key != converse.CORRECTED}
    if understood != ctx.thread.understanding:
        updates.understanding = understood
    # Counted, never fixed: a question asked again, or a reply that asks nothing before the offer.
    checks = reply_checks.misses(
        Reply(text=reply.text),
        offered=offering,
        offer_dropped=dropped,
        # A chat reply may support without asking (the client meeting, 2026-11-05: "mainly driven by questions").
        needs_question=False,
        last_mani_text=next((m.content for m in reversed(history) if m.role is MessageRole.MANI), None),
    )
    if not guarded and offering is None:
        # The three shapes and no fixes before the framework (the client's test, 2026-10-29). Counted, never fixed.
        checks += reply_checks.chat_misses(
            reply.text, shape=reply.shape, window=reply.window, insight=reply.insight, move=reply.move,
            asked_for_help=bool(reply.asked_for_help),
            earlier_insights=ctx.thread.understanding.get(converse.INSIGHTS),
            last_shape=(ctx.thread.understanding.get(converse.THINKING) or {}).get("shape"),
            latest=content,
        )
    if checks:
        logger.info("thread %s reply checks: %s", ctx.thread.id, "; ".join(checks))
    # No dashes in what Mani says (the client, 2026-11-03); the draft's are still counted above as "em dash".
    fixed = dataclasses.replace(fixed, text=repairs.without_dashes(fixed.text))
    if not fixed.text.strip():
        raise ServiceError(
            f"reply on thread {ctx.thread.id} was empty after repair",
            ErrorCategory.LLM_UNAVAILABLE,
            retryable=True,
            user_message="Mani had trouble responding. Please try again.",
        )

    if offering is not None:
        updates.retire_technique = False
        updates.technique = TechniqueState(
            thread_id=ctx.thread.id, framework_id=offering, outcome=TechniqueOutcome.OFFERED,
            phase=OFFERING, at_message_count=ctx.thread.message_count + 2,
        )
        updates.offer_frameworks.append(offering)
        updates.reset_outcomes = True
    elif declined is not None and reply.back_to_framework and not guarded and not moving:
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
    seen = understood.get(picture.KEY) or {}
    following = picture.funnel(seen)[0]
    trace = _trace(
        moment=Moment.CHATTING.value, style=conversation_style, message_count=ctx.thread.message_count,
        their_message=context.their_messages(ctx), latency_ms=call.latency_ms, guarded=guarded or None,
        model=_trace(
            shape=reply.shape, move=reply.move, heart=reply.heart, needs_info=reply.needs_info,
            insight=bool(reply.insight) or None, link=bool(reply.link) or None, checking=reply.checking,
            heading_toward=getattr(reply, "heading_toward", None), asked_for_help=reply.asked_for_help,
            frustrated=reply.frustrated, back_to_framework=reply.back_to_framework,
        ),
        may_move=allowed, moved=moving or None, offered=offering, offer_dropped=dropped,
        toward_framework=bool(understood.get(converse.TOWARD)) or None,
        corrected_offer=bool(understood.get(converse.CORRECTED)) or None,
        funnel=_trace(
            ranked=len(seen.get(picture.TIED_TO) or []), explored=len(seen.get(picture.EXPLORED) or []),
            ruled_out=len(seen.get(picture.RULED_OUT) or []), next_side=following["side"] if following else None,
        ),
        stepped_out_of=declined.id if declined else None, buttons=[p.label for p in prompts],
        notes=fixed.notes, checks=checks,
    )
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
        trace=trace,
        raw_reply=_raw(reply, settings),
        # The same prompt and conversation as the reply, so its prefix is cached, then the reply as it went out. As on
        # every other turn, the model's own crisis judgment keeps what is understood as it was.
        read_after=None if guarded else ReadAfter(
            thread_id=ctx.thread.id, user_id=ctx.thread.user_id,
            messages=[{"role": "system", "content": system.text}] + _conversation(history) + [
                {"role": "user", "content": for_model}, {"role": "assistant", "content": fixed.text},
                {"role": "system", "content": converse.read_note(conversation_style, understood)},
            ],
            model=model, parameters=parameters, routing=routing, their_messages=their_messages,
        ),
    )


async def read_understanding(claims: Claims, job: ReadAfter) -> dict | None:
    """Read what their message adds to the picture and Mani's whole reading of them, after the reply is sent, and
    store it; returns the record stored, or None. Off the person's wait: written before the reply's text, this reading
    grew with the conversation until turns passed the chat deadline (Lolly's chats, 2026-11-03). It merges onto the
    record as it is when it lands, under the thread's turn lock, so a turn that started meanwhile is never overwritten.
    A reading that fails costs this turn's picture, never a reply: logged and swallowed."""
    from mani.db import pool

    try:
        call = await client.complete(
            job.messages,
            schema.ConversationUnderstanding,
            model=job.model,
            purpose=llm_calls.Purpose.UNDERSTANDING,
            temperature=job.parameters.get("temperature", client.DEFAULT_TEMPERATURE),
            max_tokens=job.parameters.get("maxTokens", client.DEFAULT_MAX_TOKENS),
            reasoning_effort=job.parameters.get("reasoning_effort"),
            routing=job.routing,
            user_id=job.user_id,
            thread_id=job.thread_id,
            prompt_version_id=None,
        )
        async with pool.as_user(claims) as conn:
            await _lock_thread(conn, job.thread_id)
            now = await threads.understanding_of(conn, job.thread_id, job.user_id)
            if now is None:
                return None
            after = converse.read(now, call.value, their_messages=job.their_messages)
            if after != now:
                await threads.apply(conn, job.thread_id, job.user_id, threads.ThreadUpdates(understanding=after))
            return after
    except Exception:
        logger.exception("reading after the reply failed for thread %s", job.thread_id)
        return None


async def _lock_thread(conn: asyncpg.Connection, thread_id: uuid.UUID | str) -> None:
    """One writer at a time per conversation, held until the transaction ends: a turn, or the reading after one."""
    await conn.execute("select pg_advisory_xact_lock(hashtextextended($1, 1))", f"thread:{thread_id}")


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
    await _lock_thread(conn, thread_id)

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

    await rewind.save(conn, ctx, user_id)

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

    if tapped is None and context.copies_last_reply(content, history):
        return await _copied_back(conn, ctx, content, client_message_id)

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
    # The answer to a check or an offer, a concern, and the body check-in: the same voice as the chat. The summary
    # only once messages have left the window, so it never repeats what the model reads raw.
    system = composer.compose_moment(
        config, ctx.profile, should_generate_title=wants_title, offered=offered_now,
        summary=ctx.summary if window.dropped else None, memory=ctx.memory,
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
    # Where the new view forms, and in the body check-in, the core stays the belief the questions looked at: the
    # balanced belief reported as the core replaced it, and rewrote B (the career chat, 2026-11-03).
    core_fixed = moment is Moment.BODY or (
        moment is Moment.IN_STAGES and technique is not None and walk.new_view(running_framework, technique.phase)
    )
    seen_now = reply.picture
    # What they decide to do there is their step, never what they want or long for (the friend chat, 2026-11-04).
    fixed_there = ("core", "wants", "desire")
    if core_fixed and seen_now is not None and (held := [k for k in fixed_there if getattr(seen_now, k)]):
        logger.info("thread %s %s reported where fixed, ignored", ctx.thread.id, ", ".join(held))
        seen_now = seen_now.model_copy(update={key: None for key in fixed_there})
    if not guarded:
        understood = understanding.merge(ctx.thread.understanding, seen_now, reply.heart)
        deeper = (
            picture.new_core(ctx.thread.understanding.get(picture.KEY), understood.get(picture.KEY))
            if moment is Moment.IN_STAGES and not core_fixed else None
        )
        if deeper and (said := understanding.case_from_core(picture.core(understood.get(picture.KEY)))):
            # The core deepened before the new view forms: the case the later stages work on follows it.
            logger.info("thread %s core deepened inside the questions: the case follows it", ctx.thread.id)
            understood = understanding.merge_check(understood, said)
    if moment is Moment.OFFER_OPEN and not guarded and answer in ("corrected", "wants_other"):
        # They corrected what the offer said back (the client meeting, 2026-11-03): the reply says the corrected
        # reading back, the case they had not confirmed is dropped, and the next offer may come once they confirm it.
        understood = understanding.corrected(understood)
    if retiring_framework_id is not None:
        # The framework that just finished worked through this reading. The next check waits for a fresh one, so
        # Mani never checks again straight away on the case it has just finished.
        understood = {key: value for key, value in understood.items() if key not in ("heart", converse.TOWARD)}
    if understood != ctx.thread.understanding:
        updates.understanding = understood
    # A clear yes to the check is the only way to an offer (spec 0006, AC-1, AC-4). The framework is the solution
    # (the client's test, 2026-10-29): the chat finds what they tell themselves even about something really
    # happening, so a yes always brings the offer; it no longer turns the chat to helping.
    confirmed = (
        moment is Moment.CHECK_OPEN and not guarded and starting is None and reply.check_answer == "yes"
    )

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
        # An empty offer slot is filled with the core belief they confirmed: the offer names the belief (the client's
        # review, 2026-10-29), and the feeling only when no core is held.
        feeling=picture.core(understood.get(picture.KEY)).get("belief") or understood.get("feeling"),
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
            their_message=content,
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
        if walked.phase not in body_route.STAGES:
            # The check-in is code's, sent when the questions end; a reply offering one before then is dropped (the
            # career chat, 2026-11-03). The last stage, while it waits, always asks: a close written there would end
            # the conversation with nothing to answer (the friend chat, 2026-11-04). Earlier stages may stay with
            # them without a question (the client meeting, 2026-11-05: no questionnaire).
            kept = repairs.without_body_offer(fixed.text)
            notes = fixed.notes + (["body offer dropped"] if kept != fixed.text else [])
            if walked.reached is None and walked.phase == walk.content_stages(walking)[-1] and "?" not in kept:
                if question := walk.stay_question(walking, walked.entries, walked.phase, conversation_style):
                    kept = f"{kept}\n\n{question}".strip()
                    notes.append("stage question added to a reply that asked nothing")
            fixed = dataclasses.replace(fixed, text=kept, notes=notes)
        if walked.entries != (stored_all.get(walking.id) or {}):
            updates.stages_known = {**stored_all, walking.id: walked.entries}
        if walked.phase == body_route.ASK:
            # The last stage was answered: before any body check-in, they are asked whether they would like one
            # (muhammad, 2026-10-27).
            text, buttons = body_route.ask(fixed.text, walking.stages)
            fixed = dataclasses.replace(fixed, text=text, prompts=_prompts(buttons), phase=body_route.ASK)
    if moment is Moment.BODY and not guarded:
        route = config.registry.get(technique.framework_id if technique else retiring_framework_id)
        fixed, step = _body_route(fixed, reply.body, reply.options, tapped, technique, route)
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
    # No dashes in what Mani says (the client, 2026-11-03), after every template and stage line is in place; the
    # draft's are still counted above as "em dash".
    fixed = dataclasses.replace(fixed, text=repairs.without_dashes(fixed.text))
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

    if fixed.title:
        updates.title = fixed.title

    await threads.apply(conn, ctx.thread.id, user_id, updates)

    summarized = ctx.summary.summarized_message_count if ctx.summary else 0
    ledger = walk.ledger_view(walking, walked.entries, walked.phase) if walked else None
    stage_rows = (
        [{"stage": r["stage"], "status": r["status"], "asking": r["asking"]} for r in ledger]
        if ledger is not None else None
    )
    trace = _trace(
        moment=moment.value, style=conversation_style, message_count=ctx.thread.message_count,
        their_message=context.their_messages(ctx), latency_ms=call.latency_ms,
        framework=(starting or (technique.framework_id if technique else None)
                   or (ctx.technique.framework_id if ctx.technique else None)),
        phase_before=ctx.technique.phase if ctx.technique else None,
        phase_after=updates.technique.phase if updates.technique else None,
        tapped=tapped.label if tapped else None,
        safety=assessment.level.value if assessment.blocks_framework else None,
        model_concern=model_concern or None, guarded=guarded or None,
        model=_trace(
            **_stage_reports(reply), offer_answer=reply.offer_answer, check_answer=reply.check_answer,
            heart=reply.heart, body=reply.body, heading_toward=reply.heading_toward,
        ),
        applied=_trace(
            offer_answer=answer, outcome=outcome.value if outcome else None, starting=starting,
            accepted=accepted_this_turn or None, confirmed=confirmed or None,
        ),
        core_fixed=core_fixed or None,
        walk=_trace(reached=walked.reached, phase=walked.phase, unjudged=walked.unjudged or None) if walked else None,
        stages=stage_rows, offered=offered, offer_dropped=fixed.offer_dropped,
        buttons=[p.label for p in fixed.prompts], notes=fixed.notes, checks=checks,
    )
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
        stage_trace=stage_rows,
        trace=trace,
        raw_reply=_raw(reply, settings),
    )


# FastAPI's own documented order is response sent -> background tasks run -> yield
# dependencies' exit code, which is where UserConn's transaction actually commits. So this
# background task starts running *before* the message it wants to reference is guaranteed
# visible to another connection - confirmed live: attach_message raised a foreign key
# violation on every turn. A short, bounded retry is the fix, not a bigger one: the commit
# in question happens within milliseconds of the background task starting, once at all.
LINK_RETRY_ATTEMPTS = 5
LINK_RETRY_DELAY_SECONDS = 0.05


async def record_trace(turn: "Turn", thread_id: uuid.UUID | str) -> None:
    """Store the turn's trace once its message is committed, with the same bounded retry as link_call, for the same
    reason. A trace that cannot be stored costs a review, never a reply: logged and swallowed."""
    import asyncio

    from mani.db import pool, turn_traces

    for attempt in range(1, LINK_RETRY_ATTEMPTS + 1):
        try:
            async with pool.as_admin() as conn:
                await turn_traces.record(
                    conn, thread_id=thread_id, message_id=turn.message_id, llm_call_id=turn.llm_call_id,
                    trace=turn.trace, raw_reply=turn.raw_reply,
                )
            return
        except asyncpg.PostgresError:
            if attempt == LINK_RETRY_ATTEMPTS:
                logger.warning("could not store the trace for message %s", turn.message_id, exc_info=True)
                return
            await asyncio.sleep(LINK_RETRY_DELAY_SECONDS * attempt)


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


async def _copied_back(
    conn: asyncpg.Connection,
    ctx: threads.TurnContext,
    content: str,
    client_message_id: uuid.UUID | str | None,
) -> Turn:
    """Answer Mani's own last reply sent back with the fixed line, and change nothing else: no offer, no stage, and
    the picture as it was. The pair is kept, so the conversation shows what happened."""
    logger.info("thread %s: their message was Mani's last reply sent back", ctx.thread.id)
    pair = await messages_db.create_pair(
        conn, ctx.thread.id, content, COPIED_BACK, client_message_id=client_message_id,
    )
    return Turn(
        message_id=pair.mani_message_id,
        content=COPIED_BACK,
        created_at=pair.created_at,
        title=ctx.thread.title,
        was_duplicate=pair.was_duplicate,
        trace=_trace(moment="copied_back", message_count=ctx.thread.message_count),
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
        # The screen's category only, never the words that tripped it.
        trace=_trace(moment="crisis", reason=reason.split(":")[0], message_count=ctx.thread.message_count),
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
