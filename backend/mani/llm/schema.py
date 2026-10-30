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


class StageUpdate(BaseModel):
    """What they said this turn for one stage. `status` is checked by code (walk.py), not typed,
    for the reason under CLOSED SETS."""

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
    by code (walk.py), not typed, for the reason under CLOSED SETS."""

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


class FeelingEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    feeling: str = Field(
        description=(
            "An emotion they named, in their word, in the form that reads after \"feeling\", such as \"guilty\" or "
            "\"stuck\". Only an emotion: \"not unhappy\", \"okay with where I am\" or \"fine\" are how they rate their "
            "life, not feelings, and are left out. Never a belief about themselves: \"incapable\", \"not good enough\" "
            "or \"a failure\" are beliefs and go in beliefs."
        ),
    )
    about: str | None = Field(
        default=None, description="What it is about, a few of their words said to them as you. Null when they did not say.",
    )


class UnderneathEntry(BaseModel):
    """A feeling under the ones they named, as Mani reads it (muhammad, 2026-10-29): the reading the core is built on."""

    model_config = ConfigDict(extra="ignore")

    feeling: str = Field(
        description=(
            "A feeling under the ones they named, as you read it, a word or a few, such as \"inadequacy\" under "
            "\"worse about my life\", \"guilt about comparing\" or \"pressure of time\"."
        ),
    )
    rests_on: str | None = Field(
        default=None,
        description="What of theirs it rests on, a few of their words, such as \"I should be further along by now\".",
    )


class BeliefEntry(BaseModel):
    """`kind` is checked by code (chat/picture.py), not typed, for the reason under CLOSED SETS."""

    model_config = ConfigDict(extra="ignore")

    belief: str = Field(description="What they tell themselves, or say is happening, in their words said to them as you.")
    kind: str = Field(
        description=(
            "thought: something they tell themselves or conclude, such as \"you're a bad brother\". happening: "
            "something they say is really happening, which is not theirs to question, such as \"she falls asleep "
            "while the children are there\". new: a new, more balanced way of seeing it they reached, such as at a "
            "framework's last stage; never filed as a thought."
        ),
    )


class CoreEntry(BaseModel):
    """The core of it (muhammad, 2026-10-28). `about` is checked by code (chat/picture.py), not typed, for the reason
    under CLOSED SETS."""

    model_config = ConfigDict(extra="ignore")

    belief: str = Field(
        description=(
            "The deepest belief their other thoughts lead to, or the tension at the heart of it, in their words said "
            "to them as you, such as \"one slip proves you can't change\" or \"you love her, and you feel you don't "
            "matter to her\"."
        ),
    )
    feeling: str | None = Field(
        default=None,
        description=(
            "The feeling under the feelings they named, as you read it, such as shame under guilt or hopelessness "
            "under frustration. A word or two. Null until you can tell."
        ),
    )
    tension: str | None = Field(
        default=None,
        description=(
            "When two things they feel or want pull against each other, the tension in one line said to them as you, "
            "such as \"you're glad for them, and their news still makes you feel you're failing\". Null otherwise."
        ),
    )
    about: str = Field(description="self: what it says about them. others: about someone else. situation: about what is happening.")


class RiskEntry(BaseModel):
    """`to` is checked by code (chat/picture.py), not typed, for the reason under CLOSED SETS."""

    model_config = ConfigDict(extra="ignore")

    risk: str = Field(description="The risk, a few words said to them as you.")
    to: str = Field(description="self: to them. others: to someone else, such as children in their care.")


class DependencyEntry(BaseModel):
    """`kind` is checked by code (chat/picture.py), not typed, for the reason under CLOSED SETS."""

    model_config = ConfigDict(extra="ignore")

    what: str = Field(description="What the outcome depends on, a few words said to them as you.")
    kind: str = Field(
        description=(
            "internal: inside them, such as their fear of being let down again. external: outside them, such as the "
            "other person's follow-through or a manager's decision."
        ),
    )


# Mani's whole reading of them, given every chat turn before the reply is written (muhammad, 2026-10-29, approach
# A): the partner chat named "am I settling" in its first message, and five turns later the picture still held no
# core, want, need or desire, because the picture is only what each message adds and every reading was optional.
# The reading is never a delta: it is re-read from the whole conversation, the first message included, and every
# field is filled, "unclear" only when nothing they said points to it. Applied over the picture by chat/picture.py.
class Reading(BaseModel):
    model_config = ConfigDict(extra="ignore")

    underneath: list[UnderneathEntry] = Field(
        description=(
            "Every feeling you read under the ones they named, across the whole conversation, each with the words "
            "of theirs it rests on. Usually one to three. Empty only when nothing they said supports a reading."
        ),
    )
    wants: str = Field(
        description="What they want, in their own words, from anywhere in the conversation. \"unclear\" only when they have said nothing about it.",
    )
    needs: str = Field(
        description=(
            "What they need underneath what they want, your reading, such as \"to feel close and chosen, not just "
            "living alongside each other\". \"unclear\" only when nothing they said points to it."
        ),
    )
    desire: str = Field(
        description=(
            "The life or relationship they long for, your reading, in a line, and any gap between it and what they "
            "measure themselves against. Never states as wanted something they are unsure about: a fear of missing "
            "a family is not a wish for one. \"unclear\" only when nothing they said points to it."
        ),
    )
    uncertain: list[str] = Field(
        description=(
            "What is still uncertain, in a few words each: what they said they don't know yet, or are only starting "
            "to wonder about, such as \"whether they want marriage or children\" or \"whether they protect their freedom "
            "at the cost of connection\". Never said back to them as settled. Empty when nothing is."
        ),
    )
    focus: str = Field(
        description=(
            "The concern the conversation is really about now, a few words, re-read every reply: when a deeper concern "
            "has come out, the focus moves to it, such as from \"feeling behind friends' milestones\" to \"fear of losing "
            "connection while protecting independence\". Always a concern, never a solution."
        ),
    )
    core: str = Field(
        description=(
            "The belief their thoughts lead to, said to them as you, such as \"you might be settling for something "
            "that isn't fulfilling anymore\". When they have said what they tell themselves, about themselves, their "
            "relationship, their life or their choices, there is a core: name it. \"unclear\" only when they have "
            "said nothing of the kind."
        ),
    )
    core_from: str = Field(description="The words of theirs the core rests on, quoted. \"unclear\" when the core is.")
    core_feeling: str = Field(
        description="The feeling under the core, your reading, a word or two, such as inadequacy or loneliness. \"unclear\" when you cannot tell.",
    )
    core_about: str = Field(
        description="self: what it says about them. others: about someone else. situation: about what is happening or their life.",
    )
    tension: str = Field(
        description=(
            "Two things they feel or want that pull against each other, one line said to them as you, such as \"you "
            "love them, and you're not sure you're happy\". \"none\" when there is none."
        ),
    )
    problem_type: str = Field(
        description=(
            "belief: what they tell themselves is what hurts. situation: something really happening that needs "
            "dealing with, and nothing they tell themselves about it. both: something happening and something they "
            "tell themselves about it. When they have said what they tell themselves, it is never situation alone."
        ),
    )


# Merged into the thread's picture by chat/picture.py on every turn, in the chat and in a framework alike. The
# docstrings and descriptions are sent to the model.
class PictureUpdate(BaseModel):
    """What their last message adds to or changes in your picture of them. Only what is new or changed: never
    what the picture already holds. Every entry is a few of their words, said to them as you. Not shown to them.
    `shift` and `problem_type` are checked by code (chat/picture.py), not typed, for the reason CLOSED SETS
    says."""

    model_config = ConfigDict(extra="ignore")

    situations: list[str] | None = Field(default=None, description="What is happening, as they tell it. Null when nothing new.")
    feelings: list[FeelingEntry] | None = Field(default=None, description="Feelings they named for the first time, in their words. Null when none.")
    underneath: list[UnderneathEntry] | None = Field(
        default=None,
        description=(
            "Feelings under the ones they named, as you read them, each with what of theirs it rests on: new or "
            "changed only. Fill it as soon as their words support a reading, usually from their first message. Null "
            "when none is new."
        ),
    )
    beliefs: list[BeliefEntry] | None = Field(
        default=None, description="What they tell themselves, or say is really happening, that is new. Null when none.",
    )
    core: CoreEntry | None = Field(
        default=None,
        description=(
            "The core of it, only when you can first tell or it changes: the belief the other thoughts lead to, and "
            "the feeling underneath. Null otherwise."
        ),
    )
    wants: str | None = Field(
        default=None, description="What they want, in their words, when it is new or has changed. Null otherwise.",
    )
    needs: str | None = Field(
        default=None,
        description=(
            "What they need underneath what they want, as you read it, such as \"to feel they're enough by their own "
            "measure\" or \"to feel cared for without having to ask\". When it is new or has changed. Null otherwise."
        ),
    )
    desire: str | None = Field(
        default=None,
        description=(
            "The life or the relationship they long for, as you read it, in a line, and any gap between it and what "
            "they measure themselves against. When it is new or has changed. Null otherwise."
        ),
    )
    in_the_way: str | None = Field(
        default=None, description="What is stopping them, when it is new or has changed. Null otherwise.",
    )
    risks: list[RiskEntry] | None = Field(
        default=None, description="A risk to them or to someone else that their message shows. Null when none.",
    )
    dependencies: list[DependencyEntry] | None = Field(
        default=None,
        description="What the outcome depends on that their message shows for the first time, inside or outside them. Null when none.",
    )
    drop: list[str] | None = Field(
        default=None,
        description="Entries in your picture that their message shows are wrong, copied exactly as the picture shows them. Null when none.",
    )
    focus: str | None = Field(
        default=None,
        description=(
            "The situation the conversation is about now, a few words, only when it is new or has changed. Always the "
            "problem they brought, never a solution or a step being considered, such as \"feeling behind friends in "
            "career\", not \"exploring other jobs\". Null otherwise."
        ),
    )
    shift: str | None = Field(
        default=None,
        description=(
            "What their message did. adds: something new about the same situation. corrects: something in your "
            "picture was wrong. new_issue: a different situation. back: back to a situation from earlier. "
            "answered: a short answer to your last question, such as \"both\" or \"comfortable\", that confirms or "
            "chooses without adding much; it is an answer, not someone pulling away. nothing_new: it added nothing you "
            "did not know and answered nothing you asked."
        ),
    )
    problem_type: str | None = Field(
        default=None,
        description=(
            "Once you can tell, what kind of problem this is. belief: what they tell themselves is what hurts. "
            "situation: something really happening that needs dealing with. both. Null until you can tell."
        ),
    )


OfferAnswer = Literal["yes", "no", "asked", "moved_on"]
CheckAnswer = Literal["yes", "no"]
BodyBranch = Literal[
    "yes", "no", "chest", "stomach", "head", "jaw_face", "hands", "eyes", "feet", "toes", "arms", "other",
    "nearest", "none", "pain", "better", "same", "worse", "helped", "somewhat", "not_really", "finish", "unclear",
]
StageAnswer = Literal["agreed", "answered", "corrected", "stop", "not_yet"]
Heart = Literal["exploring", "core_named", "ready"]
# The three shapes of a chat reply (the client's test, 2026-10-29): acknowledge and ask openly while there is not enough
# to go on; open the window when a feeling is tied to something outside them; add the insight when there is enough.
# reflect (the client's review, 2026-10-29): now and then an acknowledgment and an observation that lets them go on,
# without a question, so the reply is not the same formula every turn. Never two in a row.
Shape = Literal["open_ask", "window", "insight", "reflect"]
# What a chat reply offers besides its question. Each moves the conversation; none fixes their situation, which is
# the framework's work (the client's test, 2026-10-29: suggestions that move it on, never solutions).
Move = Literal["none", "clarifying_options", "step", "possibilities", "small_idea"]
# Whether the set of questions is still helping them (muhammad, 2026-10-27): anything but helping makes the reply offer
# to step out, and code remembers the offer for their answer.
FrameworkFit = Literal["helping", "confused", "real_not_belief", "already_balanced", "disengaging"]
_CLOSED_SETS = {
    "offer_answer": get_args(OfferAnswer),
    "check_answer": get_args(CheckAnswer),
    "body": get_args(BodyBranch),
    "stage_answer": get_args(StageAnswer),
    "heart": get_args(Heart),
    "shape": get_args(Shape),
    "move": get_args(Move),
    "framework_fit": get_args(FrameworkFit),
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
    lose the message, as CLOSED SETS says."""

    model_config = ConfigDict(extra="ignore")

    @field_validator(
        "offer_answer", "check_answer", "heart", "body", "stage_answer", "framework_fit", "shape", "move", mode="before",
        check_fields=False,
    )
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
            "Fill this first, before text, in a few short notes as your instructions say. Not shown to the user."
        ),
    )
    check_answer: CheckAnswer | None = Field(
        default=None,
        description=(
            "How they answered your last reply, which gave your insight into the core and asked whether it "
            "captures what they feel. yes only when they clearly agree it does. no for anything else: a correction, "
            "an addition, wanting to keep talking, or something else."
        ),
    )
    heart: Heart | None = Field(
        default=None,
        description=(
            "Where your reading of the core of it stands, from the whole conversation including their message. exploring: you do not know the core yet, the belief the other thoughts lead to and the feeling underneath. core_named: you said the core back to them as an invitation and they did not correct it; carrying on or answering your next question counts, and it stays named unless they say that is not it. ready: it is named, and their message since deepened or confirmed it rather than changing it."
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
    framework_fit: FrameworkFit | None = Field(
        default=None,
        description=(
            "Whether the set of questions is still helping them, from the whole conversation. helping. confused: "
            "they do not understand what is asked, again. real_not_belief: what the stage would have them question "
            "is something really happening. already_balanced: they already see both sides of it. disengaging: "
            "shorter answers, or they say they already told you or this is going in circles. Anything but helping: "
            "your text offers to step out of the questions."
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
            "Only when their last message says they don't know or aren't sure, asks what you mean, or asks what "
            "they should do: a second, full question with two or three possibilities for the question your text "
            "ends on, drawn from their case and what they said, and room for something else. Each possibility is a "
            "plain thing a person would actually think or do in their situation. At E, and whenever they ask what "
            "to do, they may be concrete things they could do, offered as ideas for them to choose from. It starts "
            "with a verb, such as Is, Has, Are, Do or Would, and never tells them what they feel. Never the same "
            "possibilities, or the same question, as an earlier reply. Null otherwise."
        ),
    )
    picture: PictureUpdate | None = Field(
        default=None,
        description="Fill it after text, every reply: what their message adds to or changes in your picture of them.",
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


_CORE = ("reasoning", "picture", "text", "title", "crisis")
_STAGES = ("stage_updates", "stage_answer")
# The stage the walk may reach this turn, judged on every turn that can start or move the walk. Not at
# the closing, which the body route follows.
_REACH = ("next_stage",)


@functools.cache
def reply_for(
    moment: Moment,
    *,
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
        # A stage turn speaks in the chat's voice (prompts/voice.md and framework.md): no reasoning pass, the
        # stage fields are its judgement.
        names = (names - {"reasoning"}) | {*_STAGES, *_REACH, "options", "framework_fit"}
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
    if declined_row and moment is Moment.CHECK_OPEN:
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



class Window(BaseModel):
    """Opening the window (the client's test, 2026-10-29): a feeling joined to what it is tied to, outside them or inside
    them, so the question lands on both, never on the feeling alone (the client's review, 2026-10-29: loneliness and
    independence)."""

    model_config = ConfigDict(extra="ignore")

    feeling: str = Field(description="The feeling, in their words or as you read it.")
    tied_to: list[str] = Field(
        description=(
            "What it is tied to, from your picture, one or two, a few words each: outside them (what is happening, "
            "another person's behavior, a dependency) or inside them (a value, a need or a pull, such as their "
            "independence)."
        ),
    )
    closest: str = Field(
        description="Of tied_to, the one the feeling is most closely tied to: your question lands on it, with the feeling.",
    )


def _reading_required(schema: dict) -> None:
    """The reading is required of the model, never null, while code still reads a reply without one as null, so a
    reply that left it out costs no second call (CLOSED SETS)."""
    schema.setdefault("required", [])
    if "reading" not in schema["required"]:
        schema["required"].insert(0, "reading")
    field = schema.get("properties", {}).get("reading") or {}
    ref = next((option for option in field.pop("anyOf", []) if option.get("type") != "null"), None)
    if ref:
        field.update(ref)
    field.pop("default", None)


# The reply whenever no framework, offer or check is open (orchestrator.converse). The model reads every
# description. Understanding comes before the text (muhammad, 2026-10-29, approach A): written first, the text
# followed the facts of the last message and the picture judged afterwards never shaped it.
class ConversationReply(_ReplyBase):
    """Mani's reply, and where the conversation stands after it. Fill the fields in order: first your whole reading of
    them and what their message adds to the picture, then what this turn calls for, then the text, which follows from
    all of it (muhammad, 2026-10-29)."""

    model_config = ConfigDict(extra="ignore", json_schema_extra=_reading_required)

    reading: Reading | None = Field(
        default=None,
        description=(
            "Fill it first, every reply: your whole reading of them, re-read from the whole conversation including "
            "their first message, never only their last."
        ),
    )
    picture: PictureUpdate | None = Field(
        default=None,
        description="Fill it second, every reply: what their message adds to or changes in the facts of your picture of them.",
    )
    heart: Heart | None = Field(
        default=None,
        description=(
            "Where your reading of the core of it stands, from the whole conversation including their message. exploring: you do not know the core yet, the belief the other thoughts lead to and the feeling underneath. core_named: you said the core back to them as an invitation and they did not correct it; carrying on or answering your next question counts, and it stays named unless they say that is not it. ready: it is named, and their message since deepened or confirmed it rather than changing it. Say the core in this reply's text and it is core_named."
        ),
    )

    need: str | None = Field(
        default=None,
        description="What they need from you right now, a few words, judged against your reading as well as their last message.",
    )
    needs_info: bool | None = Field(
        default=None,
        description=(
            "Whether you need to know something from them that you cannot infer from the conversation. False when you "
            "have something useful to give."
        ),
    )
    info_needed: str | None = Field(default=None, description="Only when needs_info is true: what exactly, and what of theirs it connects to.")
    shape: Shape | None = Field(
        default=None,
        description=(
            "The shape of this reply. open_ask: not enough to go on yet; acknowledge, then one open question. "
            "window: a feeling is tied to something outside them; acknowledge, open the window, then ask about the "
            "feeling with what it is tied to, outside or inside them. insight: you have enough and there is a new "
            "connection to make; acknowledge, open the window, give the insight, then ask a question built on it. "
            "reflect: now and then, never two in a row, never on the reply that checks; a specific acknowledgment and "
            "an observation that lets them go on, with no direct question."
        ),
    )
    window: Window | None = Field(
        default=None, description="With shape window or insight: the feeling and the outside things it is tied to. Null otherwise.",
    )
    insight: str | None = Field(
        default=None,
        description=(
            "Only with shape insight: the aha, a connection between something that happened and a feeling that they "
            "have not put together, a sentence said as your reading. Never a suggestion, a step or a fix. Null otherwise."
        ),
    )
    insight_from: str | None = Field(
        default=None, description="Only with an insight: the situation and the feeling it joins, in a few of their words.",
    )
    link: str | None = Field(
        default=None,
        description=(
            "Only when their message brings in something new, a situation, a feeling or a person, and your picture "
            "already holds a core, need or desire: how it connects, starting with what it links to, such as \"core: "
            "the same sense of not doing enough\" or \"need: wanting to be seen\", or \"none: a separate issue\". "
            "Null otherwise."
        ),
    )
    move: Move | None = Field(
        default=None,
        description=(
            "What the reply offers besides its question, if anything. none. clarifying_options: two or three readings "
            "to choose from, such as \"is it more the time, or that it feels one-sided?\". step: a step in the "
            "conversation, such as staying with one situation first. possibilities: what it could be, when they are "
            "unsure. small_idea: one small idea, only when they asked what to do, before offering to work it through. "
            "Never a fix for their situation: that is the framework's work."
        ),
    )
    plan: str | None = Field(
        default=None,
        description="Where this conversation is heading, one line: what you know, and what comes next toward the framework.",
    )
    text: str = Field(description="What Mani says to them, following from the fields above. Required.")
    core: str | None = Field(
        default=None,
        description=(
            "Once heart is core_named or ready: the core of it and the feeling underneath, one or two sentences said "
            "to them as you, such as \"One slip feels like proof that you can't change, and underneath the guilt "
            "there is shame about who you are.\" Null otherwise."
        ),
    )
    checking: bool | None = Field(
        default=None,
        description="True only on the reply that pulls it together and asks whether it describes what they feel.",
    )
    crisis: Crisis | None = Field(
        default=None,
        description="Only when something they said sounds like they may not be safe, or may hurt themselves or someone else. Null otherwise.",
    )
    asked_for_help: bool | None = Field(
        default=None,
        description="True when their last message asks you for help, ideas, an exercise or what to do.",
    )
    frustrated: bool | None = Field(
        default=None,
        description=(
            "True when their last message shows they are frustrated with you or the conversation, such as going in "
            "circles, already having told you, or wanting something more."
        ),
    )
    back_to_framework: bool | None = Field(
        default=None,
        description="Only when the note says they stepped out of a set of questions: true when they ask to go back to it.",
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
