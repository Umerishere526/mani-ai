# ABOUTME: Answers a request with the turn it ran: ties the turn to its model call and its trace, then maps it to the wire.
# ABOUTME: Shared by every route that runs a turn, so none of them repeats the two writes.

import asyncio
import uuid

from mani.chat import orchestrator
from mani.models.api import TurnOut
from mani.routers.serializers import to_turn


async def respond(thread_id: uuid.UUID, turn: orchestrator.Turn) -> TurnOut:
    """A turn as a client sees it, after the two writes that tie it to its reply.

    Awaited, not left running after the response: Vercel stops the instance once a response is sent, so work
    started after it was being lost (2026-11-05). Both are database writes only, side by side, and the turn
    is committed by now (chat/runner.py), so the message they reference is there; each swallows its own failure.
    """
    linking = []
    if turn.llm_call_id and turn.message_id:
        linking.append(orchestrator.link_call(turn.llm_call_id, turn.message_id))
    if turn.trace and turn.message_id and not turn.was_duplicate:
        # Why this turn went the way it did (admin.turn_traces).
        linking.append(orchestrator.record_trace(turn, thread_id))
    await asyncio.gather(*linking)
    return to_turn(turn)
