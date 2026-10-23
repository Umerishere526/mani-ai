# ABOUTME: The chat endpoints - read a thread's history, send one turn, stream one turn.
# ABOUTME: Sending runs the orchestrator inside this request's single transaction.

import asyncio
import datetime as dt
import json
import logging
import uuid

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from mani.auth.deps import CurrentUser
from mani.background import fire_and_forget
from mani.chat import orchestrator
from mani.db import messages as messages_db
from mani.db.deps import UserConn
from mani.errors import ErrorCategory, ServiceError
from mani.models.api import MessageListOut, SendMessageIn, TurnOut
from mani.routers.serializers import to_exercise, to_messages
from mani.storage import signed_audio_url
from mani.summarize import update_quietly

logger = logging.getLogger(__name__)

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
    _after_turn(user, thread_id, turn)
    return await _to_turn_out(turn)


class _TurnSink:
    """The turn's stream callbacks, translated into queued SSE frames."""

    def __init__(self, queue: "asyncio.Queue[tuple[str, dict] | None]") -> None:
        self._queue = queue
        self._sent = ""

    @property
    def sent(self) -> str:
        return self._sent

    async def delta(self, text: str) -> None:
        self._sent += text
        await self._queue.put(("delta", {"text": text}))

    async def reset(self) -> None:
        self._sent = ""
        await self._queue.put(("reset", {}))

    async def replace(self, text: str) -> None:
        self._sent = text
        await self._queue.put(("replace", {"text": text}))


@router.post("/stream")
async def send_stream(
    user: CurrentUser,
    conn: UserConn,
    thread_id: uuid.UUID,
    body: SendMessageIn,
) -> StreamingResponse:
    """One user message in, the reply streamed out as server-sent events.

    The turn is the same one the plain endpoint runs, inside this request's single
    transaction: `delta` frames carry the draft as the model writes it, `done` carries
    exactly what the plain endpoint returns. The transaction commits when the stream
    finishes cleanly - UserConn's exit code runs after the response is sent.
    """
    queue: asyncio.Queue[tuple[str, dict] | None] = asyncio.Queue()
    failure: BaseException | None = None

    async def run() -> None:
        nonlocal failure
        try:
            turn = await orchestrator.send(
                conn, user, thread_id, body.content, body.client_message_id,
                stream=_TurnSink(queue),
            )
            _after_turn(user, thread_id, turn)
            await queue.put(("done", (await _to_turn_out(turn)).model_dump(mode="json")))
        except ServiceError as exc:
            await queue.put(
                ("error", {"category": exc.category.value, "message": exc.user_message})
            )
        except Exception as exc:
            logger.exception("streamed turn on thread %s failed", thread_id)
            await queue.put((
                "error",
                {
                    "category": ErrorCategory.UNKNOWN.value,
                    "message": "Mani had trouble responding. Please try again.",
                },
            ))
            failure = exc
        finally:
            await queue.put(None)

    # Kept in a closure variable so the event loop cannot collect it mid-turn.
    task = asyncio.create_task(run())

    async def frames():
        while (item := await queue.get()) is not None:
            event, data = item
            yield f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"
        if failure is not None:
            # The client already holds the error frame; raising here is what rolls the
            # transaction back instead of committing a turn that failed mid-write.
            raise failure
        await task

    return StreamingResponse(frames(), media_type="text/event-stream")


def _after_turn(user: CurrentUser, thread_id: uuid.UUID, turn: orchestrator.Turn) -> None:
    """The follow-ups both send paths run: link the cost row, refresh a due summary.

    Not FastAPI's BackgroundTasks: both of these read or reference what this turn just
    wrote, on a separate connection, and BackgroundTasks run before UserConn's
    transaction commits - see mani/background.py for how that was confirmed.
    """
    if turn.llm_call_id and turn.message_id:
        fire_and_forget(
            orchestrator.link_call(turn.llm_call_id, turn.message_id), name="link_call"
        )

    if turn.needs_summary:
        fire_and_forget(update_quietly(user, thread_id), name="update_summary")


async def _to_turn_out(turn: orchestrator.Turn) -> TurnOut:
    """The reply as the wire carries it, identical on the plain and streaming endpoints."""
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
