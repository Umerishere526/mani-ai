# ABOUTME: The chat endpoints - read a thread's history, send one turn, and run what it left for after the reply.
# ABOUTME: Sending holds no connection while the model thinks; the work after a reply is the app's own request.

import asyncio
import datetime as dt
import uuid

from fastapi import APIRouter, Query

from mani.auth.deps import CurrentUser, Participant
from mani.chat import orchestrator, runner
from mani.config import get_settings
from mani.db import messages as messages_db
from mani.db.deps import UserConn
from mani.models.api import EditMessageIn, FollowUpOut, MessageListOut, SendMessageIn, TurnOut
from mani.routers.serializers import to_messages

router = APIRouter(prefix="/v1/threads/{thread_id}/messages", tags=["chat"])


@router.get("", response_model=MessageListOut)
async def list_messages(
    user: CurrentUser,
    conn: UserConn,
    thread_id: uuid.UUID,
    limit: int = Query(default=messages_db.DEFAULT_PAGE, ge=1, le=100),
    cursor: dt.datetime | None = None,
) -> MessageListOut:
    page = await messages_db.list_for_thread(conn, thread_id, user.user_id, limit, cursor)
    live = await messages_db.latest_mani_id(conn, thread_id, user.user_id)
    return MessageListOut(
        messages=to_messages(page.messages, live), next_cursor=page.next_cursor
    )


@router.post("", response_model=TurnOut, status_code=201)
async def send(
    user: Participant,
    thread_id: uuid.UUID,
    body: SendMessageIn,
) -> TurnOut:
    """One user message in, one reply out.

    One provider call on the person's wait: the checks that the previous implementation
    answered with a regeneration - up to six of them - are deterministic corrections in
    `chat/repairs.py`. A chat turn's reading of them is a second call, asked for by the app after the reply
    (`follow_up` below).
    """
    turn = await runner.send(user, thread_id, body.content, body.client_message_id)
    return await _turn_out(thread_id, turn)


@router.post("/{message_id}/edit", response_model=TurnOut, status_code=201)
async def edit(
    user: Participant,
    thread_id: uuid.UUID,
    message_id: uuid.UUID,
    body: EditMessageIn,
) -> TurnOut:
    """Replace the person's last message: it and Mani's reply are removed, the thread state returns to what it
    was before that turn, and the new text runs as a fresh turn. The write takes it back and runs the new text in
    one transaction, so a failed turn leaves the original exchange in place."""
    turn = await runner.edit(user, thread_id, message_id, body.content)
    return await _turn_out(thread_id, turn)


@router.post("/{message_id}/follow-up", response_model=FollowUpOut)
async def follow_up(user: Participant, thread_id: uuid.UUID, message_id: uuid.UUID) -> FollowUpOut:
    """The work a turn leaves for after its reply `message_id` (Mani's reading of them, the summary when it is due),
    asked for by the app once the reply is shown.

    A request of its own, not work left running after the turn's response: on Vercel the instance stops once a
    response is sent, and about a third of the readings started that way were cut off (2026-11-05). Runs only what
    the turn stored for this reply, once; any other call does nothing and costs nothing.
    """
    done = await orchestrator.follow_up(user, thread_id, message_id)
    return FollowUpOut(
        read=bool(done and done.understanding is not None),
        summarized=bool(done and done.summarized),
        understanding=done.understanding if done and get_settings().ai_debug_mode else None,
    )


async def _turn_out(thread_id: uuid.UUID, turn: orchestrator.Turn) -> TurnOut:
    # Awaited, not left running after the response: Vercel stops the instance once a response is sent, so work
    # started after it was being lost (2026-11-05). Both are database writes only, side by side, and the turn
    # is committed by now (chat/runner.py), so the message they reference is there; each swallows its own failure.
    linking = []
    if turn.llm_call_id and turn.message_id:
        linking.append(orchestrator.link_call(turn.llm_call_id, turn.message_id))
    if turn.trace and turn.message_id and not turn.was_duplicate:
        # Why this turn went the way it did (admin.turn_traces).
        linking.append(orchestrator.record_trace(turn, thread_id))
    await asyncio.gather(*linking)

    return TurnOut(
        id=turn.message_id,
        content=turn.content,
        created_at=turn.created_at,
        prompts=turn.prompts,
        title=turn.title,
        crisis_detected=turn.crisis_detected,
        crisis_blocks_chat=turn.crisis_blocks_chat,
        was_duplicate=turn.was_duplicate,
        reasoning=turn.reasoning,
        ledger=turn.ledger,
        understanding=turn.understanding if get_settings().ai_debug_mode else None,
        check_at_message_count=turn.check_at_message_count if get_settings().ai_debug_mode else None,
        trace=turn.trace if get_settings().ai_debug_mode else None,
        follow_up_pending=bool(turn.read_after or turn.needs_summary) and not turn.was_duplicate,
    )
