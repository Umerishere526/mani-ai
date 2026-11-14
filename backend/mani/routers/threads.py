# ABOUTME: Thread endpoints - the read-only opening, start from a first message, list, current, fetch, delete.
# ABOUTME: The thread id in the path is checked against the caller by RLS and by the query.

import datetime as dt
import uuid

from fastapi import APIRouter, Query

from mani import memory
from mani.auth.deps import ChatOpen, CurrentUser
from mani.chat import greeting, orchestrator, runner
from mani.db import messages as messages_db, pauses, threads
from mani.db.deps import UserConn
from mani.errors import ErrorCategory, ServiceError
from mani.models.api import (
    CurrentOut,
    MemoryFoldOut,
    MessageOut,
    OpeningOut,
    ThreadListOut,
    ThreadOut,
    ThreadStartedOut,
    ThreadStartIn,
    ThreadUpdateIn,
)
from mani.routers.serializers import to_messages, to_thread
from mani.routers.turns import respond

router = APIRouter(prefix="/v1/threads", tags=["threads"])


@router.get("", response_model=ThreadListOut)
async def list_threads(
    user: CurrentUser,
    conn: UserConn,
    limit: int = Query(default=threads.DEFAULT_PAGE, ge=1, le=100),
    # A timestamp, not a string. Typed loosely it reached Postgres as a cast and a
    # malformed value became a 500 instead of a refused request.
    cursor: dt.datetime | None = None,
) -> ThreadListOut:
    page = await threads.list_for_user(conn, user.user_id, limit, cursor)
    return ThreadListOut(
        threads=[to_thread(t) for t in page.threads], next_cursor=page.next_cursor
    )


@router.get("/opening", response_model=OpeningOut)
async def opening(user: CurrentUser, conn: UserConn) -> OpeningOut:
    """What a new conversation opens with, for a client to show before the person has written anything. Writes
    nothing: the conversation is created by their first message (`start`)."""
    pause = await pauses.active(conn, user.user_id)
    return OpeningOut(
        chat_paused_from=pause.started_at if pause else None,
        chat_paused_until=pause.ends_at if pause else None,
        greeting=await orchestrator.opening_greeting(conn, user.user_id),
        style_options=greeting.STYLE_OPTIONS,
        openers=greeting.OPENERS,
    )


@router.post("", response_model=ThreadStartedOut, status_code=201)
async def start(user: ChatOpen, body: ThreadStartIn) -> ThreadStartedOut:
    """The person's first message creates the conversation: Mani's greeting, the style they chose, then their message
    as a turn. Mani's opening line is written here rather than generated, so it costs nothing."""
    thread, turn = await runner.start(user, body.content, body.client_message_id, body.style)
    return ThreadStartedOut(thread=to_thread(thread), turn=await respond(thread.id, turn))


@router.post("/memory-fold", response_model=MemoryFoldOut)
async def fold_memory(user: CurrentUser) -> MemoryFoldOut:
    """Fold the person's finished conversations into what Mani remembers of them. Asked for by the app when they open
    a new conversation, not left running after that response: Vercel stops the instance once a response is sent, and
    folds started that way never wrote a row (2026-11-05). Only conversations last written before this request
    arrived are folded, so the one their first message starts while it runs is left alone. Folds only what waits, so a
    repeated request costs nothing; a failure is logged and costs only that memory."""
    return MemoryFoldOut(folded=await memory.fold_finished(user, idle_before=dt.datetime.now(dt.UTC)))


@router.get("/current", response_model=CurrentOut)
async def current(user: CurrentUser, conn: UserConn) -> CurrentOut:
    """The conversation to show on opening the app: the one they last wrote in, or none, when the app shows the
    opening instead. Writes nothing."""
    thread = await threads.most_recent(conn, user.user_id)
    if thread is None:
        return CurrentOut()
    return CurrentOut(thread=to_thread(thread), messages=await _history(conn, thread.id, user.user_id))


# How many of a thread's newest messages the app is sent on opening it; older ones page in from
# the messages route. The app's own number, apart from how much of the thread the model sees.
OPENING_TAIL = 20


async def _history(conn, thread_id: uuid.UUID, user_id: str) -> list[MessageOut]:
    """A thread's tail, oldest first, with buttons live only on Mani's newest message."""
    page = await messages_db.list_for_thread(conn, thread_id, user_id, limit=OPENING_TAIL)
    live = await messages_db.latest_mani_id(conn, thread_id, user_id)
    return to_messages(list(reversed(page.messages)), live)


@router.get("/{thread_id}", response_model=ThreadOut)
async def get_thread(user: CurrentUser, conn: UserConn, thread_id: uuid.UUID) -> ThreadOut:
    thread = await threads.get(conn, thread_id, user.user_id)
    if thread is None:
        raise ServiceError(
            f"thread {thread_id} not found for user {user.user_id}",
            ErrorCategory.NOT_FOUND,
            user_message="That conversation is not available.",
        )
    return to_thread(thread)


@router.patch("/{thread_id}", response_model=ThreadOut)
async def update_thread(
    user: CurrentUser, conn: UserConn, thread_id: uuid.UUID, body: ThreadUpdateIn
) -> ThreadOut:
    """Change how Mani speaks in this conversation.

    The style is a label from a closed set, not a privilege: the caller names which of
    the three tones they want, never who they are. Ownership is enforced by RLS and by
    the predicate on the write, as everywhere else.
    """
    if body.conversation_style is not None:
        await threads.apply(
            conn, thread_id, user.user_id,
            threads.ThreadUpdates(conversation_style=body.conversation_style),
        )

    thread = await threads.get(conn, thread_id, user.user_id)
    if thread is None:
        raise ServiceError(
            f"thread {thread_id} not found for user {user.user_id}",
            ErrorCategory.NOT_FOUND,
            user_message="That conversation is not available.",
        )
    return to_thread(thread)


@router.delete("/{thread_id}", status_code=204)
async def delete_thread(user: CurrentUser, conn: UserConn, thread_id: uuid.UUID) -> None:
    """Hide a conversation. Erasure is a separate retention mechanism."""
    if not await threads.soft_delete(conn, thread_id, user.user_id):
        raise ServiceError(
            f"thread {thread_id} not found for user {user.user_id}",
            ErrorCategory.NOT_FOUND,
            user_message="That conversation is not available.",
        )
