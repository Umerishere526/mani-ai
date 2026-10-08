# ABOUTME: The JSON shapes the model replies in, as names and types only.
# ABOUTME: What each field means lives in the seeded prompts, never in a description here.

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


# Where a library button navigates to. A closed set, checked before it is stored; the values a
# button may name are listed in response_format.md's `fields` section.
class LibrarySection(StrEnum):
    HOME = "home"
    EMOTIONAL_INTELLIGENCE = "EmotionalIntelligence"
    NARCISSISTIC_DYNAMICS = "NarcissisticDynamics"
    BUILDING_HABITS = "BuildingHabits"
    BOUNDARIES = "Boundaries"
    ANXIETY = "Anxiety"
    BURNOUT = "Burnout"


# One tappable capsule under a reply.
class SmartPrompt(BaseModel):
    model_config = ConfigDict(extra="ignore")

    label: str
    library: str | None = None
    technique: str | None = None
    decline: bool | None = None

    @field_validator("decline", mode="before")
    @classmethod
    def _decline_written_as_a_word(cls, value: object) -> object:
        """The model sometimes writes the word ("decline", "Keep chatting") where a boolean
        belongs, and one such reply failed the whole turn. A word there means the button
        declines; only an explicit no means it does not."""
        if isinstance(value, str):
            return value.strip().lower() not in {"", "false", "no", "0", "null", "none"}
        return value


class TechniqueState(BaseModel):
    model_config = ConfigDict(extra="ignore")

    technique: str
    step: str
    accepted: bool | None = None


class Crisis(BaseModel):
    model_config = ConfigDict(extra="ignore")

    reason: str


# The shape is a closed set named in the prompt (mani_base.md reply_shapes) rather than typed
# as an enum, and is checked in guards.py instead. A value outside an enum is a
# ValidationError, and a ValidationError here does not degrade one cosmetic field - it fails
# the whole reply, losing the message the person typed. Nothing the model reports about its
# own style is worth a lost turn, so the prompt asks and the guard decides.
class Style(BaseModel):
    model_config = ConfigDict(extra="ignore")

    shape: str


# What one turn asks the model for. Optional fields come back null, not absent. What each field
# means is said once, in response_format.md's `fields` section, so the schema sent carries names
# and types only.
class Reply(BaseModel):
    model_config = ConfigDict(extra="ignore")

    # reasoning and style come before text on purpose: structured output is generated in
    # schema order, so a field declared after text can only describe a reply already
    # written, never shape it.
    reasoning: str | None = None
    style: Style | None = None
    heading_toward: str | None = None
    text: str
    prompts: list[SmartPrompt] | None = None
    title: str | None = None
    crisis: Crisis | None = None
    state: TechniqueState | None = None
    # There is no clinical_note field. The model was asked for three or four sentences of
    # clinical formulation on every turn, for a care team that has nowhere to read it: it
    # reached no column, no log, and no screen. Paying output tokens for a formulation about
    # someone's mental state and then discarding it is the worst of both - the cost of
    # holding the reading and none of the use. If a care-team surface is ever built, this
    # comes back together with the column, the retention rule and the access policy that
    # make storing it defensible.


# What summarization asks for. Schema-validated rather than parsed out of prose; what each field
# means is said in summarization.md.
class Extraction(BaseModel):
    model_config = ConfigDict(extra="ignore")

    current_issue: str
    summary: str
    techniques_tried: list["ExtractedTechnique"] = Field(default_factory=list)


class ExtractedTechnique(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    helpful: bool
    context: str | None = None


# What the memory fold asks for: patterns across conversations, in the person's words.
#
# Each list holds short statements of what they said, never an interpretation of it. The
# fold replaces the whole memory each time, so an entry that no longer holds is dropped by
# leaving it out. What each list means is said in memory_fold.md.
class Memory(BaseModel):
    model_config = ConfigDict(extra="ignore")

    themes: list[str] = Field(default_factory=list)
    low_times: list[str] = Field(default_factory=list)
    better_times: list[str] = Field(default_factory=list)
    what_helps: list[str] = Field(default_factory=list)
    what_doesnt: list[str] = Field(default_factory=list)
    how_they_talk: list[str] = Field(default_factory=list)
