# ABOUTME: The chat endpoints - read a thread's history, and send one turn.
# ABOUTME: Sending runs the orchestrator inside this request's single transaction.

import datetime as dt
import uuid

from fastapi import APIRouter, BackgroundTasks, Query

from mani.auth.deps import CurrentUser
from mani.chat import orchestrator
from mani.db import messages as messages_db
from mani.db.deps import UserConn
from mani.models.api import MessageListOut, SendMessageIn, TurnOut
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
    user: CurrentUser,
    conn: UserConn,
    thread_id: uuid.UUID,
    body: SendMessageIn,
    background: BackgroundTasks,
) -> TurnOut:
    """One user message in, one reply out.

    Exactly one provider call per turn: the checks that the previous implementation
    answered with a regeneration - up to six of them - are deterministic corrections in
    `chat/repairs.py`.
    """
    turn = await orchestrator.send(
        conn, user, thread_id, body.content, body.client_message_id
    )

    if turn.llm_call_id and turn.message_id:
        background.add_task(orchestrator.link_call, turn.llm_call_id, turn.message_id)

    if turn.needs_summary:
        # After the response, on its own connection. The reference started an un-awaited
        # coroutine inside the request, which the runtime was free to abandon.
        background.add_task(update_quietly, user, thread_id)

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
    )
