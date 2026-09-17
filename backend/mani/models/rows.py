# ABOUTME: Pydantic models for database rows, in the database's own snake_case.
# ABOUTME: The wire format lives in models/api.py; these never leave the backend.

from __future__ import annotations

import datetime as dt
import uuid
from enum import StrEnum
from typing import Any, Self

import asyncpg
from pydantic import BaseModel, ConfigDict, Field


class Row(BaseModel):
    """Base for anything read out of Postgres."""

    # Frozen because a row is a snapshot of what the database held when it was read.
    # The previous implementation mutated its in-memory thread object mid-turn and then
    # read the mutated copy back as if it were state, which is how phase tracking and
    # the cooldown counters drifted apart.
    model_config = ConfigDict(frozen=True, extra="ignore")

    @classmethod
    def from_record(cls, record: asyncpg.Record | None) -> Self | None:
        return cls.model_validate(dict(record)) if record is not None else None

    @classmethod
    def from_records(cls, records: list[asyncpg.Record]) -> list[Self]:
        return [cls.model_validate(dict(r)) for r in records]


class MessageRole(StrEnum):
    USER = "user"
    MANI = "mani"


class TechniqueOutcome(StrEnum):
    OFFERED = "offered"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class SupportStyle(StrEnum):
    SUPPORTIVE = "supportive"
    REFLECTIVE = "reflective"
    DIRECT = "direct"


class Profile(Row):
    user_id: uuid.UUID
    nickname: str | None = None
    topics: list[str] = Field(default_factory=list)
    support_style: SupportStyle | None = None
    age_bracket: str | None = None


class Thread(Row):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str | None = None
    message_count: int = 0
    crisis_detected: bool = False
    created_at: dt.datetime
    last_message_at: dt.datetime
    deleted_at: dt.datetime | None = None


class Message(Row):
    id: uuid.UUID
    thread_id: uuid.UUID
    user_id: uuid.UUID
    role: MessageRole
    # The clean text the person or Mani actually said. The hidden [ctx] metadata block
    # is built per turn and never stored, so history cannot replay stale context.
    content: str
    prompt_options: list[dict[str, Any]] | None = None
    selected_prompt: str | None = None
    client_message_id: uuid.UUID | None = None
    created_at: dt.datetime


class TechniqueState(Row):
    """The live technique on a thread. Absent means no technique in progress."""

    thread_id: uuid.UUID
    framework_id: str
    outcome: TechniqueOutcome
    phase: str | None = None
    at_message_count: int
    library_offered_since: bool = False


class ResponseStyle(Row):
    """One entry in the rolling window used to keep replies from repeating shape."""

    shape: str
    voice: str | None = None


class TechniqueTried(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    name: str
    helpful: bool
    context: str | None = None


class ThreadSummary(Row):
    thread_id: uuid.UUID
    user_id: uuid.UUID
    summary: str | None = None
    techniques_tried: list[TechniqueTried] = Field(default_factory=list)
    summarized_through_message_id: uuid.UUID | None = None
    summarized_message_count: int = 0


class Framework(Row):
    """A therapeutic technique, with its phase sequence as ordered data."""

    id: str
    name: str
    summary: str
    body: str
    activation_conditions: str = ""
    phases: list[str]
    display_order: int = 0
    # The router's input (central indication, weighted phrase lists, distinctions) and the
    # per-phase clinical content (purpose, listening cues, readiness, boundaries, the styled
    # `ask`). activation_conditions is left in place and simply stops being read for routing -
    # a flat string cannot hold either shape.
    activation: dict[str, Any] = Field(default_factory=dict)
    stages: dict[str, Any] = Field(default_factory=dict)

    def phase_index(self, phase: str | None) -> int:
        """Position in the sequence, or -1 for nothing started / unknown."""
        if phase is None:
            return -1
        try:
            return self.phases.index(phase)
        except ValueError:
            return -1

    def knows_phase(self, phase: str | None) -> bool:
        return phase in self.phases


class Prompt(Row):
    id: uuid.UUID
    name: str
    description: str = ""
    content: str
    version: int = 1
    model_id: str | None = None
    model_parameters: dict[str, Any] = Field(default_factory=dict)
    routing: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class Exercise(Row):
    id: uuid.UUID
    title: str
    subtitle: str | None = None
    description: str = ""
    type: str | None = None
    category: str
    audio_path: str
    duration_minutes: float | None = None
    display_order: int = 0
    show_on_home_screen: bool = False
