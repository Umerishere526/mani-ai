# ABOUTME: The chat endpoints - read a thread's history, and send one turn.
# ABOUTME: Sending runs the orchestrator inside this request's single transaction.

import datetime as dt
import uuid

from fastapi import APIRouter, Query

from mani.auth.deps import CurrentUser
from mani.background import fire_and_forget
from mani.chat import orchestrator
from mani.db import messages as messages_db
from mani.db.deps import UserConn
from mani.models.api import MessageListOut, SendMessageIn, TurnOut
from mani.routers.serializers import to_exercise, to_messages
from mani.storage import signed_audio_url
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
) -> TurnOut:
    """One user message in, one reply out.

    Exactly one provider call per turn: the checks that the previous implementation
    answered with a regeneration - up to six of them - are deterministic corrections in
    `chat/repairs.py`.
    """
    turn = await orchestrator.send(
        conn, user, thread_id, body.content, body.client_message_id
    )

    # Not FastAPI's BackgroundTasks: both of these read or reference what this turn just
    # wrote, on a separate connection, and BackgroundTasks run before UserConn's
    # transaction commits - see mani/background.py for how that was confirmed.
    if turn.llm_call_id and turn.message_id:
        fire_and_forget(
            orchestrator.link_call(turn.llm_call_id, turn.message_id), name="link_call"
        )

    if turn.needs_summary:
        fire_and_forget(update_quietly(user, thread_id), name="update_summary")

    # The exercise a completed framework hands off to, signed here rather than in the
    # orchestrator - the audio link is a wire concern, and the row model carries a path.
    exercise = (
        to_exercise(turn.exercise, await signed_audio_url(turn.exercise.audio_path))
        if turn.exercise
        else None
    )

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
        exercise=exercise,
    )
