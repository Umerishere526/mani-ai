# ABOUTME: The structured shapes beside the turn's own reply (chat/reply.py): the buttons under a reply, and what the
# ABOUTME: summary asks the model for. Field descriptions are read by the model.

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class LibrarySection(StrEnum):
    """The library's sections, as the client lists them (2026-11-16): the category every exercise sits in, and where a
    library button can open. A closed set, so a typo never becomes a section of its own."""

    ANXIETY = "Anxiety"
    BOUNDARIES = "Boundaries"
    BUILDING_HABITS = "BuildingHabits"
    EMOTIONAL_INTELLIGENCE = "EmotionalIntelligence"
    LOVE_RELATIONSHIPS = "LoveRelationships"
    MANAGING_WORRY = "ManagingWorry"
    SLEEP = "Sleep"
    BURNOUT = "Burnout"
    STRESS = "Stress"
    WORKPLACE_CHALLENGES = "WorkplaceChallenges"


# The library's front page, where a library button goes when no section fits. Not a section: no exercise sits in it.
LIBRARY_HOME = "home"


def _listed(values) -> str:
    return ", ".join(f'"{v}"' for v in values)


# CLOSED SETS: a closed set the model reports is named in the field's description rather than typed as an enum, and
# checked by code instead. A value outside an enum is a ValidationError, and a ValidationError here does not degrade
# one field - it costs a second provider call and then raises, losing the message the person typed. So the schema
# asks and code decides.


class Button(BaseModel):
    """What every tappable capsule carries."""

    model_config = ConfigDict(extra="ignore")

    label: str = Field(description="Display text shown to the user.")
    library: str | None = Field(
        default=None,
        description=(
            "Set only when this button navigates to the library. Null otherwise. "
            f"One of: {_listed([LIBRARY_HOME, *LibrarySection])}. \"home\" is the library's front page: "
            "use it for a general Visit library button."
        ),
    )
    decline: bool | None = Field(
        default=None,
        description="True when tapping this button declines the technique being offered.",
    )


class SmartPrompt(Button):
    """One tappable capsule under a reply."""

    technique: str | None = Field(
        default=None,
        description=(
            "The technique id this button offers, when the button is a technique offer. "
            "Null otherwise."
        ),
    )


class Extraction(BaseModel):
    """What summarization asks for. Schema-validated rather than parsed out of prose."""

    model_config = ConfigDict(extra="ignore")

    summary: str = Field(
        description=(
            "A 2-4 sentence prose summary of what was discussed: the main concern, key "
            'moments, and any progress or realisations. Third person ("User is dealing '
            'with...").'
        )
    )
    techniques_tried: list["ExtractedTechnique"] = Field(
        default_factory=list,
        description="Coping techniques or exercises discussed or practised. May be empty.",
    )


class ExtractedTechnique(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(description='The technique name, e.g. "deep breathing", "abcde".')
    helpful: bool = Field(description="Whether it seemed to help.")
    context: str | None = Field(
        default=None, description="Brief note on when or how it was used. May be null."
    )
