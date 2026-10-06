# ABOUTME: The JSON shape Mani must reply in, and the field descriptions sent with it.
# ABOUTME: Every description is prompt surface - the model reads them, so wording matters.

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


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

    technique: str = Field(
        description="The framework id, exactly as listed in the Framework Index."
    )
    step: str = Field(
        description=(
            "The step you ask in this reply, from the steps in [ctx]: the next one their words do "
            "not already meet, or the same step for your one more attempt at it. Never an earlier one."
        )
    )
    accepted: bool | None = Field(
        default=None,
        description=(
            "Set to true when the user accepts a technique offer in free text "
            '(e.g., "yeah let\'s do it", "sure", "ok"), or asks for one they declined '
            "earlier in this conversation. Set to false when they decline an offer in free "
            "text, or carry on talking without answering it: that is Keep chatting. Set to "
            "null when they asked about the offer itself, so it stays open, and on every "
            "other turn."
        ),
    )


class Crisis(BaseModel):
    model_config = ConfigDict(extra="ignore")

    reason: str = Field(
        default="",
        description="Brief description of the crisis signal. Never read back to anyone.",
    )
    category: str | None = Field(
        default=None,
        description=(
            "What kind of concern, one of: suicide, self_harm, harm_to_other, cannot_stay_safe, "
            "abuse_or_violence, overdose, medical_emergency, loss_of_contact_with_reality, other. "
            "Use other only for something you thought about that is not danger."
        ),
    )

    @field_validator("reason", mode="before")
    @classmethod
    def _no_reason_is_empty(cls, value: object) -> object:
        """A flag with a null reason is still a flag; reading it as empty keeps the reply."""
        return "" if value is None else value

    @field_validator("category", mode="before")
    @classmethod
    def _only_text_names_a_kind(cls, value: object) -> object:
        """A number or a list there is no kind. Reading it as none keeps the reply, and a flag
        with no kind is treated as a real concern."""
        return value if isinstance(value, str) else None


class Style(BaseModel):
    model_config = ConfigDict(extra="ignore")

    shape: str = Field(
        description=f"The response shape you used: {_listed(SHAPES)}."
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
            "Choose before writing text: the response shape this reply will use. It may "
            "repeat; the opening words may not."
        ),
    )
    text: str = Field(description="Your conversational response to the user. Required.")
    # Plain strings for the same reason as the closed sets above: repairs reads them, and an
    # unknown value is dropped rather than costing the turn.
    ending: str | None = Field(
        default=None,
        description=(
            "Only on the reply that ends a running framework, moving to the body check in: "
            "\"resolved\" when it has what it needs, \"pivoted\" when it stopped helping or a step "
            "could not be answered after one more attempt, \"stopped\" when they asked to stop. "
            "Null otherwise."
        ),
    )
    felt_after: str | None = Field(
        default=None,
        description=(
            "Only with answering_practice in [ctx]: how they say they feel after the practice, one "
            "of \"better\", \"mixed\", \"unchanged\", \"worse\", \"unsure\". Null when they did "
            "not say, and on every other turn."
        ),
    )

    prompts: list[SmartPrompt] | None = Field(
        default=None,
        description=(
            "Buttons under the reply. When you offer a set of questions, give one button with "
            "\"technique\" set to its id: the labels of an offer are set for you. Include "
            "\"library\" ONLY on a button that opens the library. Otherwise buttons only where "
            "a stage gives them; set to null when none are given."
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
            "Set when something in their message made you stop and think about whether they, or "
            "someone else, may be in danger: suicidal thoughts, an intent to self-harm, a wish to "
            "die, an intent to hurt another person, violence or control done to them, a medical "
            "emergency happening now, a possible overdose. Name the kind in category. If it was "
            "danger, choose that kind. When it is unclear, choose the kind that fits, not other. "
            "If you thought about it and it is not danger (an urge to act on a message, a heated "
            "moment that made you stop and think), choose other; frustration that did not is no flag. A threat or a wish to hurt a person is "
            "harm_to_other, even when it is angry or vague, never other. Do NOT set it for ordinary sadness or frustration, "
            "hopelessness or exhaustion (\"I can not do this anymore\"), physical pain or injury "
            "(\"I broke my arm\", \"I fell and hurt myself\"), or an ambiguous \"I need help\". For a "
            "physical injury, ask whether they have been able to get it seen to and how it is "
            "affecting them, then support the emotional side. For anything else ambiguous, ask "
            "one gentle question to learn whether they are in danger or hurting emotionally "
            "first. Set to null when there is no safety concern."
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

    current_issue: str = Field(
        description=(
            "One line, in plain terms: what the person is actually working through right "
            "now. Replaced each run to match the newest messages, even where the fuller "
            "summary still carries older history. Never a technique name, never a feeling "
            "alone - the situation or question they came with."
        )
    )
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
