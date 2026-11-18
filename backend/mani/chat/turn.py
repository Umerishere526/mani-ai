# ABOUTME: One user message from arrival to stored reply, with one model call that writes every word Mani says.
# ABOUTME: Code adds only the client's fixed pieces, the buttons, the framework's order and the safety pause.

from __future__ import annotations

import asyncio
import datetime as dt
import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

import asyncpg

from mani.auth.jwt import Claims
from mani.chat import context, crisis, decide as decide_mod, facts, judged as judged_mod, pause, record as rec, rewind, safety, taps
from mani.chat.greeting import COPIED_BACK, OPENERS, RETURN_OPENER, STYLE_OPTIONS, greeting
from mani.chat.repairs import offer_buttons, without_dashes
from mani.chat.reply import TurnReply
from mani.chat.techniques import OFFERING
from mani.config import get_settings
from mani.db import llm_calls, messages as messages_db, pauses, profiles, threads
from mani.errors import ErrorCategory, ServiceError
from mani.llm import client
from mani.llm.schema import SmartPrompt
from mani.models.rows import Message, MessageRole, SupportStyle, TechniqueOutcome, Thread
from mani.prompts import cache, composer

logger = logging.getLogger(__name__)

# The turn's one model call, with client.complete's signature. chat/runner.py supplies it, so no connection is held
# while the model thinks.
Ask = Callable[..., Awaitable[client.Call]]
# A title is asked for once the thread has a real exchange behind it.
TITLE_AFTER_MESSAGES = 3
# The trace and the call link are written once the turn's message is committed, which happens after the response.
LINK_RETRY_ATTEMPTS = 5
# Said with every refusal for a limit, since a message refused there is never read for safety.
IN_DANGER = "If you're in danger or thinking about hurting yourself, call 911 now, or call or text 988."
LINK_RETRY_DELAY_SECONDS = 0.05


@dataclass(frozen=True)
class Turn:
    """What the endpoint sends back. The debug-only fields are None unless AI_DEBUG_MODE is on."""

    message_id: uuid.UUID | None
    content: str
    created_at: object
    prompts: list[SmartPrompt] = field(default_factory=list)
    title: str | None = None
    crisis_detected: bool = False
    paused_from: dt.datetime | None = None
    paused_until: dt.datetime | None = None
    was_duplicate: bool = False
    needs_summary: bool = False
    llm_call_id: uuid.UUID | None = None
    reasoning: str | None = None
    ledger: list[dict] | None = None
    understanding: dict | None = None
    check_at_message_count: int | None = None
    trace: dict | None = None
    raw_reply: dict | None = None


async def send(
    conn: asyncpg.Connection, claims: Claims, thread_id: uuid.UUID | str, content: str,
    client_message_id: uuid.UUID | str | None = None, *, ask: Ask, config: cache.Config,
) -> Turn:
    """Run one turn in the caller's transaction, and leave the summary for after the reply when it is due."""
    turn = await _turn(conn, claims, thread_id, content, client_message_id, ask=ask, config=config)
    if not turn.was_duplicate:
        await threads.set_pending_follow_up(conn, thread_id, claims.user_id, follow_up_due(turn))
    return turn


def follow_up_due(turn: Turn) -> dict | None:
    """What the turn leaves for after its reply, as threads.pending_follow_up holds it: the summary, or nothing."""
    if turn.message_id is None or not turn.needs_summary:
        return None
    return {"message_id": str(turn.message_id), "summary": True}


@dataclass(frozen=True)
class FollowedUp:
    """What the work after a reply did: whether the summary was brought up to date, and whether it failed and still
    waits for the next request. `understanding` stays None: nothing reads the conversation after a reply."""

    understanding: dict | None = None
    summarized: bool = False
    pending: bool = False


# The summary stops here, well inside its claim (threads.FOLLOW_UP_CLAIM_SECONDS), so no second request takes the work
# while it still runs.
FOLLOW_UP_DEADLINE_SECONDS = 90


async def follow_up(claims: Claims, thread_id: uuid.UUID | str, message_id: uuid.UUID | str) -> FollowedUp | None:
    """Bring the summary up to date for Mani's reply `message_id`, when the app or the schedule asks once the reply is
    shown. None when nothing waits for that reply, or another request is running it. A request of its own, since on
    Vercel nothing runs after a response; claimed and settled in short transactions, and a failure stays waiting."""
    from mani import summarize
    from mani.db import pool

    async with pool.as_user(claims) as conn:
        waiting = await threads.claim_pending_follow_up(conn, thread_id, claims.user_id, message_id)
    if waiting is None:
        return None
    summarized = failed = False
    if waiting.get("summary"):
        try:
            async with asyncio.timeout(FOLLOW_UP_DEADLINE_SECONDS):
                summarized = await summarize.update(claims, thread_id) is not None
        except Exception:
            logger.exception("summarization failed for thread %s", thread_id)
            failed = True
    left = {"message_id": str(message_id), "summary": True} if failed else None
    async with pool.as_user(claims) as conn:
        await threads.settle_pending_follow_up(conn, thread_id, claims.user_id, message_id, left)
    return FollowedUp(summarized=summarized, pending=failed)


async def _turn(
    conn: asyncpg.Connection, claims: Claims, thread_id, content: str, client_message_id, *, ask: Ask,
    config: cache.Config,
) -> Turn:
    settings = get_settings()
    if (duplicate := await _arrival(conn, claims, thread_id, client_message_id)) is not None:
        return duplicate
    await lock_thread(conn, thread_id)
    ctx = await threads.load_turn_context(conn, thread_id, claims.user_id)
    if ctx is None:
        raise ServiceError(f"thread {thread_id} not found for user {claims.user_id}", ErrorCategory.NOT_FOUND,
                           user_message="That conversation is not available.")
    await rewind.save(conn, ctx, claims.user_id)
    window = await messages_db.for_context(conn, thread_id, claims.user_id,
                                           budget_chars=settings.context_budget_chars)
    history = window.messages
    if (style := taps.chosen_style(history, content)) is not None:
        return await _open_in_style(conn, ctx, content, style, client_message_id)

    record = dict(ctx.thread.understanding or {})
    technique = ctx.technique
    running = technique if (technique is not None and technique.outcome is TechniqueOutcome.ACCEPTED
                            and technique.phase not in (None, OFFERING)) else None
    open_offer = technique if technique is not None and technique.outcome is TechniqueOutcome.OFFERED else None
    tapped = taps.find_tapped_prompt(history, content)
    tap = taps.tap_event(tapped, config.registry, open_offer)
    style_name = context.resolve_style(ctx)
    if tap.explain is not None:
        return await _explained(conn, ctx, content, tap.explain.id, style_name, tapped, client_message_id, config)

    check = pause.return_check(ctx)
    answering = None if check is not None else pause.answering(ctx)
    before = safety.State(ctx.thread.safety)
    holding = before is not safety.State.CLEAR or check is not None
    if tapped is None and not holding and context.copies_last_reply(content, history):
        return await _copied_back(conn, ctx, content, client_message_id)
    if not holding:
        await within_limits(conn, claims.user_id, settings)

    wants_title = ctx.thread.message_count >= TITLE_AFTER_MESSAGES and not ctx.thread.title
    end_check_asked = record.get(rec.SAFETY_END_CHECK) == "asked"
    told = facts.facts(
        ctx, config, record=record, style=style_name, running=None if tap.starting else running, open_offer=open_offer,
        event=tap.fact, wants_title=wants_title, return_check=check, answering_return=answering,
        end_check_asked=end_check_asked,
    )
    model, parameters, routing = composer.model_settings(config, "mani")
    call = await ask(
        [{"role": "system", "content": facts.system_prompt(config, ctx, summary_due=bool(window.dropped))}]
        + conversation(history)
        + [{"role": "user", "content": context.disarm(content)}, {"role": "system", "content": told}],
        TurnReply, model=model, purpose=llm_calls.Purpose.CHAT,
        temperature=parameters.get("temperature", client.DEFAULT_TEMPERATURE),
        max_tokens=parameters.get("maxTokens", client.DEFAULT_MAX_TOKENS),
        reasoning_effort=parameters.get("reasoning_effort"), routing=routing, user_id=claims.user_id,
        thread_id=ctx.thread.id, prompt_version_id=None,
        fallback=crisis.CRISIS_REPLY if holding else crisis.TROUBLE_REPLY,
    )
    return await _apply(conn, ctx, call, content=content, tapped=tapped, tap=tap, record=record, running=running,
                        open_offer=open_offer, check=check, answering=answering, before=before, holding=holding,
                        wants_title=wants_title, end_check_asked=end_check_asked, window=window, config=config,
                        client_message_id=client_message_id, settings=settings)


async def _apply(
    conn, ctx: threads.TurnContext, call: client.Call, *, content, tapped, tap, record, running, open_offer, check,
    answering, before, holding, wants_title, end_check_asked, window, config, client_message_id, settings,
) -> Turn:
    """What the reply decides, written in this transaction. A fallback reply (no host answered) moves nothing."""
    reply: TurnReply = call.value
    fallback = call.model == "fallback"
    if fallback:
        judgment = judged_mod.Judged(state_after=before, pausing=False, about=record.get(rec.DANGER_ABOUT),
                                     asked=False, settled_now=False)
        decision = decide_mod.Decision(declined=rec.declined(record), finished=rec.finished(record))
    else:
        judgment = judged_mod.judge(before, reply.safety, record, return_check=check, answering_return=answering)
        # A worry open on the thread or found in this message comes before anything the reply asks for, except the
        # answer that settles the safety question after a framework's last stage: that one carries the close.
        settles_end_check = end_check_asked and judgment.state_after is safety.State.CLEAR
        guarded = (holding or judgment.state_after is not safety.State.CLEAR) and not settles_end_check
        decision = decide_mod.decide(
            reply, config.registry, thread_id=ctx.thread.id, running=running, open_offer=open_offer, tap=tap,
            record=record, guarded=guarded,
            count_after=ctx.thread.message_count + 2,
            end_check_due=bool(record.get(rec.DANGER_REACHED)) and record.get(rec.SAFETY_END_CHECK) != "done",
            end_check_asked=end_check_asked,
        )
    text = (crisis.pause_reply(judgment.about, settings.crisis_pause_minutes) if judgment.pausing
            else crisis.END_CHECK if decision.end_check else reply.text)
    text = without_dashes(text).strip()
    if not text:
        raise ServiceError(f"reply on thread {ctx.thread.id} was empty", ErrorCategory.LLM_UNAVAILABLE, retryable=True,
                           user_message="Mani had trouble responding. Please try again.")
    updates, after = _updates(ctx, reply, decision, judgment, record=record, check=check, answering=answering,
                              fallback=fallback, end_check_asked=end_check_asked, wants_title=wants_title)
    pair = await messages_db.create_pair(
        conn, ctx.thread.id, content, text, selected_prompt=tapped.label if tapped else None,
        prompt_options=[p.model_dump(mode="json", exclude_none=True) for p in decision.prompts] or None,
        client_message_id=client_message_id,
    )
    await threads.apply(conn, ctx.thread.id, ctx.thread.user_id, updates)
    flagged = await _record_danger(conn, ctx, before, judgment, pair)
    paused = await _pause_writes(conn, ctx, judgment, reply, answering=answering, fallback=fallback, pair=pair,
                                 minutes=settings.crisis_pause_minutes)
    summarized = ctx.summary.summarized_message_count if ctx.summary else 0
    trace = {key: value for key, value in {
        "action": reply.action, "framework": reply.framework, "stage": reply.stage,
        "safety": judged_mod.traced(reply.safety), "paused": judgment.pausing or None,
        "buttons": [p.label for p in decision.prompts], "latency_ms": call.latency_ms, "refused": decision.refused,
        "fallback": fallback or None, "notes": reply.notes if settings.ai_debug_mode else None,
    }.items() if value not in (None, "", [], {})}
    return Turn(
        message_id=pair.mani_message_id, content=text, created_at=pair.created_at, prompts=decision.prompts,
        title=updates.title or ctx.thread.title, crisis_detected=flagged or judgment.state_after is safety.State.DANGER,
        paused_from=paused.started_at if paused else None, paused_until=paused.ends_at if paused else None,
        was_duplicate=pair.was_duplicate, needs_summary=window.dropped > summarized and not judgment.pausing,
        llm_call_id=call.call_id, understanding=after if settings.ai_debug_mode else None, trace=trace,
        raw_reply=reply.model_dump(mode="json") if settings.ai_debug_mode else None,
    )


def _updates(ctx, reply: TurnReply, decision, judgment, *, record, check, answering, fallback, end_check_asked,
             wants_title) -> tuple[threads.ThreadUpdates, dict]:
    """The thread's changes and its record after this turn."""
    after = rec.with_outcomes(record, notes=None if fallback else reply.notes, declined=decision.declined,
                              finished=decision.finished)
    updates = threads.ThreadUpdates()
    if not fallback:
        after = judged_mod.safety_record(after, return_check=check, answering_return=answering, judged=judgment,
                                         read_about=reply.safety.about)
        if judgment.state_after.value != ctx.thread.safety:
            updates.safety = judgment.state_after.value
    if decision.end_check:
        after[rec.SAFETY_END_CHECK] = "asked"
        updates.safety = safety.State.UNSURE.value
    elif end_check_asked and decision.finished != rec.finished(record):
        after[rec.SAFETY_END_CHECK] = "done"
    elif judgment.settled_now and after.get(rec.SAFETY_END_CHECK) == "done":
        after.pop(rec.SAFETY_END_CHECK)
    if after != record:
        updates.understanding = after
    if decision.technique is not None:
        updates.technique = decision.technique
    updates.retire_technique = decision.retire_technique
    updates.reset_outcomes = decision.reset_outcomes
    if decision.offered:
        updates.offer_frameworks.append(decision.offered)
    if reply.title and wants_title and not fallback:
        updates.title = reply.title
    return updates, after


async def _record_danger(conn, ctx, before: safety.State, judgment, pair) -> bool:
    """The turn that first finds danger is recorded once for review (admin.crisis_events), never with their words."""
    if pair.was_duplicate or judgment.state_after is not safety.State.DANGER or before is safety.State.DANGER:
        return False
    logger.warning("thread %s may be in danger (%s)", ctx.thread.id, judgment.about)
    await threads.mark_crisis(conn, ctx.thread.id, f"safety: {judgment.about or 'danger'}", pair.user_message_id)
    return True


async def _pause_writes(conn, ctx, judgment, reply: TurnReply, *, answering, fallback, pair, minutes):
    """An answer to the return check that settles it marks that pause checked; a pausing turn starts a pause."""
    if pair.was_duplicate or fallback:
        return None
    if answering is not None and judgment.state_after is safety.State.CLEAR:
        await pauses.mark_checked(conn, answering)
    if judgment.pausing:
        return await pauses.start(conn, ctx.thread.user_id, ctx.thread.id, minutes, reply.safety.why)
    return None


async def _arrival(conn, claims: Claims, thread_id, client_message_id) -> Turn | None:
    """The locks and gates before anything is read: a retry waits for the first request and gets its stored reply,
    and a paused person is refused."""
    if client_message_id is not None:
        await conn.execute("select pg_advisory_xact_lock(hashtextextended($1, 0))",
                           f"{claims.user_id}:{client_message_id}")
    if (active := await pauses.active(conn, claims.user_id)) is not None:
        raise pause.paused_error(active)
    if client_message_id is None:
        return None
    existing = await messages_db.find_pair_by_client_id(conn, claims.user_id, client_message_id)
    if existing is None:
        return None
    user_message, reply_message = existing
    if str(user_message.thread_id) != str(thread_id):
        raise ServiceError(f"client_message_id {client_message_id} already used in thread {user_message.thread_id}",
                           ErrorCategory.CONFLICT, user_message="That message was already sent in another conversation.")
    thread = await threads.get(conn, thread_id, claims.user_id)
    return Turn(
        message_id=reply_message.id if reply_message else None,
        content=reply_message.content if reply_message else "",
        created_at=reply_message.created_at if reply_message else None,
        prompts=[SmartPrompt.model_validate(p) for p in (reply_message.prompt_options or [])] if reply_message else [],
        title=thread.title if thread else None, crisis_detected=bool(thread and thread.crisis_detected),
        was_duplicate=True,
    )


async def _explained(conn, ctx, content, framework_id: str, style: str, tapped, client_message_id, config) -> Turn:
    """Tell me more: the client's explanation for their style, word for word, with no model call."""
    framework = config.registry.get(framework_id)
    text = ((framework.stages.get(OFFERING) or {}).get("explain") or {}).get(style) or framework.summary
    prompts = offer_buttons(framework.id, explained=True)
    pair = await messages_db.create_pair(
        conn, ctx.thread.id, content, text, selected_prompt=tapped.label,
        prompt_options=[p.model_dump(mode="json", exclude_none=True) for p in prompts],
        client_message_id=client_message_id,
    )
    return Turn(message_id=pair.mani_message_id, content=text, created_at=pair.created_at, prompts=prompts,
                title=ctx.thread.title, was_duplicate=pair.was_duplicate)


async def _open_in_style(conn, ctx, content: str, style: SupportStyle, client_message_id) -> Turn:
    """The chosen style, with that style's fixed opener and no model call. While a pause that has run out still owes
    the question how things are, that question is the opener, and it is recorded as asked."""
    check = pause.return_check(ctx)
    reply = RETURN_OPENER if check is not None else OPENERS[style.value]
    pair = await messages_db.create_pair(conn, ctx.thread.id, content, reply, selected_prompt=content.strip(),
                                         client_message_id=client_message_id)
    updates = threads.ThreadUpdates(conversation_style=style)
    if check is not None and not pair.was_duplicate:
        updates.understanding = {**(ctx.thread.understanding or {}),
                                 rec.RETURN_CHECK: {"pause": str(check.pause_id), "state": "asked"}}
    await threads.apply(conn, ctx.thread.id, ctx.thread.user_id, updates)
    return Turn(message_id=pair.mani_message_id, content=reply, created_at=pair.created_at, title=ctx.thread.title)


async def _copied_back(conn, ctx, content: str, client_message_id) -> Turn:
    """Mani's own last reply sent back gets the fixed line, and nothing else changes."""
    logger.info("thread %s: their message was Mani's last reply sent back", ctx.thread.id)
    pair = await messages_db.create_pair(conn, ctx.thread.id, content, COPIED_BACK, client_message_id=client_message_id)
    return Turn(message_id=pair.mani_message_id, content=COPIED_BACK, created_at=pair.created_at,
                title=ctx.thread.title, was_duplicate=pair.was_duplicate, trace={"copied_back": True})


async def within_limits(conn: asyncpg.Connection, user_id: str, settings) -> None:
    """Refuse a paid reply past the day's or the minute's limit, counted from the messages they sent. Nothing judges
    the message before the refusal, so the refusal itself says where to get help."""
    for limit, window, user_message in (
        (settings.daily_message_limit, dt.timedelta(hours=24),
         "You've reached today's message limit. Please come back tomorrow. " + IN_DANGER),
        (settings.minute_message_limit, dt.timedelta(minutes=1),
         "You're sending messages faster than Mani can answer. Please wait a minute and try again. " + IN_DANGER),
    ):
        if limit and await messages_db.count_from_user_since(conn, user_id, window) >= limit:
            raise ServiceError(f"user {user_id} reached the limit of {limit} per {window}", ErrorCategory.RATE_LIMITED,
                               retryable=True, user_message=user_message)


async def lock_thread(conn: asyncpg.Connection, thread_id: uuid.UUID | str) -> None:
    """One writer at a time per conversation, held until the transaction ends."""
    await conn.execute("select pg_advisory_xact_lock(hashtextextended($1, 1))", f"thread:{thread_id}")


def conversation(history: list[Message]) -> list[dict[str, str]]:
    return [{"role": "user" if m.role is MessageRole.USER else "assistant",
             "content": context.disarm(m.content) if m.role is MessageRole.USER else m.content} for m in history]


async def start_thread(conn: asyncpg.Connection, claims: Claims) -> Thread:
    """Open a conversation and write Mani's opening line, with the style buttons."""
    thread = await threads.create(conn, claims.user_id)
    await messages_db.create_greeting(conn, thread.id, await opening_greeting(conn, claims.user_id, thread.id),
                                      prompt_options=STYLE_OPTIONS)
    return thread


async def opening_greeting(conn: asyncpg.Connection, user_id: str, exclude: uuid.UUID | None = None) -> str:
    """The line a conversation opens with, made in one place so a client's preview matches what is stored."""
    profile = await profiles.get(conn, user_id)
    return greeting(profile.nickname if profile else None, await has_written_in_earlier_thread(conn, user_id, exclude))


async def has_written_in_earlier_thread(conn: asyncpg.Connection, user_id: str, exclude: uuid.UUID | None = None) -> bool:
    return bool(await conn.fetchval(
        f"select exists (select 1 from public.threads t where user_id = $1 and id is distinct from $2 and "
        f"{threads.WRITTEN_IN})", user_id, exclude,
    ))


async def record_trace(turn: Turn, thread_id: uuid.UUID | str) -> None:
    """Store the turn's trace once its message is committed. A trace that cannot be stored costs a review, never a
    reply: logged and swallowed."""
    from mani.db import pool, turn_traces

    for attempt in range(1, LINK_RETRY_ATTEMPTS + 1):
        try:
            async with pool.as_admin() as conn:
                await turn_traces.record(conn, thread_id=thread_id, message_id=turn.message_id,
                                         llm_call_id=turn.llm_call_id, trace=turn.trace, raw_reply=turn.raw_reply)
            return
        except asyncpg.PostgresError:
            if attempt == LINK_RETRY_ATTEMPTS:
                logger.warning("could not store the trace for message %s", turn.message_id, exc_info=True)
                return
            await asyncio.sleep(LINK_RETRY_DELAY_SECONDS * attempt)


async def link_call(call_id: uuid.UUID, message_id: uuid.UUID) -> None:
    """Point a recorded model call at the message it produced, once that message is committed."""
    from mani.db import pool

    for attempt in range(1, LINK_RETRY_ATTEMPTS + 1):
        try:
            async with pool.as_admin() as conn:
                await llm_calls.attach_message(conn, call_id, message_id)
            return
        except asyncpg.PostgresError:
            if attempt == LINK_RETRY_ATTEMPTS:
                logger.exception("failed to link llm call %s to message %s after %d attempts", call_id, message_id,
                                 LINK_RETRY_ATTEMPTS)
                return
            await asyncio.sleep(LINK_RETRY_DELAY_SECONDS)
