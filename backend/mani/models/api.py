# ABOUTME: Request and response bodies - the contract web/ and mobile/ generate types from.
# ABOUTME: Nothing here carries a user id: identity comes from the token, never the body.

from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, ConfigDict, Field

from mani.llm.schema import SmartPrompt
from mani.models.rows import Exercise, MessageRole, SupportStyle


class ThreadOut(BaseModel):
    id: uuid.UUID
    title: str | None = None
    message_count: int = 0
    crisis_detected: bool = False
    crisis_blocks_chat: bool = True
    created_at: dt.datetime
    last_message_at: dt.datetime


class ThreadListOut(BaseModel):
    threads: list[ThreadOut]
    next_cursor: str | None = None


class ThreadCreateIn(BaseModel):
    title: str | None = Field(default=None, max_length=200)


class MessageOut(BaseModel):
    id: uuid.UUID
    thread_id: uuid.UUID
    role: MessageRole
    content: str
    prompts: list[SmartPrompt] = Field(default_factory=list)
    selected_prompt: str | None = None
    created_at: dt.datetime


class MessageListOut(BaseModel):
    messages: list[MessageOut]
    next_cursor: str | None = None


class SendMessageIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=4000)
    # Supplied by the client so a retried send returns the original reply instead of
    # paying for a second one. It identifies the request, not the person.
    client_message_id: uuid.UUID | None = None


class TurnOut(BaseModel):
    id: uuid.UUID | None = None
    content: str
    created_at: dt.datetime | None = None
    prompts: list[SmartPrompt] = Field(default_factory=list)
    title: str | None = None
    crisis_detected: bool = False
    crisis_blocks_chat: bool = True
    was_duplicate: bool = False
    reasoning: str | None = None


class StartOut(BaseModel):
    """A thread and its opening line, for the chat screen's first load."""

    thread: ThreadOut
    messages: list[MessageOut]
    is_new: bool


class ProfileIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nickname: str | None = Field(default=None, max_length=40)
    topics: list[str] | None = None
    support_style: SupportStyle | None = None
    age_bracket: str | None = None


class ProfileOut(BaseModel):
    nickname: str | None = None
    topics: list[str] = Field(default_factory=list)
    support_style: SupportStyle | None = None
    age_bracket: str | None = None


class ExerciseOut(Exercise):
    """The catalog entry as a client sees it: a signed link, not a storage path."""

    audio_url: str | None = None


class CompletionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exercise_id: uuid.UUID
    helpful: bool | None = None


class CompletionOut(BaseModel):
    id: uuid.UUID
    exercise_id: uuid.UUID
    helpful: bool | None = None
    completed_at: dt.datetime


class PromptOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str = ""
    content: str
    version: int
    model_id: str | None = None
    model_parameters: dict = Field(default_factory=dict)
    routing: dict = Field(default_factory=dict)
    is_active: bool = True


class PromptIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=100)
    description: str | None = None
    content: str | None = None
    model_id: str | None = None
    model_parameters: dict | None = None
    routing: dict | None = None
    is_active: bool | None = None
    change_summary: str | None = Field(default=None, max_length=500)


class PromptVersionOut(BaseModel):
    id: uuid.UUID
    prompt_id: uuid.UUID
    version: int
    content: str
    model_id: str | None = None
    model_parameters: dict = Field(default_factory=dict)
    routing: dict = Field(default_factory=dict)
    change_summary: str | None = None
    created_at: dt.datetime
