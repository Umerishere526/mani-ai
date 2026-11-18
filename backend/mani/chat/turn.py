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
from mani.chat import crisis, decide as decide_mod, facts, judged as judged_mod, pause, record as rec, rewind, safety, taps
from mani.chat.greeting import (
    COPIED_BACK, STYLE_OPTIONS, greeting, openers, resolve_style,
)
from mani.chat.repairs import clean_title, start_buttons, suggestion_buttons, without_dashes
from mani.chat.reply import TurnReply
from mani.chat.techniques import FEELINGS, OFFERING, STEPS, example_text, steps_text
from mani.config import get_settings
from mani.text import copies_last_reply
from mani.db import llm_calls, messages as messages_db, pauses, profiles, threads
from mani.errors import ErrorCategory, ServiceError
from mani.llm import client
from mani.llm.schema import SmartPrompt
from mani.models.rows import Framework, Message, MessageRole, SupportStyle, TechniqueOutcome, Thread
from mani.prompts import cache, composer

logger = logging.getLogger(__name__)

# The turn's one model call, with client.complete's signature. chat/runner.py supplies it, so no connection is held
# while the model thinks; it gives back None when no host answered.
Ask = Callable[..., Awaitable[client.Call | None]]
# A title is asked for once the thread has a real exchange behind it.
TITLE_AFTER_MESSAGES = 3
# The trace and the call link are written once the turn's message is committed, which happens after the response.
LINK_RETRY_ATTEMPTS = 5
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
    understanding: dict | None = None
    trace: dict | None = None
    raw_reply: dict | None = None


async def send(
    conn: asyncpg.Connection, claims: Claims, thread_id: uuid.UUID | str, content: str,
    client_message_id: uuid.UUID | str | None = None, *, ask: Ask, config: cache.Config, answer_failure: bool,
) -> Turn:
    """Run one turn in the caller's transaction, and leave the summary for after the reply when it is due.
    `answer_failure`: a reply the model left empty gets the fixed words; otherwise it fails the turn and nothing is
    written (an edit), as runner.run does for a model that never answered."""
    turn = await _turn(conn, claims, thread_id, content, client_message_id, ask=ask, config=config,
                       answer_failure=answer_failure)
    if not turn.was_duplicate:
        await threads.set_pending_follow_up(conn, thread_id, claims.user_id, follow_up_due(turn))
    return turn


def follow_up_due(turn: Turn) -> dict | None:
    """What the turn leaves for after its reply, as threads.pending_follow_up holds it: the summary, or nothing."""
    if turn.message_id is None or not turn.needs_summary:
        return None
    return _summary_waiting(turn.message_id)


def _summary_waiting(message_id: uuid.UUID | str) -> dict:
    """The summary left waiting for after Mani's reply `message_id`, as threads.pending_follow_up holds it."""
    return {"message_id": str(message_id), "summary": True}


@dataclass(frozen=True)
class FollowedUp:
    """What the work after a reply did: whether the summary was brought up to date, and whether it failed and still
    waits for the next request."""

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
    left = _summary_waiting(message_id) if failed else None
    async with pool.as_user(claims) as conn:
        await threads.settle_pending_follow_up(conn, thread_id, claims.user_id, message_id, left)
    return FollowedUp(summarized=summarized, pending=failed)


async def _turn(
    conn: asyncpg.Connection, claims: Claims, thread_id, content: str, client_message_id, *, ask: Ask,
    config: cache.Config, answer_failure: bool,
) -> Turn:
    settings = get_settings()
    if (duplicate := await _arrival(conn, claims, thread_id, client_message_id)) is not None:
        return duplicate
    await threads.lock(conn, thread_id)
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
    # An offer is open while its row stands at the lead-in or the five steps: one they moved past is retired (phase null).
    open_offer = technique if (technique is not None and technique.outcome is TechniqueOutcome.OFFERED
                               and technique.phase in (OFFERING, STEPS)) else None
    tapped = taps.find_tapped_prompt(history, content)
    tap = taps.tap_event(tapped, config.registry, open_offer)
    style_name = resolve_style(
        ctx.thread.conversation_style.value if ctx.thread.conversation_style else None,
        ctx.profile.support_style.value if ctx.profile and ctx.profile.support_style else None,
    )
    if tap.explain is not None:
        return await _explained(conn, ctx, content, tap.explain, style_name, tapped, client_message_id)
    if tap.example is not None:
        return await _fixed_step(conn, ctx, content, example_text(tap.example),
                                 start_buttons(tap.example, with_example=False), tapped, client_message_id)

    check = pause.return_check(ctx)
    answering = None if check is not None else pause.answering(ctx)
    before = safety.State(ctx.thread.safety)
    holding = before is not safety.State.CLEAR or check is not None
    last_reply = next((m.content for m in reversed(history) if m.role is MessageRole.MANI), None)
    if tapped is None and not holding and copies_last_reply(content, last_reply):
        return await _copied_back(conn, ctx, content, client_message_id)
    if not holding:
        await within_limits(conn, claims.user_id, settings)

    wants_title = ctx.thread.message_count >= TITLE_AFTER_MESSAGES and not ctx.thread.title
    end_check_asked = rec.end_check(record) == rec.END_CHECK_ASKED
    # The question after a framework's last stage holds the turn too, but its answer may close the set.
    held = holding and not end_check_asked
    told = facts.facts(
        ctx, config, record=record, style=style_name, running=running if held or not tap.starting else None,
        open_offer=open_offer, event=facts.HELD_START if held and tap.starting else tap.fact, wants_title=wants_title,
        return_check=check, answering_return=answering, end_check_asked=end_check_asked, holding=held,
    )
    model, parameters, routing = composer.model_settings(config, "mani")
    call = await ask(
        [{"role": "system", "content": facts.system_prompt(config, ctx, summary_due=bool(window.dropped))}]
        + conversation(history)
        + [{"role": "user", "content": content}, {"role": "system", "content": told}],
        TurnReply, model=model, purpose=llm_calls.Purpose.CHAT,
        temperature=parameters.get("temperature", client.DEFAULT_TEMPERATURE),
        max_tokens=parameters.get("maxTokens", client.DEFAULT_MAX_TOKENS),
        reasoning_effort=parameters.get("reasoning_effort"), routing=routing, user_id=claims.user_id,
        thread_id=ctx.thread.id, prompt_version_id=None,
    )
    if call is None:
        return await _unanswered(conn, ctx, content, crisis.CRISIS_REPLY if holding else crisis.TROUBLE_REPLY,
                                 before=before, tapped=tapped, client_message_id=client_message_id,
                                 needs_summary=_summary_due(ctx, window))
    return await _apply(conn, ctx, call, content=content, tapped=tapped, tap=tap, record=record, running=running,
                        open_offer=open_offer, check=check, answering=answering, before=before, holding=holding,
                        wants_title=wants_title, end_check_asked=end_check_asked, window=window, config=config,
                        client_message_id=client_message_id, settings=settings, answer_failure=answer_failure,
                        style=style_name)


async def _apply(
    conn, ctx: threads.TurnContext, call: client.Call, *, content, tapped, tap, record, running, open_offer, check,
    answering, before, holding, wants_title, end_check_asked, window, config, client_message_id, settings,
    answer_failure, style,
) -> Turn:
    """What the reply decides, written in this transaction."""
    reply: TurnReply = call.value
    judgment = judged_mod.judge(before, reply.safety, record, return_check=check, answering_return=answering)
    # A worry open on the thread or found in this message comes before anything the reply asks for, except the
    # answer that settles the safety question after a framework's last stage: that one carries the close.
    settles_end_check = end_check_asked and judgment.state_after is safety.State.CLEAR
    guarded = (holding or judgment.state_after is not safety.State.CLEAR) and not settles_end_check
    decision = decide_mod.decide(
        reply, config.registry, thread_id=ctx.thread.id, running=running, open_offer=open_offer, tap=tap,
        record=record, guarded=guarded,
        count_after=ctx.thread.message_count + 2,
        end_check_due=bool(record.get(rec.DANGER_REACHED)) and rec.end_check(record) != rec.END_CHECK_DONE,
        end_check_asked=end_check_asked,
    )
    text = (crisis.pause_reply(judgment.about, settings.crisis_pause_minutes) if judgment.pausing
            else crisis.END_CHECK if decision.end_check else reply.text)
    if judgment.body_emergency and not judgment.pausing:
        text = f"{text.rstrip()}\n\n{crisis.BODY_EMERGENCY}"
    if decision.show_steps is not None:
        text = f"{text.rstrip()}\n\n{steps_text(decision.show_steps, style)}"
    text = without_dashes(text).strip()
    answered = bool(text)
    if not text and not answer_failure:
        raise ServiceError(f"reply on thread {ctx.thread.id} was empty", ErrorCategory.LLM_UNAVAILABLE, retryable=True,
                           user_message="Mani had trouble responding. Please try again.")
    if not text:
        # An empty reply is answered like no reply at all, with the fixed words; its safety judgment still stands, and
        # nothing else it asked for moves.
        logger.warning("reply on thread %s was empty; sending the fixed reply", ctx.thread.id)
        text = (crisis.CRISIS_REPLY if holding or judgment.state_after is not safety.State.CLEAR
                else crisis.TROUBLE_REPLY)
        decision = decide_mod.Decision(declined=rec.declined(record), finished=rec.finished(record))
    prompts = decision.prompts
    # The model's suggested answers show only in the chat: never beside code's own buttons, inside a set or an offer,
    # or on a turn held for safety.
    if answered and not prompts and running is None and open_offer is None and not guarded and not judgment.pausing:
        prompts = suggestion_buttons(reply.options)
    updates, after = _updates(ctx, reply, decision, judgment, record=record, check=check, answering=answering,
                              end_check_asked=end_check_asked, wants_title=wants_title)
    pair = await messages_db.create_pair(
        conn, ctx.thread.id, content, text, selected_prompt=tapped.label if tapped else None,
        prompt_options=[p.model_dump(mode="json", exclude_none=True) for p in prompts] or None,
        client_message_id=client_message_id,
    )
    await threads.apply(conn, ctx.thread.id, ctx.thread.user_id, updates)
    flagged = await _record_danger(conn, ctx, before, judgment, pair)
    paused = await _pause_writes(conn, ctx, judgment, reply, answering=answering, pair=pair,
                                 minutes=settings.crisis_pause_minutes)
    trace = {key: value for key, value in {
        "action": reply.action, "framework": reply.framework, "stage": reply.stage,
        "safety": judged_mod.traced(reply.safety), "paused": judgment.pausing or None,
        "body_emergency": (judgment.body_emergency and not judgment.pausing) or None,
        "buttons": [p.label for p in prompts], "suggested": bool(prompts) and not decision.prompts or None,
        "latency_ms": call.latency_ms, "refused": decision.refused,
        "notes": reply.notes if settings.ai_debug_mode else None,
    }.items() if value not in (None, "", [], {})}
    return Turn(
        message_id=pair.mani_message_id, content=text, created_at=pair.created_at, prompts=prompts,
        title=updates.title or ctx.thread.title, crisis_detected=flagged or judgment.state_after is safety.State.DANGER,
        paused_from=paused.started_at if paused else None, paused_until=paused.ends_at if paused else None,
        was_duplicate=pair.was_duplicate, needs_summary=_summary_due(ctx, window) and not judgment.pausing,
        llm_call_id=call.call_id, understanding=after if settings.ai_debug_mode else None, trace=trace,
        raw_reply=reply.model_dump(mode="json") if settings.ai_debug_mode else None,
    )


def _updates(ctx, reply: TurnReply, decision, judgment, *, record, check, answering, end_check_asked,
             wants_title) -> tuple[threads.ThreadUpdates, dict]:
    """The thread's changes and its record after this turn."""
    after = rec.with_outcomes(record, notes=reply.notes, declined=decision.declined, finished=decision.finished)
    after = judged_mod.safety_record(after, return_check=check, answering_return=answering, judged=judgment,
                                     read_about=reply.safety.about)
    updates = threads.ThreadUpdates()
    if judgment.state_after.value != ctx.thread.safety:
        updates.safety = judgment.state_after.value
    if decision.end_check:
        after[rec.SAFETY_END_CHECK] = rec.END_CHECK_ASKED
        updates.safety = safety.State.UNSURE.value
    elif end_check_asked and decision.technique is not None and decision.technique.phase == FEELINGS:
        after[rec.SAFETY_END_CHECK] = rec.END_CHECK_DONE
    elif judgment.settled_now and rec.end_check(after) == rec.END_CHECK_DONE:
        after.pop(rec.SAFETY_END_CHECK)
    if after != record:
        updates.understanding = after
    if decision.technique is not None:
        updates.technique = decision.technique
    updates.retire_technique = decision.retire_technique
    if wants_title and (title := clean_title(reply.title)):
        updates.title = title
    return updates, after


async def _record_danger(conn, ctx, before: safety.State, judgment, pair) -> bool:
    """The turn that first finds danger is recorded once for review (admin.crisis_events), never with their words."""
    if pair.was_duplicate or judgment.state_after is not safety.State.DANGER or before is safety.State.DANGER:
        return False
    logger.warning("thread %s may be in danger (%s)", ctx.thread.id, judgment.about)
    await threads.mark_crisis(conn, ctx.thread.id, f"safety: {judgment.about or 'danger'}", pair.user_message_id)
    return True


async def _pause_writes(conn, ctx, judgment, reply: TurnReply, *, answering, pair, minutes):
    """An answer to the return check that settles it marks that pause checked; a pausing turn starts a pause."""
    if pair.was_duplicate:
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


async def _explained(conn, ctx, content, framework: Framework, style: str, tapped, client_message_id) -> Turn:
    """A lead-in button: the client's five steps for their style, word for word, with no model call. The offer moves
    to its steps, where the next answer starts it, sets it aside or lets it lapse."""
    turn = await _fixed_step(conn, ctx, content, steps_text(framework, style),
                             start_buttons(framework, with_example=True), tapped, client_message_id)
    if not turn.was_duplicate and ctx.technique is not None:
        await threads.apply(conn, ctx.thread.id, ctx.thread.user_id,
                            threads.ThreadUpdates(technique=ctx.technique.model_copy(update={"phase": STEPS})))
    return turn


async def _fixed_step(conn, ctx, content, text: str, prompts: list[SmartPrompt], tapped, client_message_id) -> Turn:
    """One of the client's fixed offer steps (the five steps, the example), sent with its buttons and no model call."""
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
    reply = openers(check is not None)[style.value]
    pair = await messages_db.create_pair(conn, ctx.thread.id, content, reply, selected_prompt=content.strip(),
                                         client_message_id=client_message_id)
    updates = threads.ThreadUpdates(conversation_style=style)
    if check is not None and not pair.was_duplicate:
        updates.understanding = rec.return_check(ctx.thread.understanding or {}, str(check.pause_id), "asked")
    await threads.apply(conn, ctx.thread.id, ctx.thread.user_id, updates)
    return Turn(message_id=pair.mani_message_id, content=reply, created_at=pair.created_at, title=ctx.thread.title)


def _summary_due(ctx, window) -> bool:
    """Messages have left the window that the summary does not cover yet."""
    return window.dropped > (ctx.summary.summarized_message_count if ctx.summary else 0)


async def _unanswered(conn, ctx, content: str, text: str, *, before: safety.State, tapped, client_message_id,
                      needs_summary: bool) -> Turn:
    """No host answered: the fixed words go out as Mani's reply and nothing else changes, so the safety state, the
    notes and the framework stay where they were."""
    pair = await messages_db.create_pair(conn, ctx.thread.id, content, text,
                                         selected_prompt=tapped.label if tapped else None,
                                         client_message_id=client_message_id)
    return Turn(message_id=pair.mani_message_id, content=text, created_at=pair.created_at, title=ctx.thread.title,
                crisis_detected=before is safety.State.DANGER, was_duplicate=pair.was_duplicate,
                needs_summary=needs_summary, trace={"unanswered": True})


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
         "You've reached today's message limit. Please come back tomorrow. " + crisis.IN_DANGER),
        (settings.minute_message_limit, dt.timedelta(minutes=1),
         "You're sending messages faster than Mani can answer. Please wait a minute and try again. " + crisis.IN_DANGER),
    ):
        if limit and await messages_db.count_from_user_since(conn, user_id, window) >= limit:
            raise ServiceError(f"user {user_id} reached the limit of {limit} per {window}", ErrorCategory.RATE_LIMITED,
                               retryable=True, user_message=user_message)


def conversation(history: list[Message]) -> list[dict[str, str]]:
    return [{"role": "user" if m.role is MessageRole.USER else "assistant", "content": m.content} for m in history]


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
    reply."""
    from mani.db import turn_traces

    await _once_committed(lambda conn: turn_traces.record(
        conn, thread_id=thread_id, message_id=turn.message_id, llm_call_id=turn.llm_call_id, trace=turn.trace,
        raw_reply=turn.raw_reply), f"the trace for message {turn.message_id}")


async def link_call(call_id: uuid.UUID, message_id: uuid.UUID) -> None:
    """Point a recorded model call at the message it produced, once that message is committed."""
    await _once_committed(lambda conn: llm_calls.attach_message(conn, call_id, message_id),
                          f"the link from llm call {call_id} to message {message_id}")


async def _once_committed(write: Callable[[asyncpg.Connection], Awaitable[None]], what: str) -> None:
    """An admin write that needs the turn's message committed, retried while the commit lands. One that never
    succeeds is logged and swallowed."""
    from mani.db import pool

    for attempt in range(1, LINK_RETRY_ATTEMPTS + 1):
        try:
            async with pool.as_admin() as conn:
                await write(conn)
            return
        except asyncpg.PostgresError:
            if attempt == LINK_RETRY_ATTEMPTS:
                logger.warning("could not store %s after %d attempts", what, LINK_RETRY_ATTEMPTS, exc_info=True)
                return
            await asyncio.sleep(LINK_RETRY_DELAY_SECONDS * attempt)
