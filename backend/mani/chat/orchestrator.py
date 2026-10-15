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
from mani.chat import context, eligibility, redraft, repairs, safety
from mani.chat.greeting import (
    CHAT_MORE_LABEL,
    EXPLAIN_LABELS,
    GO_TO_LIBRARY_LABEL,
    TRY_IT_LABEL,
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
    summaries,
    threads,
)
from mani.errors import ErrorCategory, ServiceError
from mani.llm import client
from mani.llm.schema import LibrarySection, Reply, SmartPrompt, WorkingRead
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

# The somatic stage's own safety condition, word for word: "they mention pain, trouble
# breathing, or feeling faint". Checked against the user's own message, never the model's
# drafted text - a place name like "Stomach" must not be mistaken for this.
_MENTIONS_PAIN = re.compile(
    r"\bpain\b|\bhurts?\b|\baches?\b|breath(e|ing)|\bfaint\b|\bdizzy\b|\blightheaded\b",
    re.IGNORECASE,
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


def _checkin_asked_in(history: list[Message]) -> bool:
    """Whether the conversation history actually contains a turn where Mani asked the body
    check-in question - the real flow having reached it, not just the model's current text
    claiming so."""
    return any(
        m.role is MessageRole.MANI
        and any(str(o.get("label", "")) == repairs.PLACE_LABELS[0] for o in (m.prompt_options or []))
        for m in history
    )


def _body_route_step(
    fixed: repairs.Repaired,
    framework_id: str,
    stages: dict,
    style: str,
    content: str,
    previous_phase: str | None,
    awaiting_place: bool,
    checkin_asked: bool,
    describes_body_improvement: bool,
) -> repairs.Repaired:
    """The turn after a body question the person has answered: where they feel it, and then
    the practice for that place. The body is asked about once; the choice of Chat More / Go to
    Library waits for a practice, unless they decline or already know what they will do.

    Covers a person who answers the check-in, one who says they do not know where, and one who
    described their body before the check-in was asked.
    """
    answering = previous_phase == "somatic_checkin" or (
        previous_phase == "somatic_practice" and awaiting_place
    )
    described_early = (
        previous_phase not in ("somatic_checkin", "somatic_practice")
        and fixed.phase == "somatic_checkin"
        and _ASKS_WHAT_NEXT.search(fixed.text) is not None
        # The model's own text matching the handoff phrase is not proof the check-in
        # actually happened - require the real flow to have reached it, or the user's own
        # message to independently describe their body (a place), or the model's own
        # drafted reply judging that the user's message described an improvement.
        and (
            checkin_asked
            or repairs.named_place(content) is not None
            or describes_body_improvement
        )
    )
    if not (answering or described_early) or repairs.declines_or_acts(content):
        return fixed
    stage = stages.get("somatic_practice") or {}
    safety_reply = next(
        (repairs.reply_for(b, style) for b in stage.get("if_unclear") or [] if "pain" in b.get("when", "")),
        None,
    )
    if safety_reply and safety_reply in fixed.text and _MENTIONS_PAIN.search(content):
        return fixed
    place = repairs.named_place(content)
    text, labels = fixed.text, []
    practice = repairs.practice_for(stage, place, style) if place else None
    if practice is not None:
        text, labels = practice
    elif not repairs.practice_in(stage, text, style):
        script = (stage.get("ask") or {}).get(style)
        if not script:
            return fixed
        text = repairs.with_the_check_in(repairs.first_sentence(text), script)
        labels = list(repairs.PLACE_LABELS)
    return dataclasses.replace(
        fixed,
        text=text,
        framework_id=framework_id,
        phase="somatic_practice",
        prompts=[SmartPrompt(label=label) for label in labels],
    )


def _stage_in_force(
    framework: Framework | None,
    technique: TechniqueState | None,
    *,
    accepted_this_turn: bool,
) -> redraft.StageInForce | None:
    """The stage this reply starts from, as [ctx] shows it: the first after the offer on the turn
    they say yes, otherwise the stage in force."""
    if framework is None or technique is None or not technique.phase:
        return None
    index = framework.phase_index(technique.phase)
    if accepted_this_turn and technique.phase == OFFERING:
        index += 1
        asked, asks = False, 0
    elif technique.outcome is TechniqueOutcome.ACCEPTED:
        asked, asks = True, technique.stage_asks
    else:
        return None
    if not 0 < index < len(framework.phases):
        return None
    return redraft.StageInForce(framework.id, framework.phases[index], asked, asks)


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
    # What Mani made of them on this reply, slot by slot, exactly as stored for the next turn, and
    # what code did to it on the way. Only with AI_DEBUG_MODE, so the read can be watched turn by turn.
    working_read: dict | None = None
    read_notes: list[str] | None = None
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
    # is not running, so it must not strip technique buttons or keep the imminent-action offer
    # switched off.
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
    # call entirely; concern only suppresses the imminent-action offer below, so the model still answers.
    assessment = safety.screen(content)
    if assessment.level is safety.Level.CRISIS:
        return await _handle_crisis(
            conn, ctx, content,
            reason=f"safety screen: {assessment.category.value if assessment.category else 'unspecified'}",
            reply_text=safety.protocol_for(assessment.category),
            tapped=tapped, client_message_id=client_message_id, settings=settings,
            updates=updates,
        )

    # Read by the imminent-action check below and by the capsule repair further down, which needs
    # everything they have said rather than only this turn.
    user_texts = [m.content for m in history if m.role is MessageRole.USER] + [content]
    # Mani's own earlier replies, which the offer gate reads: a set of questions may not be
    # offered until one of them has put an understanding to the person and they have answered it.
    mani_texts = [m.content for m in history if m.role is MessageRole.MANI]
    # Their names, so an earlier offer's own words are not read as an understanding of the person.
    previous_read = WorkingRead.stored(ctx.summary.working_read if ctx.summary else None)
    framework_names = tuple(
        f.name for f in (config.registry.get(fid) for fid in config.registry.ids) if f
    )

    # Which framework fits is the model's call, from the Framework Index. Code decides only the one
    # case it must not leave to the model: an imminent action is offered a pause now, with the
    # offering stage in hand. repairs.apply and redraft still check whatever is offered.
    candidate = None
    # Only while the framework it points to is available; with that one paused, nothing is urgent.
    urgent = (
        eligibility.IMMINENT_ACTION_FRAMEWORK in config.registry and eligibility.urgent(user_texts)
    )
    if urgent and technique is None and assessment.level is safety.Level.NONE:
        candidate = config.registry.get(eligibility.IMMINENT_ACTION_FRAMEWORK)

    running_framework = config.registry.get(technique.framework_id) if technique else None

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
        ctx, framework=active_framework, candidate=candidate,
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
    clear_ok = context.cooldown_passed(ctx)
    framework_going = ctx.technique is not None and ctx.technique.outcome is TechniqueOutcome.ACCEPTED
    # Every reply before an offer asks one question, so the conversation keeps moving. Not while
    # the questions run (each stage asks its own), not on a safety concern, and not when the draft
    # itself chose a shape that asks nothing, which is how it answers someone who only wants to be heard.
    needs_question = not framework_going and not assessment.blocks_framework

    # They asked about the offer still open, by tapping Tell me more or typing a question the
    # draft itself reports as about the offer. The reply answers and offers the same one again,
    # which is not a new offer and waits for nothing.
    def _asked_about(draft: Reply) -> bool:
        """They asked about the open offer: Tell me more, or a typed question the draft itself
        reports as about the offer (state names it, accepted left null)."""
        if offer is None:
            return False
        if tapped is not None and tapped.label.strip().lower() in EXPLAIN_LABELS:
            return True
        return bool(
            deferred and draft.state is not None
            and draft.state.technique == offer.technique and draft.state.accepted is None
        )

    def _accepts(draft: Reply) -> bool:
        """A yes typed to the offer still open, which the draft itself reports and the outcome
        below is read from."""
        return (
            tapped is None and technique is not None and technique.outcome is TechniqueOutcome.OFFERED
            and draft.state is not None and draft.state.accepted is True
        )

    def _why(draft: Reply) -> list[str]:
        return redraft.reasons(
            draft, user_texts, config.registry,
            # A typed reply to an offer already open is Keep chatting unless it asks about the
            # offer, so offering again there waits out the cooldown; the repeat used to be dropped
            # and leave no question.
            offer_not_allowed=not _asked_about(draft) and not clear_ok,
            may_offer=clear_ok and not assessment.blocks_framework and not framework_going
            and not deferred,
            needs_question=needs_question,
            stage_in_force=None if assessment.blocks_framework else _stage_in_force(
                running_framework, technique, accepted_this_turn=accepted_this_turn or _accepts(draft),
            ),
            last_mani_text=next(
                (m.content for m in reversed(history) if m.role is MessageRole.MANI), None
            ),
            mani_texts=mani_texts,
            framework_names=framework_names,
            urgent=urgent,
            previous_read=previous_read,
        )

    why = _why(reply)
    attempts = 0
    spent_ms = call.latency_ms
    # A draft that names a feeling they never did, offers before it may, offers what they said
    # rules out, or asks nothing gets one more try, told why; a missing question, a confusion
    # read as an answer, a question moved on from unanswered, or an under-answered multi-question
    # message gets a second. What still fails is corrected by repairs.apply.
    while why and attempts < 2 and (attempts == 0 or any(
        "asks no question" in w
        or "is confusion, not an answer" in w
        or "you moved on from" in w
        or "questions in that message and you answered" in w
        for w in why
    )):
        left = redraft.redraft_seconds(spent_ms)
        if left is None:
            # A slow provider makes every call slow, so a redraft would double a turn that has
            # already kept them waiting. The draft in hand stands and repairs.apply corrects it.
            logger.warning(
                "thread %s skipping redraft after %d ms: %s", ctx.thread.id, spent_ms, "; ".join(why)
            )
            break
        logger.info("thread %s redrafting: %s", ctx.thread.id, "; ".join(why))
        try:
            again = await client.complete(
                [{"role": "system", "content": system.text}]
                + _conversation(history)
                + [{"role": "user", "content": context.with_rewrite_notes(prefix, why) + for_model}],
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
                timeout_seconds=left,
            )
        except ServiceError as failed:
            if failed.category not in (ErrorCategory.LLM_TIMEOUT, ErrorCategory.LLM_UNAVAILABLE):
                raise
            # The draft already in hand is a whole reply and repairs.apply corrects what it can;
            # losing the person's message because the second try stalled costs more than a
            # draft that was only flagged.
            logger.warning("thread %s redraft failed (%s); keeping the first draft", ctx.thread.id, failed.category)
            break
        reply = again.value
        spent_ms += again.latency_ms
        attempts += 1
        why = _why(reply)
    asked_about_offer = _asked_about(reply)
    if reply.heading_toward:
        # Read by the steering evals and by anyone asking why a question went where it did:
        # the id only, never a word of what the person said.
        logger.info("thread %s heading toward %s", ctx.thread.id, reply.heading_toward)
    if reply.next_move == "offer" or redraft.offered(reply, config.registry):
        # What the draft claimed about having put an understanding to them, against what its own
        # earlier replies bear out. Two words, so a model that claims it without having done it
        # can be counted rather than only read about in a transcript.
        logger.info(
            "thread %s offering with understanding_said=%s, borne out: %s",
            ctx.thread.id, reply.understanding_said,
            redraft.stated_understanding(mani_texts, user_texts, framework_names),
        )
    if framework_going and not reply.stages_known and not assessment.blocks_framework:
        # Counted to decide whether a missing ledger needs its own redraft: ids only.
        logger.warning("thread %s framework turn without stages_known", ctx.thread.id)
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

    if asked_about_offer and offer.technique and not any(p.technique for p in reply.prompts or []):
        # Asking about the offer is answered by making it again. A reply that explained and
        # stopped left the offer with no buttons, and the yes typed after it started nothing.
        reply = reply.model_copy(
            update={"prompts": [SmartPrompt(label=TRY_IT_LABEL, technique=offer.technique)]}
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
            asked_about_it = asked_about_offer
            if not asked_about_it or (reply.state is not None and reply.state.accepted is False):
                outcome = TechniqueOutcome.DECLINED
    elif (
        tapped is None
        and technique is not None
        and outcome is TechniqueOutcome.OFFERED
        and reply.state is not None
        and reply.state.accepted is True
        and reply.state.technique == technique.framework_id
    ):
        # An offer can stay open with no buttons under Mani's last reply, when the answer to Tell
        # me more asked something else. A yes to it is still a yes; read from the offer that is
        # open, not from whether buttons were showing, or the questions run while it says offered.
        outcome = TechniqueOutcome.ACCEPTED
        accepted_this_turn = True
        offered_now.append(technique.framework_id)
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
        # An offer a second draft still makes after what they said ruled it out is dropped the
        # way an early one is.
        # An offer that a second draft still makes without having put an understanding to them
        # is dropped here, the way one made before the cooldown is. Otherwise the redraft is the
        # only thing standing between a premature offer and the person reading it.
        cooldown_passed=(
            clear_ok
            and outcome is not TechniqueOutcome.DECLINED
            and not redraft.ruled_out(reply, user_texts, config.registry)
            # An imminent action is the one offer that cannot wait to be understood first.
            and (urgent or redraft.understanding_ok(
                reply, mani_texts, user_texts, framework_names
            ))
        ),
        conversation_style=context.resolve_style(ctx),
        wants_title=wants_title,
        # An offer made again after they asked what it involves doesn't repeat the description.
        last_mani_text=next((m.content for m in reversed(history) if m.role is MessageRole.MANI), None),
        nickname=ctx.profile.nickname if ctx.profile else None,
        # The greeting says their name by design; the model's own replies count from there.
        name_said_before=bool(
            ctx.profile and ctx.profile.nickname
            and any(ctx.profile.nickname in m.content
                    for m in [m for m in history if m.role is MessageRole.MANI][1:])
        ),
        clarification_already_used=context.clarification_used(history),
        offer_asked_about=asked_about_offer,
        stage_exhausted=(
            technique is not None and not accepted_this_turn
            and technique.stage_asks >= context.MAX_STAGE_ASKS
        ),
    )
    if assessment.blocks_framework or model_concern:
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
    checkin_asked = _checkin_asked_in(history)
    describes_body_improvement = reply.describes_body_improvement is True
    if technique is not None and not (assessment.blocks_framework or model_concern):
        fixed = _body_route_step(
            fixed,
            technique.framework_id,
            config.registry.get(technique.framework_id).stages,
            context.resolve_style(ctx),
            content,
            technique.phase,
            _awaiting_place(history),
            checkin_asked,
            describes_body_improvement,
        )
    # The model's own text matching the handoff phrase is not proof the check-in actually
    # happened: the real flow must have asked it, or the user's own message must independently
    # describe their body. Otherwise the text is trusted as fresh model prose and the
    # mandatory check-in script still runs.
    checkin_satisfied = (
        checkin_asked
        or repairs.named_place(content) is not None
        or describes_body_improvement
        or repairs.declines_or_acts(content)
    )
    if (
        fixed.phase == "somatic_checkin" and fixed.framework_id is not None
        and not (checkin_satisfied and _ASKS_WHAT_NEXT.search(fixed.text))
    ):
        # The client's flow (2026-09-24): the body check-in is fixed content, sent word for
        # word, never reworded. Skipped when they already described their body and this
        # reply moves straight to the two choices instead of asking again.
        stage = config.registry.get(fixed.framework_id).stages.get("somatic_checkin") or {}
        script = (stage.get("ask") or {}).get(context.resolve_style(ctx))
        if script:
            fixed = dataclasses.replace(fixed, text=repairs.with_the_check_in(fixed.text, script))
    if fixed.notes:
        logger.info("repaired reply on thread %s: %s", ctx.thread.id, "; ".join(fixed.notes))
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
            prompts=(
                _handoff() if checkin_satisfied and _ASKS_WHAT_NEXT.search(fixed.text)
                else without_handoff
            ),
        )
    if retiring_framework_id is not None and repairs.comes_back(content):
        # The client's words for a feeling that returns after the practice, sent as written.
        returning = repairs.returning_reply(
            config.registry.get(retiring_framework_id).stages.get("somatic_practice") or {},
            context.resolve_style(ctx),
        )
        if returning:
            fixed = dataclasses.replace(fixed, text=returning)
    if (
        retiring_framework_id is not None
        and content.strip().lower() not in _HANDOFF_LABELS
        and not _offered_handoff(history)
    ):
        # The reply that ends a framework offers the client's two choices, always and
        # exactly. Left to the model they came back mislabeled or missing. Skipped when
        # they have already chosen one, or were just offered both.
        fixed = dataclasses.replace(fixed, prompts=_handoff())
    elif (
        technique is None
        and retiring_framework_id is None
        and _ASKS_WHAT_NEXT.search(fixed.text) is not None
    ):
        # No framework is live this turn, and none just retired - but the model wrote the
        # "keep chatting or go to the Library" sentence on its own initiative anyway (e.g. on
        # a later turn, well after a framework's state row was retired). The sentence still
        # means the same two choices, so it still gets the same buttons.
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
        updates.style = ResponseStyle(shape=fixed.style.shape)
    read_notes: list[str] = []
    if (
        not redraft.offered(reply, config.registry) and not framework_going
        and (asked_known := redraft.asks_what_is_known(reply, previous_read, mani_texts))
    ):
        read_notes.append(f"still asks for something it already has ({asked_known}), even after a redraft")
    if redraft.same_unknown(previous_read, reply):
        read_notes.append("still trying to find out the same thing as last reply")
        logger.info("thread %s read still after the same unknown as last reply", ctx.thread.id)
    stored_read: WorkingRead | None = None
    if reply.working_read and not assessment.blocks_framework:
        # Carried to the next turn so the reading goes forward rather than being formed again
        # from nothing. Not on a safety turn: the reply there is not the work of a reading. A
        # feeling they never named is taken out first, or it would be read as theirs from then on.
        read, invented = repairs.grounded_read(reply.working_read, user_texts)
        if invented:
            read_notes.append(f"dropped feeling word(s) they never used: {', '.join(invented)}")
            logger.info(
                "thread %s dropped %d feeling word(s) they did not use from the read",
                ctx.thread.id, len(invented),
            )
        stored_read = repairs.carried_read(previous_read, read)
        updates.working_read = stored_read.model_dump_json()
    if fixed.title:
        updates.title = fixed.title

    await threads.apply(conn, ctx.thread.id, user_id, updates)

    exercise = None
    if retiring_framework_id is not None:
        said = [m.content for m in history if m.role is MessageRole.USER][-2:] + [content]
        exercise = await _offer_exercise(
            conn, retiring_framework_id, config, model, routing, user_id, ctx.thread.id,
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
        working_read=stored_read.model_dump() if settings.ai_debug_mode and stored_read else None,
        read_notes=read_notes if settings.ai_debug_mode else None,
        ledger=(
            redraft.ledger_view(
                reply,
                config.registry.get(reply.state.technique) if reply.state else running_framework,
                fixed.phase or (technique.phase if technique else None),
            )
            if settings.ai_debug_mode and (reply.stages_known or framework_going)
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


async def summary_snapshot(
    conn: asyncpg.Connection, thread_id: uuid.UUID | str, user_id: str
) -> tuple[list[Message], object | None]:
    """The messages a summary run should read, and the summary it is updating."""
    existing = await summaries.get(conn, thread_id)
    page = await messages_db.list_for_thread(conn, thread_id, user_id, limit=200)
    return list(reversed(page.messages)), existing
