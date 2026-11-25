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
from mani.chat import crisis, decide as decide_mod, enforce, facts, pause, questions, record as rec, rewind, safety, taps, worry
from mani.chat.greeting import (
    COPIED_BACK, OPENERS, STYLE_OPTIONS, greeting, resolve_style,
)
from mani.chat.repairs import clean_title, start_buttons
from mani.chat.reply import TurnReply, shaped
from mani.chat.techniques import FEELINGS, OFFERING, STEPS, steps_text
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
    # What the pause this turn started is for: overdose, or whose danger it is (R90).
    paused_for: str | None = None
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
    turn = await _respond(conn, claims, ctx, content, client_message_id, ask=ask, config=config,
                          answer_failure=answer_failure, settings=settings)
    # Saved once the turn is written, from the context it started on. A turn that asks the model ends its read at
    # the ask and rolls back, so the snapshot is written only by the pass that keeps it.
    await rewind.save(conn, ctx, claims.user_id)
    return turn


async def _respond(
    conn: asyncpg.Connection, claims: Claims, ctx, content: str, client_message_id, *, ask: Ask,
    config: cache.Config, answer_failure: bool, settings,
) -> Turn:
    thread_id = ctx.thread.id
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
    check = pause.return_check(ctx)
    answering = None if check is not None else pause.answering(ctx)
    stood = worry.standing(ctx, check, answering)
    before = stood.state
    holding = before is not safety.State.CLEAR or check is not None or answering is not None
    # A held turn (an open worry, or the question owed after a pause) goes to the model, never to a fixed step.
    if tap.explain is not None and not holding:
        return await _explained(conn, ctx, content, tap.explain, style_name, tapped, client_message_id)
    last_reply = next((m.content for m in reversed(history) if m.role is MessageRole.MANI), None)
    if tapped is None and not holding and copies_last_reply(content, last_reply):
        return await _copied_back(conn, ctx, content, client_message_id)
    if not holding:
        await within_limits(conn, claims.user_id, settings)

    wants_title = ctx.thread.message_count >= TITLE_AFTER_MESSAGES and not ctx.thread.title
    person_messages = _person_messages(history)
    end_check_asked = rec.end_check(record) == rec.END_CHECK_ASKED
    # The question after a framework's last stage holds the turn too, but its answer may close the set.
    held = holding and not end_check_asked
    told_running = running if held or not tap.starting else None
    told_offer = (open_offer if open_offer is None or decide_mod.offer_current(open_offer, ctx.thread.message_count)
                  else None)
    # Show me how's own fact replaces what the lead-in says comes next; on a held turn the tap's fact is not said.
    told = facts.facts(
        ctx, config, record=record, style=style_name, running=told_running,
        open_offer=told_offer if tap.demonstrate is None else None,
        event=(facts.HELD_START if tap.starting else None) if held and (tap.starting or tap.demonstrate) else tap.fact,
        wants_title=wants_title,
        return_check=check, answering_return=answering, end_check_asked=end_check_asked, holding=held, stood=stood,
        person_messages=person_messages,
    )
    # The schema offers only what the facts allow, so a reply code already knows it would refuse is never written.
    shape = shaped(facts.offerable(config, record=record, running=told_running, open_offer=told_offer, holding=held,
                                   person_messages=person_messages, state=before))
    model, parameters, routing = composer.model_settings(config, "mani")
    try:
        call = await ask(
            [{"role": "system", "content": facts.system_prompt(config, ctx, summary_due=bool(window.dropped))}]
            + conversation(history)
            + [{"role": "user", "content": content}, {"role": "system", "content": told}],
            shape, model=model, purpose=llm_calls.Purpose.CHAT,
            temperature=parameters.get("temperature", client.DEFAULT_TEMPERATURE),
            max_tokens=parameters.get("maxTokens", client.DEFAULT_MAX_TOKENS),
            reasoning_effort=worry.HELD_REASONING_EFFORT if holding else parameters.get("reasoning_effort"),
            routing=routing, user_id=claims.user_id,
            thread_id=ctx.thread.id, prompt_version_id=None,
        )
        if call is None:
            return await _unanswered(conn, ctx, content, crisis.CRISIS_REPLY if holding else crisis.TROUBLE_REPLY,
                                     before=before, tapped=tapped, client_message_id=client_message_id,
                                     needs_summary=_summary_due(ctx, window))
        return await _apply(conn, ctx, call, content=content, tapped=tapped, tap=tap, record=record, running=running,
                            open_offer=open_offer, check=check, answering=answering, stood=stood, holding=holding,
                            wants_title=wants_title, end_check_asked=end_check_asked, window=window, config=config,
                            client_message_id=client_message_id, settings=settings, answer_failure=answer_failure,
                            style=style_name, person_messages=person_messages)
    except ServiceError as error:
        # Any refusal while a worry is held names where to get help (S9, S10). PROVISIONAL: clinician sign-off
        # required before deploy.
        if not holding:
            raise
        raise crisis.with_help(error) from error


async def _apply(
    conn, ctx: threads.TurnContext, call: client.Call, *, content, tapped, tap, record, running, open_offer, check,
    answering, stood, holding, wants_title, end_check_asked, window, config, client_message_id, settings,
    answer_failure, style, person_messages,
) -> Turn:
    """What the reply decides, written in this transaction."""
    reply: TurnReply = call.value
    judgment = worry.step(stood, reply.safety, content)
    # A worry open on the thread or found in this message comes before anything the reply asks for, except the
    # answer that settles the safety question after a framework's last stage: that one carries the close.
    settles_end_check = end_check_asked and judgment.state is safety.State.CLEAR
    guarded = (holding or judgment.state is not safety.State.CLEAR) and not settles_end_check
    # A typed wish to stop is read as one, so the close follows with no question (R95).
    reply, enforced = enforce.read_stop(reply, content, guarded=guarded)
    decision = decide_mod.decide(
        reply, config.registry, thread_id=ctx.thread.id, running=running, open_offer=open_offer, tap=tap,
        record=record, guarded=guarded,
        count_after=ctx.thread.message_count + 2,
        end_check_due=bool(record.get(rec.DANGER_REACHED)) and rec.end_check(record) != rec.END_CHECK_DONE,
        end_check_asked=end_check_asked, person_messages=person_messages,
    )
    ask = ""
    if judgment.pausing:
        # The model wrote its reply before code decided to pause, so its words can invite more conversation the pause
        # then blocks (TC-S3, 2026-11-25: a work question under the pause). A pausing turn says only code's pause words,
        # where to get help first. CR-7, PROVISIONAL: clinician sign-off required before deploy.
        text = crisis.pause_reply(judgment.about, settings.crisis_pause_seconds)
    elif decision.end_check:
        text = crisis.END_CHECK
    elif check is not None:
        text = (crisis.RETURN_DANGER_REPLY if reply.safety.level == "danger"
                else crisis.return_check_reply(judgment.about or stood.about))
    elif answering is not None and judgment.state is safety.State.CLEAR:
        # Their answer that they are all right gets code's one follow-up in place of the reply's question (S12).
        # PROVISIONAL: clinician sign-off required before deploy.
        text, ask = reply.text, crisis.AFTER_PAUSE_FOLLOW_UP
    else:
        text, ask = reply.text, reply.question.ask
    # Every reply asks one question at most, its own, after its text; a guarded turn's words lose nothing. The open
    # chat, with no set, offer or safety worry in play, asks none after frustration and keeps the question it asked.
    # An offer code refused leaves the reply in the open chat: no buttons follow its lead-in.
    open_chat = questions.in_open_chat(
        in_play=running is not None or open_offer is not None or decision.technique is not None, guarded=guarded,
        action="none" if decision.refused == "offer" else reply.action)
    # A reply at the offer, its lead-in or the reply its five steps follow, begins no stage (RF-1).
    offered = decision.show_steps or (config.registry.get(reply.framework) if decision.technique is not None
                                      and decision.technique.phase == OFFERING else None)
    sent = enforce.sent(text, ask, fixed=judgment.pausing or decision.end_check or check is not None,
                        guarded=guarded, open_chat=open_chat, latest=reply.question.latest,
                        directive=style == SupportStyle.DIRECTIVE, helping=reply.said.move.strip().lower() == "help",
                        openers=[entry.get("opens", "") for entry in rec.replies(record)], offered=offered,
                        stage=reply.stage)
    text, asked, cut = sent.text, sent.asked, sent.cut
    enforced += sent.enforced
    # What the reply asked and gave, kept before code adds its own pieces; the fixed words for an empty reply give none.
    entry = _ledger_entry(reply, text, asked, open_chat=open_chat) if text else None
    if not text and not answer_failure:
        raise ServiceError(f"reply on thread {ctx.thread.id} was empty", ErrorCategory.LLM_UNAVAILABLE, retryable=True,
                           user_message="Mani had trouble responding. Please try again.")
    if not text:
        # An empty reply is answered like no reply at all, with the fixed words; its safety judgment still stands, and
        # nothing else it asked for moves.
        logger.warning("reply on thread %s was empty; sending the fixed reply", ctx.thread.id)
        text = (crisis.CRISIS_REPLY if holding or judgment.state is not safety.State.CLEAR
                else crisis.TROUBLE_REPLY)
        decision = decide_mod.Decision(declined=rec.declined(record), finished=rec.finished(record))
    # Code's own pieces follow the reply only once it says something: where to get help, and the five steps. The first
    # danger of a kind always names its numbers (S2, S7). PROVISIONAL: clinician sign-off required before deploy.
    added_help = crisis.help_missing(text, judgment.about) if judgment.resources_due else None
    resources_added = added_help is not None
    if resources_added:
        text = f"{text}\n\n{added_help}"
    if decision.show_steps is not None:
        text = f"{text}\n\n{steps_text(decision.show_steps, style)}"
    prompts = decision.prompts
    updates, after = _updates(ctx, reply, decision, judgment, record=record, check=check, answering=answering,
                              end_check_asked=end_check_asked, wants_title=wants_title, entry=entry)
    pair = await messages_db.create_pair(
        conn, ctx.thread.id, content, text, selected_prompt=tapped.label if tapped else None,
        prompt_options=[p.model_dump(mode="json", exclude_none=True) for p in prompts] or None,
        client_message_id=client_message_id,
    )
    await threads.apply(conn, ctx.thread.id, ctx.thread.user_id, updates)
    flagged = await _record_danger(conn, ctx, stood.state, judgment, pair)
    paused = await _pause_writes(conn, ctx, judgment, reply, pair=pair,
                                 seconds=settings.crisis_pause_seconds)
    trace = {key: value for key, value in {
        "action": reply.action, "framework": reply.framework, "stage": reply.stage,
        "safety": worry.traced(reply.safety), "paused": judgment.pausing or None,
        "resources_added": resources_added or None, "raised_by_phrase": judgment.raised or None,
        "buttons": [p.label for p in prompts], "latency_ms": call.latency_ms, "first_token_ms": call.first_token_ms,
        "refused": decision.refused,
        "question_cut": cut, "enforced": enforced, "question": reply.question.model_dump() if open_chat and settings.ai_debug_mode else None,
        "notes": reply.notes if settings.ai_debug_mode else None,
    }.items() if value not in (None, "", [], {})}
    return Turn(
        message_id=pair.mani_message_id, content=text, created_at=pair.created_at, prompts=prompts,
        title=updates.title or ctx.thread.title, crisis_detected=flagged or judgment.state is safety.State.DANGER,
        paused_from=paused.started_at if paused else None, paused_until=paused.ends_at if paused else None,
        paused_for=paused.paused_for if paused else None,
        was_duplicate=pair.was_duplicate, needs_summary=_summary_due(ctx, window) and not judgment.pausing,
        llm_call_id=call.call_id, understanding=after if settings.ai_debug_mode else None, trace=trace,
        raw_reply=call.value.model_dump(mode="json") if settings.ai_debug_mode else None,
    )


def _ledger_entry(reply: TurnReply, text: str, asked: str, *, open_chat: bool) -> dict:
    """What the reply asked and gave, as rec.with_reply takes it: the question it sent with its job (in a set, the stage
    it asks), whether it was in the open chat, its move and gist, and its text."""
    intent = reply.question.intent.strip().lower()
    if not asked:
        intent = "none"
    elif reply.stage and not open_chat:
        intent = reply.stage
    elif intent not in questions.INTENTS:
        intent = "unsaid"
    return {"question": asked, "intent": intent, "open_chat": open_chat, "move": reply.said.move,
            "gist": reply.said.gist, "text": text}


def _updates(ctx, reply: TurnReply, decision, judgment, *, record, check, answering, end_check_asked,
             wants_title, entry: dict | None) -> tuple[threads.ThreadUpdates, dict]:
    """The thread's changes and its record after this turn. `entry`: what the reply asked and gave, None when the
    fixed words went out in its place."""
    after = rec.with_outcomes(record, notes=reply.notes, people=[p.model_dump() for p in reply.people],
                              events=[e.model_dump() for e in reply.events], declined=decision.declined,
                              finished=decision.finished, library=decision.library)
    after = rec.with_answer(after, reply.question.answered)
    if entry is not None:
        after = rec.with_reply(after, **entry)
    after = worry.record_after(after, judgment, check=check, answering=answering)
    updates = threads.ThreadUpdates()
    if judgment.state.value != ctx.thread.safety:
        updates.safety = judgment.state.value
    if decision.end_check:
        after[rec.SAFETY_END_CHECK] = rec.END_CHECK_ASKED
        updates.safety = safety.State.UNSURE.value
    elif end_check_asked and decision.technique is not None and decision.technique.phase == FEELINGS:
        after[rec.SAFETY_END_CHECK] = rec.END_CHECK_DONE
    elif end_check_asked and (decision.retire_technique or (
            decision.technique is not None and decision.technique.outcome is not TechniqueOutcome.ACCEPTED)):
        # The set ended another way while the question waited, so no question stays marked as asked.
        after.pop(rec.SAFETY_END_CHECK)
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
    if pair.was_duplicate or judgment.state is not safety.State.DANGER or before is safety.State.DANGER:
        return False
    logger.warning("thread %s may be in danger (%s)", ctx.thread.id, judgment.about)
    await threads.mark_crisis(conn, ctx.thread.id, f"safety: {judgment.about or 'danger'}", pair.user_message_id)
    return True


async def _pause_writes(conn, ctx, judgment, reply: TurnReply, *, pair, seconds):
    """A pausing turn starts a pause."""
    if pair.was_duplicate:
        return None
    if judgment.pausing:
        return await pauses.start(conn, ctx.thread.user_id, ctx.thread.id, seconds, reply.safety.why,
                                  judgment.paused_for)
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
    if reply_message is not None and reply_message.content in crisis.UNREAD_REPLIES:
        # The model never answered this message, so the retry runs the turn instead of repeating the fixed words, from
        # the state before it. Only the conversation's last turn can be taken back; any other keeps its stored reply.
        try:
            await rewind.undo_last_turn(conn, claims.user_id, thread_id, user_message.id)
            return None
        except ServiceError:
            pass
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
    """Not sure: the client's five steps for their style, word for word, with no model call. The offer moves to its
    steps, where the next answer starts it, sets it aside or lets it lapse."""
    turn = await _fixed_step(conn, ctx, content, steps_text(framework, style),
                             start_buttons(framework), tapped, client_message_id)
    if not turn.was_duplicate and ctx.technique is not None:
        await threads.apply(conn, ctx.thread.id, ctx.thread.user_id,
                            threads.ThreadUpdates(technique=ctx.technique.model_copy(update={"phase": STEPS})))
    return turn


async def _fixed_step(conn, ctx, content, text: str, prompts: list[SmartPrompt], tapped, client_message_id) -> Turn:
    """One of the client's fixed offer steps (the five steps), sent with its buttons and no model call."""
    pair = await messages_db.create_pair(
        conn, ctx.thread.id, content, text, selected_prompt=tapped.label,
        prompt_options=[p.model_dump(mode="json", exclude_none=True) for p in prompts],
        client_message_id=client_message_id,
    )
    return Turn(message_id=pair.mani_message_id, content=text, created_at=pair.created_at, prompts=prompts,
                title=ctx.thread.title, was_duplicate=pair.was_duplicate)


async def _open_in_style(conn, ctx, content: str, style: SupportStyle, client_message_id) -> Turn:
    """The chosen style, with that style's fixed opener and no model call."""
    reply = OPENERS[style.value]
    pair = await messages_db.create_pair(conn, ctx.thread.id, content, reply, selected_prompt=content.strip(),
                                         client_message_id=client_message_id)
    await threads.apply(conn, ctx.thread.id, ctx.thread.user_id, threads.ThreadUpdates(conversation_style=style))
    return Turn(message_id=pair.mani_message_id, content=reply, created_at=pair.created_at, title=ctx.thread.title)


def _person_messages(history: list[Message]) -> int:
    """How many messages the person has sent in this conversation, this one included. The tap that chose the style
    answers the greeting's style buttons and is not one of theirs."""
    count, styles_shown = 1, False
    for message in history:
        if message.role is MessageRole.MANI:
            styles_shown = any(option.get("style") for option in message.prompt_options or [])
        elif not styles_shown:
            count += 1
    return count


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
    """Store the turn's trace beside its committed message. A trace that cannot be stored costs a review, never a
    reply."""
    from mani.db import turn_traces

    await _stored_or_logged(lambda conn: turn_traces.record(
        conn, thread_id=thread_id, message_id=turn.message_id, llm_call_id=turn.llm_call_id, trace=turn.trace,
        raw_reply=turn.raw_reply), f"the trace for message {turn.message_id}")


async def link_call(call_id: uuid.UUID, message_id: uuid.UUID) -> None:
    """Point a recorded model call at the committed message it produced."""
    await _stored_or_logged(lambda conn: llm_calls.attach_message(conn, call_id, message_id),
                            f"the link from llm call {call_id} to message {message_id}")


async def _stored_or_logged(write: Callable[[asyncpg.Connection], Awaitable[None]], what: str) -> None:
    """An admin write about a turn whose message is already committed (chat/runner.py commits before the route
    responds). One that fails is logged and swallowed: it costs a record, never a delivered reply."""
    from mani.db import pool

    try:
        async with pool.as_admin() as conn:
            await write(conn)
    except asyncpg.PostgresError:
        logger.warning("could not store %s", what, exc_info=True)
