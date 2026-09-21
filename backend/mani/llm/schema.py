# ABOUTME: The JSON shape Mani must reply in, and the field descriptions sent with it.
# ABOUTME: Every description is prompt surface - the model reads them, so wording matters.

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class LibrarySection(StrEnum):
    """Where a library button navigates to. A closed set, checked before it is stored."""

    HOME = "home"
    EMOTIONAL_INTELLIGENCE = "EmotionalIntelligence"
    NARCISSISTIC_DYNAMICS = "NarcissisticDynamics"
    BUILDING_HABITS = "BuildingHabits"
    BOUNDARIES = "Boundaries"
    ANXIETY = "Anxiety"
    BURNOUT = "Burnout"


class SmartPrompt(BaseModel):
    """One tappable capsule under a reply."""

    model_config = ConfigDict(extra="ignore")

    label: str = Field(description="Display text shown to the user.")
    library: LibrarySection | None = Field(
        default=None,
        description="Set only when this button navigates to the library. Null otherwise.",
    )
    technique: str | None = Field(
        default=None,
        description=(
            "The technique id this button offers, when the button is a technique offer. "
            "Null otherwise."
        ),
    )
    decline: bool | None = Field(
        default=None,
        description="True when tapping this button declines the technique being offered.",
    )


class TechniqueState(BaseModel):
    model_config = ConfigDict(extra="ignore")

    technique: str = Field(
        description="The framework id, exactly as listed in the Framework Index."
    )
    step: str = Field(
        description=(
            "The current stage id you are executing, from that framework's stage list in "
            "active_framework. Stages must follow that list's order - you cannot skip one."
        )
    )
    accepted: bool | None = Field(
        default=None,
        description=(
            "Set to true when the user accepts a technique offer in free text "
            '(e.g., "yeah let\'s do it", "sure", "ok"). Set to false when they decline it '
            "in free text. Only relevant during the offering phase. "
            "Set to null when the user did neither, so the offer stays open."
        ),
    )


class Crisis(BaseModel):
    model_config = ConfigDict(extra="ignore")

    reason: str = Field(description="Brief description of the crisis signal")


class Style(BaseModel):
    model_config = ConfigDict(extra="ignore")

    shape: str = Field(
        description=(
            'The response shape you used: "warmth lead", "honor and follow", '
            '"mirror and ask", "mirror and hold", "gentle follow", or "presence only".'
        )
    )
    voice: str | None = Field(
        default=None,
        description=(
            'The mirroring voice you used, if you mirrored: "naming", "receiving", '
            '"quoting", "transitional", or "observing". Null if no mirroring.'
        ),
    )


class Reply(BaseModel):
    """What one turn asks the model for. Optional fields come back null, not absent."""

    model_config = ConfigDict(extra="ignore")

    text: str = Field(description="Your conversational response to the user. Required.")
    prompts: list[SmartPrompt] | None = Field(
        default=None,
        description=(
            "Tappable button options if your response ends with a question that has "
            "2-3 clear choices. Each prompt has a \"label\" field (required). "
            "ONLY include \"technique\" field when INITIALLY ASKING if user wants to try "
            "a technique. Include \"library\" field with value \"home\" ONLY when offering "
            "library navigation. Labels should be in USER voice (\"Yes, let's try it\", "
            "\"Not right now\"). Set to null if no buttons are appropriate "
            "(e.g., open-ended questions). At most three."
        ),
    )
    title: str | None = Field(
        default=None,
        description=(
            "Short title for this conversation (3-6 words). "
            "Provide when system prompt requests a title. "
            "Set to null if no title instruction was given."
        ),
    )
    crisis: Crisis | None = Field(
        default=None,
        description=(
            "Set ONLY when user expresses suicidal ideation, self-harm intent, or deep "
            'hopelessness. Examples: "I want to end it", "no point in living", '
            '"better off without me". Do NOT set for normal sadness or frustration. '
            "Set to null if no crisis detected."
        ),
    )
    state: TechniqueState | None = Field(
        default=None,
        description=(
            "REQUIRED when you are offering or guiding a technique - you MUST populate "
            "this field with the technique name and current step. This includes: offering "
            "a technique, walking through any phase, or completing the ground phase. "
            "Only set to null when the conversation has no active technique."
        ),
    )
    reasoning: str | None = Field(
        default=None,
        description=(
            "Required. Your internal reasoning before generating text. Follow the "
            "Reasoning Field instructions: (1) state your identity and tone goal, "
            "(2) state your response pattern, (3) diction check - list your previous "
            "opening words and choose a structurally different one, (4) mirror check - "
            "list the user's exact words you will reflect. Not shown to user."
        ),
    )
    style: Style | None = Field(
        default=None,
        description=(
            "Declare the response shape and mirroring voice you used in this response. "
            "Check the recent_styles in [ctx] to avoid repeating the same shape or voice."
        ),
    )
    clinical_note: str | None = Field(
        default=None,
        description=(
            "Required. Your clinical read of this turn, written for the care team and "
            "never shown to the user. This is the one place you may name things "
            "directly: what appears to be going on beneath what they said, the pattern "
            "you think you are seeing, what they have not said that matters, any risk "
            "signal short of crisis, whether the active framework and style still fit, "
            "and what to watch for next turn. Write it as a clinician would to a "
            "colleague - specific, hedged where you are uncertain, and honest when you "
            "do not have enough to go on. Three or four sentences. It must not change "
            "what you said to the person: the no-labelling rules govern the reply, this "
            "field is where the reading belongs instead."
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
