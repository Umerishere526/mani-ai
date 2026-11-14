# ABOUTME: Turns database rows into the wire shapes, in one place.
# ABOUTME: Row models stay internal; only what these return crosses the API boundary.

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from mani.chat import context
from mani.config import get_settings
from mani.db.exercises import Completion
from mani.llm.schema import SmartPrompt
from mani.models.api import (
    CompletionOut,
    ExerciseOut,
    MessageOut,
    ProfileOut,
    PromptOut,
    PromptVersionOut,
    ThreadOut,
    TurnOut,
)
from mani.models.rows import (
    Exercise,
    Message,
    MessageRole,
    Pause,
    Profile,
    Prompt,
    Thread,
)

if TYPE_CHECKING:
    from mani.chat.orchestrator import Turn


def to_thread(thread: Thread) -> ThreadOut:
    return ThreadOut(
        id=thread.id,
        title=thread.title,
        message_count=thread.message_count,
        crisis_detected=thread.crisis_detected,
        created_at=thread.created_at,
        last_message_at=thread.last_message_at,
        conversation_style=thread.conversation_style,
    )


def to_message(message: Message, *, prompts_live: bool = False) -> MessageOut:
    """One message as a client sees it.

    Buttons are only offered on Mani's newest message, so every other message returns
    none. They are presentation, not history: the implementation this replaces kept them
    on old rows and deleted them afterwards with an UPDATE, which left tappable offers
    behind whenever that write failed. `selected_prompt` does persist everywhere - what
    somebody chose is part of the conversation, what they were offered is not.
    """
    return MessageOut(
        id=message.id,
        thread_id=message.thread_id,
        role=message.role,
        # Nothing written by this backend carries a [ctx] block, but messages written by
        # the system it replaces do, and those must not be shown to anyone.
        content=(
            context.strip(message.content)
            if message.role is MessageRole.USER
            else message.content
        ),
        prompts=(
            [SmartPrompt.model_validate(p) for p in (message.prompt_options or [])]
            if prompts_live
            else []
        ),
        selected_prompt=message.selected_prompt,
        created_at=message.created_at,
    )


def to_messages(
    messages: list[Message], live_prompt_id: uuid.UUID | None
) -> list[MessageOut]:
    return [to_message(m, prompts_live=m.id == live_prompt_id) for m in messages]


def to_turn(turn: Turn) -> TurnOut:
    debug = get_settings().ai_debug_mode
    return TurnOut(
        id=turn.message_id,
        content=turn.content,
        created_at=turn.created_at,
        prompts=turn.prompts,
        title=turn.title,
        crisis_detected=turn.crisis_detected,
        paused_from=turn.paused_from,
        paused_until=turn.paused_until,
        was_duplicate=turn.was_duplicate,
        reasoning=turn.reasoning,
        ledger=turn.ledger,
        understanding=turn.understanding if debug else None,
        check_at_message_count=turn.check_at_message_count if debug else None,
        trace=turn.trace if debug else None,
        follow_up_pending=bool(turn.read_after or turn.needs_summary) and not turn.was_duplicate,
    )


def to_profile(profile: Profile | None, pause: Pause | None = None) -> ProfileOut:
    paused = {
        "chat_paused_from": pause.started_at if pause else None,
        "chat_paused_until": pause.ends_at if pause else None,
    }
    if profile is None:
        return ProfileOut(**paused)
    return ProfileOut(
        **paused,
        nickname=profile.nickname,
        topics=profile.topics,
        support_style=profile.support_style,
        age_bracket=profile.age_bracket,
    )


def to_exercise(exercise: Exercise, audio_url: str | None) -> ExerciseOut:
    return ExerciseOut(**exercise.model_dump(exclude={"audio_path"}), audio_url=audio_url)


def to_completion(completion: Completion) -> CompletionOut:
    return CompletionOut(
        id=completion.id,
        exercise_id=completion.exercise_id,
        helpful=completion.helpful,
        completed_at=completion.completed_at,
    )


def to_prompt(prompt: Prompt) -> PromptOut:
    return PromptOut(**prompt.model_dump())


def to_prompt_version(record) -> PromptVersionOut:
    return PromptVersionOut(**dict(record))
