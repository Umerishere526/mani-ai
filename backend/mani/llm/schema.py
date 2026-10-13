# ABOUTME: The JSON shape Mani must reply in, and the field descriptions sent with it.
# ABOUTME: Every description is prompt surface - the model reads them, so wording matters.

from __future__ import annotations

import functools
import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, create_model, field_validator

logger = logging.getLogger(__name__)


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
# The two shapes that ask nothing. A draft that chose one is not asked for a question: the model
# reads when someone only wants to be listened to, so no phrase list has to.
NO_QUESTION_SHAPES = ("mirror and hold", "presence only")


class Button(BaseModel):
    """What every tappable capsule carries."""

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


class Crisis(BaseModel):
    model_config = ConfigDict(extra="ignore")

    reason: str = Field(description="Brief description of the crisis signal")


class Style(BaseModel):
    model_config = ConfigDict(extra="ignore")

    shape: str = Field(
        description=f"The response shape you used: {_listed(SHAPES)}."
    )


class StageUpdate(BaseModel):
    """What they said this turn for one stage. `status` is checked by code (walk.py), not typed,
    for the reason the note on SHAPES gives."""

    model_config = ConfigDict(extra="ignore")

    stage: str = Field(description="The stage id, from framework_stages in [ctx].")
    said: str = Field(
        description=(
            "Their own short words for this stage, never yours. For activate, a phrase that reads "
            "after \"You mentioned\", such as \"being left out of meetings at work\"."
        )
    )
    status: str = Field(
        description=(
            "known: their words answer the stage. partial: half of it is there. possible: "
            "activate only, an event that likely started this but they never said so."
        )
    )
    corrected: bool | None = Field(
        default=None,
        description="True when they said words stored for this stage earlier are wrong.",
    )


# Merged into the thread's record by chat/understanding.py. The docstring is sent to the model.
class UnderstandingUpdate(BaseModel):
    """What their message names or changes about how they feel and what they are dealing with. A
    null keeps what is already known."""

    model_config = ConfigDict(extra="ignore")

    feeling: str | None = Field(
        default=None,
        description=(
            "Their own word for how they feel, only when this message names it or changes it, in the "
            "form that reads after \"feeling\", such as \"frustrated\". Never one they did not use. "
            "Null otherwise."
        ),
    )
    issue: str | None = Field(
        default=None,
        description=(
            "What they are dealing with, in their words, only when this message first makes it clear "
            "or moves to another. Null otherwise."
        ),
    )


OfferAnswer = Literal["yes", "no", "asked", "moved_on"]
BodyBranch = Literal[
    "chest", "head", "stomach", "elsewhere", "no_place", "agreed", "declined", "acting", "pain",
    "returned",
]
StageAnswer = Literal["agreed", "answered", "corrected", "let_go", "not_yet"]
_CLOSED_SETS = {
    "offer_answer": get_args(OfferAnswer),
    "body": get_args(BodyBranch),
    "stage_answer": get_args(StageAnswer),
}


class Moment(StrEnum):
    """What the database says is happening this turn. It picks the reply shape, so a field
    exists only in the moment where it means something."""

    CONCERN = "concern"
    BODY = "body"
    IN_STAGES = "in_stages"
    OFFER_OPEN = "offer_open"
    CHATTING = "chatting"


class Offer(BaseModel):
    """The model's part of an offer: the slots of the client's template, never its words."""

    model_config = ConfigDict(extra="ignore")

    going_through: str | None = None
    lead_line: str | None = None


class _ReplyBase(BaseModel):
    """What every reply shape shares: unknown fields are dropped, and an off-list value in a
    closed set is read as null. A ValidationError there would cost a second call and could
    lose the message, as the note on SHAPES says."""

    model_config = ConfigDict(extra="ignore")

    @field_validator("offer_answer", "body", "stage_answer", mode="before", check_fields=False)
    @classmethod
    def _off_list_is_null(cls, value: object, info) -> object:
        if value is None or value in _CLOSED_SETS[info.field_name]:
            return value
        # The value itself is not logged: it is the model's words, which may carry theirs.
        logger.info("off-list %s ignored", info.field_name)
        return None


class Reply(_ReplyBase):
    """Every field a reply can carry. The model is sent only the subset for this turn's moment
    (`reply_for`), and what it returns is read back into this record, so a field outside the
    moment is always null here."""

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
    understanding_update: UnderstandingUpdate | None = Field(
        default=None,
        description=(
            "Fill it before text: only what their message names or changes about their feeling or "
            "their issue. Not shown to the user."
        ),
    )
    heading_toward: str | None = Field(
        default=None,
        description=(
            "Choose before writing text: the id from the Framework Index that this "
            "conversation is most likely heading toward, or null when nothing has pointed "
            "anywhere yet. It decides which set you offer, never what you ask. Not shown to "
            "the user."
        ),
    )
    offer: Offer | None = Field(
        default=None,
        description=(
            "Fill it to offer the set in heading_toward, when your reasoning says to offer; null "
            "otherwise. The offer's words are the client's: you fill only these parts, in their "
            "words. Your text is not sent when the offer is."
        ),
    )
    offer_answer: OfferAnswer | None = Field(
        default=None,
        description=(
            "How they answered the offer in your last reply: yes, no, asked (about it, or what "
            "it involves), or moved_on (they talked about something else)."
        ),
    )
    their_words: str | None = Field(default=None)
    body: BodyBranch | None = Field(
        default=None,
        description=(
            "The body route branch their message meets, by its id from [ctx]. returned: the "
            "feeling came back after the practice. Null when none fits."
        ),
    )
    stage_updates: list[StageUpdate] | None = Field(
        default=None,
        description=(
            "Fill it before text. Only the stages whose words you learned or that changed in their "
            "message, never what stages_known in [ctx] already holds. On the turn they accept the offer, "
            "every stage the conversation already answers. Null when there is none. Not shown to the user."
        ),
    )
    stage_answer: StageAnswer | None = Field(
        default=None,
        description=(
            "How their message answers the stage in force. agreed: yes to your check of what they "
            "said. answered: they gave what the stage needs, with an update for it. corrected: a no "
            "with new words, with an update for it. let_go: move on without words, because it was "
            "asked twice already or the question made them uneasy. not_yet: a plain no, unclear, or "
            "I don't know while you still help."
        ),
    )
    text: str = Field(description="Your conversational response to the user. Required.")
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
            "Set when the person shows a genuine safety concern - suicidal thoughts, an intent "
            "to self-harm, or a wish to die. This does NOT cut off the conversation; it flags "
            "the moment so the framework pauses and the reply stays with them. Do NOT set it "
            "for ordinary sadness or frustration, hopelessness or exhaustion, physical pain or "
            "injury, or an ambiguous request for help. For anything ambiguous, ask one gentle "
            "question to learn whether they are in danger or hurting emotionally first. Set to "
            "null when there is no safety concern."
        ),
    )
    # There is no clinical_note field. The model was asked for three or four sentences of
    # clinical formulation on every turn, for a care team that has nowhere to read it: it
    # reached no column, no log, and no screen. Paying output tokens for a formulation about
    # someone's mental state and then discarding it is the worst of both - the cost of
    # holding the reading and none of the use. If a care-team surface is ever built, this
    # comes back together with the column, the retention rule and the access policy that
    # make storing it defensible.


@dataclass(frozen=True)
class Slots:
    """What each slot of the client's templates asks for, in the thread's style: the text inside
    its `<...>`. The client's own description of the slot is what the model reads."""

    going_through: str | None = None
    lead_line: str | None = None
    their_words: str | None = None


_CORE = ("reasoning", "style", "understanding_update", "heading_toward", "text", "title", "crisis")
_STAGES = ("stage_updates", "stage_answer")


@functools.cache
def reply_for(
    moment: Moment,
    *,
    may_offer: bool = False,
    declined_row: bool = False,
    on_closing: bool = False,
    slots: Slots = Slots(),
) -> type[BaseModel]:
    """The reply shape sent this turn: the core fields plus what this moment needs. A field that
    is not here cannot be filled, so the gate is the database that picked the moment."""
    names = set(_CORE)
    overrides: dict[str, tuple] = {}
    if moment is Moment.BODY:
        names |= {"body", *(_STAGES if on_closing else ())}
    elif moment is Moment.IN_STAGES:
        names |= set(_STAGES)
    elif moment is Moment.OFFER_OPEN:
        names |= {"offer_answer", *_STAGES}
        if slots.their_words:
            names.add("their_words")
            overrides["their_words"] = (
                str | None,
                Field(default=None, description=f"Only on no, or when they chose Keep chatting: {slots.their_words}."),
            )
    elif moment is Moment.CHATTING:
        if may_offer and slots.going_through:
            names.add("offer")
            overrides["offer"] = (_offer_model(slots.going_through, slots.lead_line) | None, Reply.model_fields["offer"])
        if declined_row:
            names |= {"offer_answer", *_STAGES}
            overrides["offer_answer"] = (
                OfferAnswer | None,
                Field(default=None, description="yes when they ask for the set they declined; null otherwise."),
            )
    fields = {
        name: overrides.get(name, (info.annotation, info))
        for name, info in Reply.model_fields.items()
        if name in names
    }
    return create_model("Reply", __base__=_ReplyBase, **fields)


@functools.cache
def _offer_model(going_through: str, lead_line: str | None) -> type[BaseModel]:
    """The offer's slots in this style. lead_line exists only when the style's template opens
    with a whole line of the model's own."""
    fields: dict[str, tuple] = {"going_through": (str | None, Field(default=None, description=going_through))}
    if lead_line:
        fields["lead_line"] = (str | None, Field(default=None, description=lead_line))
    return create_model("Offer", __config__=ConfigDict(extra="ignore"), **fields)


def as_reply(parsed: BaseModel) -> Reply:
    """A reply in this turn's shape, read into the full record, every absent field null."""
    return Reply.model_validate(parsed.model_dump())


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
        description=(
            "What they said did not help, asked not to do, or a question they skipped or found "
            "uncomfortable."
        ),
    )
    how_they_talk: list[str] = Field(
        default_factory=list,
        description=(
            "How they like the conversation to go, from how they responded: e.g. \"prefers "
            "short replies\", \"usually declines exercises\"."
        ),
    )
