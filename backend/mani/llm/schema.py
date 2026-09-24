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


def _listed(values) -> str:
    return ", ".join(f'"{v}"' for v in values)


# The closed sets below are named in the descriptions rather than typed as enums, and are
# checked in repairs.py instead. A value outside an enum is a ValidationError, and a
# ValidationError here does not degrade one cosmetic field - it costs a second provider call
# and then raises, losing the message the person typed. Nothing the model reports about its
# own style is worth a lost turn, so the schema asks and the repair decides.
SHAPES = (
    "warmth lead", "honor and follow", "mirror and ask", "mirror and hold",
    "gentle follow", "presence only",
)
VOICES = ("naming", "receiving", "quoting", "transitional", "observing")


class SmartPrompt(BaseModel):
    """One tappable capsule under a reply."""

    model_config = ConfigDict(extra="ignore")

    label: str = Field(description="Display text shown to the user.")
    library: str | None = Field(
        default=None,
        description=(
            "Set only when this button navigates to the library. Null otherwise. "
            f"One of: {_listed(LibrarySection)}. \"home\" is the library's front page: "
            "use it for a general Go to Library button."
        ),
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
            "The current stage id you are executing, from framework_stages in [ctx]. "
            "Stages must follow that list's order - you cannot skip one."
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
        description=f"The response shape you used: {_listed(SHAPES)}."
    )
    voice: str | None = Field(
        default=None,
        description=(
            f"The mirroring voice you used, if you mirrored: {_listed(VOICES)}. "
            "Null if no mirroring."
        ),
    )


class Reply(BaseModel):
    """What one turn asks the model for. Optional fields come back null, not absent."""

    model_config = ConfigDict(extra="ignore")

    # reasoning and style come before text on purpose: structured output is generated in
    # schema order, so a field declared after text can only describe a reply already
    # written, never shape it.
    reasoning: str | None = Field(
        default=None,
        description=(
            "Fill this first, before text. Work through the steps under 'The reasoning "
            "field' in your instructions. Not shown to the user."
        ),
    )
    style: Style | None = Field(
        default=None,
        description=(
            "Choose before writing text: the response shape and mirroring voice this reply "
            "will use. The shape may repeat; the voice must differ from the last entry in "
            "recent_styles in [ctx]."
        ),
    )
    text: str = Field(description="Your conversational response to the user. Required.")
    prompts: list[SmartPrompt] | None = Field(
        default=None,
        description=(
            "Tappable button options if your response ends with a question that has "
            "2-3 clear choices. Each prompt has a \"label\" field (required). "
            "ONLY include \"technique\" field when INITIALLY ASKING if user wants to try "
            "a technique. Include \"library\" ONLY on a button that opens the library. "
            "Labels should be in USER voice (\"Yes, let's try it\", "
            "\"Not right now\"). Set to null if no buttons are appropriate "
            "(e.g., open-ended questions). Two or three, never more."
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
            "this field with the technique id and the stage you are on. This includes "
            "offering a technique and every stage through the last one in framework_stages. "
            "Only set to null when the conversation has no active technique."
        ),
    )
    # There is no clinical_note field. The model was asked for three or four sentences of
    # clinical formulation on every turn, for a care team that has nowhere to read it: it
    # reached no column, no log, and no screen. Paying output tokens for a formulation about
    # someone's mental state and then discarding it is the worst of both - the cost of
    # holding the reading and none of the use. If a care-team surface is ever built, this
    # comes back together with the column, the retention rule and the access policy that
    # make storing it defensible.


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


class Memory(BaseModel):
    """What the memory fold asks for: patterns across conversations, in the person's words.

    Each list holds short statements of what they said, never an interpretation of it. The
    fold replaces the whole memory each time, so an entry that no longer holds is dropped by
    leaving it out.
    """

    model_config = ConfigDict(extra="ignore")

    themes: list[str] = Field(
        default_factory=list,
        description="What they keep coming back to, in their words. Short phrases.",
    )
    low_times: list[str] = Field(
        default_factory=list,
        description=(
            "When they feel low, and the reason they gave, e.g. \"feels low most Sunday "
            "evenings, because of work on Monday\". Only what they said; no diagnosis."
        ),
    )
    better_times: list[str] = Field(
        default_factory=list,
        description="When they feel better, and what was going on, as they described it.",
    )
    what_helps: list[str] = Field(
        default_factory=list,
        description="Ways of coping they described as helping, including any framework.",
    )
    what_doesnt: list[str] = Field(
        default_factory=list,
        description="What they said did not help, or asked not to do.",
    )
    how_they_talk: list[str] = Field(
        default_factory=list,
        description=(
            "How they like the conversation to go, from how they responded: e.g. \"prefers "
            "short replies\", \"usually declines exercises\"."
        ),
    )
