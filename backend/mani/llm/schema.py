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
            "What they said for this stage, in their words and said to them as you, such as "
            "\"your boss criticized your work in front of the team\", or the possibility of yours they "
            "picked or restated as theirs. One event or thought, a dozen words at most. Never they or "
            "the user for them."
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
    gap: str | None = Field(
        default=None,
        description=(
            "partial only: which part of the stage they have not given yet, by the id of its line in "
            "stage_if_unclear, such as challenge for dispute. Null otherwise."
        ),
    )


class NextStage(BaseModel):
    """How the conversation answers the stage the walk reaches next. `status` and `gap` are checked
    by code (walk.py), not typed, for the reason the note on SHAPES gives."""

    model_config = ConfigDict(extra="ignore")

    status: str = Field(
        description=(
            "known: their words answer the stage. partial: part of it is there. possible: activate "
            "only, an event that likely started this but they never said so. missing: nothing they "
            "said answers it."
        )
    )
    said: str | None = Field(
        default=None,
        description=(
            "What they said for this stage, in their words and said to them as you, a dozen words at "
            "most. Never they or the user for them. Null when missing."
        ),
    )
    gap: str | None = Field(
        default=None,
        description=(
            "partial only: which part of the stage they have not given yet, by the id of its line in "
            "next_stage_if_unclear, such as challenge for dispute. Null otherwise."
        ),
    )


# Merged into the thread's record by chat/understanding.py. The docstring is sent to the model.
class UnderstandingUpdate(BaseModel):
    """The feelings their message names. They are added to the ones already known and never replace them.
    A null keeps what is already known."""

    model_config = ConfigDict(extra="ignore")

    feeling: str | None = Field(
        default=None,
        description=(
            "Each feeling word this message names, in their words and in the form that reads after "
            "\"feeling\", such as \"frustrated\", separated by commas. Only ones they used and that "
            "are new. They are added to the ones already known. Null otherwise."
        ),
    )


# Read by the orchestrator: a check with all its parts, on a reply that judged the heart of it ready, is written to
# the thread, and repairs sends its parts in this order in place of the reply's text. The docstring is sent to the
# model.
class Check(BaseModel):
    """Your check of what you understand, filled only on the reply that checks it with them. Together the
    parts read as a short flowing summary of two or three sentences, in your own words, said to them as you,
    from their words only. Each part continues the one before it and is never a list. The parts are sent in
    this order, in place of your text."""

    model_config = ConfigDict(extra="ignore")

    conflict: str | None = Field(default=None, description="The heart of it: what they are torn between or what it means to them, the start of the summary.")
    want: str | None = Field(default=None, description="What they want, continuing from the conflict as one thought.")
    in_the_way: str | None = Field(default=None, description="What is stopping them, continuing from the part before.")
    question: str | None = Field(default=None, description="Your one question asking whether that captures what they have been experiencing, leaving room for something you missed.")


OfferAnswer = Literal["yes", "no", "asked", "moved_on"]
CheckAnswer = Literal["yes", "no"]
BodyBranch = Literal[
    "yes", "no", "chest", "stomach", "head", "jaw_face", "hands", "eyes", "feet", "toes", "arms", "other",
    "nearest", "none", "pain", "better", "same", "worse", "helped", "somewhat", "not_really", "finish", "unclear",
]
StageAnswer = Literal["agreed", "answered", "corrected", "stop", "not_yet"]
Heart = Literal["exploring", "conflict_named", "ready"]
_CLOSED_SETS = {
    "offer_answer": get_args(OfferAnswer),
    "check_answer": get_args(CheckAnswer),
    "body": get_args(BodyBranch),
    "stage_answer": get_args(StageAnswer),
    "heart": get_args(Heart),
}


class Moment(StrEnum):
    """What the database says is happening this turn. It picks the reply shape, so a field
    exists only in the moment where it means something."""

    CONCERN = "concern"
    BODY = "body"
    IN_STAGES = "in_stages"
    OFFER_OPEN = "offer_open"
    CHECK_OPEN = "check_open"
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

    @field_validator("offer_answer", "check_answer", "heart", "body", "stage_answer", mode="before", check_fields=False)
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

    # Mani's text comes right after the reasoning and the answers that decide what moment this is, the
    # stage answer before the stage updates and the next stage, so the text is written for what they
    # report: structured output is generated in schema order, and the reading of the person (the
    # understanding, the set heading toward, the shape) planned the reply as a case note while it came
    # first (live, 2026-10-13). The stage fields still come before text, since the stage's words are
    # code's and the text follows them; heading_toward still comes before offer.
    reasoning: str | None = Field(
        default=None,
        description=(
            "Fill this first, before text. Work through the steps under 'The reasoning "
            "field' in your instructions. Not shown to the user."
        ),
    )
    check_answer: CheckAnswer | None = Field(
        default=None,
        description=(
            "How they answered the check of your understanding in your last reply. yes only when "
            "they clearly agree with all of it. no for anything else: a correction, an addition, "
            "or talking about something else."
        ),
    )
    heart: Heart | None = Field(
        default=None,
        description=(
            "Where your reading of the heart of it stands, from the whole conversation including their "
            "message. exploring: the central conflict is not clear yet. conflict_named: you said the "
            "tension back to them and they agreed. ready: the conflict is agreed, and you also know what "
            "they want and what is stopping them."
        ),
    )
    offer_answer: OfferAnswer | None = Field(
        default=None,
        description=(
            "How they answered the offer in your last reply: yes, no, asked (about it, or what "
            "it involves), or moved_on (they talked about something else)."
        ),
    )
    body: BodyBranch | None = Field(
        default=None,
        description=(
            "What their message answers at the body check-in step named by body_step in [ctx], by one of "
            "the values listed there. Null when none fits."
        ),
    )
    stage_answer: StageAnswer | None = Field(
        default=None,
        description=(
            "How their message answers the stage in force. agreed: yes to your check of what they "
            "said, even with more added. answered: they gave what the stage needs, or picked one of "
            "your possibilities as theirs, with an update for it. corrected: a no with new words, with "
            "an update for it. not_yet: a plain no, unclear, unsure, I don't know, a question back about what you "
            "asked, or only part of what the stage needs, so the walk stays. stop: they clearly want to stop or leave the questions."
        ),
    )
    stage_updates: list[StageUpdate] | None = Field(
        default=None,
        description=(
            "Fill it before text. The stage in force, from their message, and an earlier stage they "
            "correct. Never what stages_known already holds unchanged. Null when there is none. Not "
            "shown to the user."
        ),
    )
    next_stage: NextStage | None = Field(
        default=None,
        description=(
            "Fill it before text, every time: how this conversation answers the stage named next_stage "
            "in [ctx], judged by next_stage_ready_when and next_stage_reach from everything they have "
            "said about the issue they confirmed, before or after your check, the latest words for "
            "each part. Used only if the walk reaches that stage this turn. Not shown to the user."
        ),
    )
    text: str = Field(
        description="What Mani says to them, in the style they chose. Required."
    )
    options: str | None = Field(
        default=None,
        description=(
            "A second, full question that makes it easy to answer: two or three concrete possibilities for "
            "the question your text ends on, drawn from their case and what they said, and room for "
            "something else. It starts with a verb, such as Is, Has, Are, Do or Would, reads as you would ask "
            "it aloud, and never tells them what they feel. Sent on the line under your text, so your text "
            "never holds them. Null only when your question is yes or no, you ask nothing, or you are "
            "checking your understanding."
        ),
    )
    understanding_update: UnderstandingUpdate | None = Field(
        default=None,
        description=(
            "Only what their message names or changes about their feeling, their "
            "issue, what lies under it, or the feeling underneath it. Not shown to the user."
        ),
    )
    heading_toward: str | None = Field(
        default=None,
        description=(
            "The id from the Framework Index that this "
            "conversation is most likely heading toward, or null when nothing has pointed "
            "anywhere yet. It decides which set you offer, never what you ask. Not shown to "
            "the user."
        ),
    )
    style: Style | None = Field(
        default=None,
        description=(
            "The response shape this reply used."
        ),
    )
    check: Check | None = Field(
        default=None,
        description=(
            "Fill it only when heart is ready in this reply: it checks your understanding with them. "
            "Null otherwise. Not shown to the user."
        ),
    )
    offer: Offer | None = Field(
        default=None,
        description=(
            "Fill it only when check_answer is yes: the set in heading_toward, closest to what they "
            "confirmed. Null otherwise. The offer's words are the client's: you fill only these "
            "parts, in their words. Your text is not sent when the offer is."
        ),
    )
    their_words: str | None = Field(default=None)
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


_CORE = ("reasoning", "style", "understanding_update", "text", "title", "crisis")
_STAGES = ("stage_updates", "stage_answer")
# The stage the walk may reach this turn, judged on every turn that can start or move the walk. Not at
# the closing, which the body route follows.
_REACH = ("next_stage",)


@functools.cache
def reply_for(
    moment: Moment,
    *,
    may_check: bool = False,
    declined_row: bool = False,
    slots: Slots = Slots(),
) -> type[BaseModel]:
    """The reply shape sent this turn: the core fields plus what this moment needs. A field that
    is not here cannot be filled, so the gate is the database that picked the moment."""
    names = set(_CORE)
    overrides: dict[str, tuple] = {}
    if moment is Moment.BODY:
        names |= {"body", "options"}
    elif moment is Moment.IN_STAGES:
        names |= {*_STAGES, *_REACH, "options"}
    elif moment is Moment.OFFER_OPEN:
        names |= {"offer_answer", *_STAGES, *_REACH, "options"}
        if slots.their_words:
            names.add("their_words")
            overrides["their_words"] = (
                str | None,
                Field(default=None, description=f"Only on no, or when they chose Keep chatting: {slots.their_words}."),
            )
    elif moment is Moment.CHECK_OPEN:
        # The answer to a check is where the set is chosen, and a no carries on toward the heart of it.
        names |= {"check_answer", "heading_toward", "heart"}
        if slots.going_through:
            names.add("offer")
            overrides["offer"] = (_offer_model(slots.going_through, slots.lead_line) | None, Reply.model_fields["offer"])
    elif moment is Moment.CHATTING:
        # One question carries its own possibilities, so a chatting reply has no options line (R30).
        names.add("heart")
        if may_check:
            names.add("check")
    if declined_row and moment in (Moment.CHECK_OPEN, Moment.CHATTING):
        names |= {"offer_answer", *_STAGES, *_REACH}
        overrides["offer_answer"] = (
            OfferAnswer | None,
            Field(default=None, description="yes when they ask for the set they declined; null otherwise."),
        )
    order = list(Reply.model_fields)
    if moment is Moment.CHECK_OPEN:
        # On the answer to a check a yes is the client's offer, which replaces the text, so the set and
        # its slots are filled before the text; written after it, the slots were left empty (live,
        # 2026-10-13: "offer unusable: no lead_line" in Supportive and Reflective).
        order = [n for n in order if n not in ("heading_toward", "offer")]
        at = order.index("check_answer") + 1
        order[at:at] = ["heading_toward", "offer"]
    fields = {
        name: overrides.get(name, (Reply.model_fields[name].annotation, Reply.model_fields[name]))
        for name in order
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



# The reply whenever no framework, offer or check is open (orchestrator.converse). The model reads every
# description. Text comes first, so the voice is written before anything is judged about it.
class ConversationReply(_ReplyBase):
    """Mani's reply, and where the conversation stands after it."""

    text: str = Field(description="What Mani says to them. Required.")
    heart: Heart | None = Field(
        default=None,
        description=(
            "exploring: you don't yet know what they are torn between or what it means to them. conflict_named: "
            "you said the heart of it back and they agreed. ready: that is agreed, and you also know what they want "
            "and what is stopping them."
        ),
    )
    conflict: str | None = Field(
        default=None,
        description="Once heart is conflict_named or ready: what they are torn between or what it means to them, one sentence said to them as you. Null otherwise.",
    )
    want: str | None = Field(
        default=None, description="Once known: what they want, one sentence said to them as you. Null otherwise.",
    )
    in_the_way: str | None = Field(
        default=None, description="Once known: what is stopping them, one sentence said to them as you. Null otherwise.",
    )
    checking: bool | None = Field(
        default=None,
        description="True only on the reply that pulls it together and asks whether it describes what they feel.",
    )
    feelings: str | None = Field(
        default=None,
        description="Feeling words they used for the first time in their last message, in their words, separated by commas. Null otherwise.",
    )
    crisis: Crisis | None = Field(
        default=None,
        description="Only when something they said sounds like they may not be safe, or may hurt themselves or someone else. Null otherwise.",
    )
    title: str | None = Field(
        default=None,
        description="Only when the instructions ask for a title: a short title for this conversation. Null otherwise.",
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
