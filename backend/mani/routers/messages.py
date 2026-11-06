# ABOUTME: The chat endpoints - read a thread's history, and send one turn.
# ABOUTME: Sending holds no connection while the model thinks: chat/runner.py reads, calls, then writes.

import datetime as dt
import uuid

from fastapi import APIRouter, Query

from mani.auth.deps import CurrentUser, Participant
from mani.auth.jwt import Claims
from mani.background import fire_and_forget
from mani.chat import orchestrator, runner
from mani.config import get_settings
from mani.db import messages as messages_db
from mani.db.deps import UserConn
from mani.models.api import EditMessageIn, MessageListOut, SendMessageIn, TurnOut
from mani.routers.serializers import to_messages
from mani.summarize import update_quietly

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
    `chat/repairs.py`. A chat turn's reading of them is a second call, after the reply.
    """
    turn = await runner.send(user, thread_id, body.content, body.client_message_id)
    return _turn_out(user, thread_id, turn)


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
    return _turn_out(user, thread_id, turn)


def _turn_out(user: Claims, thread_id: uuid.UUID, turn: orchestrator.Turn) -> TurnOut:
    # Not FastAPI's BackgroundTasks: both of these read or reference what this turn just
    # wrote, on a separate connection, and BackgroundTasks run before a UserConn
    # transaction commits - see mani/background.py for how that was confirmed.
    if turn.llm_call_id and turn.message_id:
        fire_and_forget(
            orchestrator.link_call(turn.llm_call_id, turn.message_id), name="link_call"
        )

    if turn.trace and turn.message_id and not turn.was_duplicate:
        # Why this turn went the way it did, stored once the message is committed (admin.turn_traces).
        fire_and_forget(orchestrator.record_trace(turn, thread_id), name="record_trace")

    if turn.needs_summary:
        fire_and_forget(update_quietly(user, thread_id), name="update_summary")

    if turn.read_after and not turn.was_duplicate:
        # What their message adds to Mani's picture of them, read once the reply is on its way.
        fire_and_forget(orchestrator.read_understanding(user, turn.read_after), name="read_understanding")

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
    )
