# ABOUTME: Thread endpoints - list, start, fetch, delete.
# ABOUTME: The thread id in the path is checked against the caller by RLS and by the query.

import datetime as dt
import uuid

from fastapi import APIRouter, Query

from mani.auth.deps import CurrentUser
from mani.chat import orchestrator
from mani.db import messages as messages_db, threads
from mani.db.deps import UserConn
from mani.errors import ErrorCategory, ServiceError
from mani.models.api import (
    MessageOut,
    StartOut,
    ThreadCreateIn,
    ThreadListOut,
    ThreadOut,
    ThreadUpdateIn,
)
from mani.routers.serializers import to_messages, to_thread

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


@router.post("", response_model=StartOut, status_code=201)
async def start(user: CurrentUser, conn: UserConn, body: ThreadCreateIn) -> StartOut:
    """Open a thread and write Mani's opening line.

    The greeting is written here rather than generated, so the first screen costs nothing
    and appears immediately.
    """
    thread, created = await orchestrator.start_thread(conn, user, body.title)
    return StartOut(
        thread=to_thread(thread),
        messages=await _history(conn, thread.id, user.user_id),
        is_new=created,
    )


@router.post("/current", response_model=StartOut)
async def current(user: CurrentUser, conn: UserConn) -> StartOut:
    """The conversation to show on opening the app, starting one if there is none.

    POST rather than GET because it writes: a first-time user gets a thread and a
    greeting. A GET is required to be safe, and caches and prefetchers treat it that way.
    """
    thread = await threads.most_recent(conn, user.user_id)
    created = False
    if thread is None:
        thread, created = await orchestrator.start_thread(conn, user)

    return StartOut(
        thread=to_thread(thread),
        messages=await _history(conn, thread.id, user.user_id),
        is_new=created,
    )


async def _history(conn, thread_id: uuid.UUID, user_id: str) -> list[MessageOut]:
    """A thread's tail, with buttons live only on Mani's newest message."""
    history = await messages_db.recent_for_context(conn, thread_id, user_id)
    live = await messages_db.latest_mani_id(conn, thread_id, user_id)
    return to_messages(history, live)


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
