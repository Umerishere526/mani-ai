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


SafetySignal = Literal[
    "possible", "wish_to_be_dead", "suicidal_thoughts", "self_harm", "means", "intent", "plan", "acted",
    "cannot_stay_safe", "harm_to_others", "abuse", "medical_emergency",
]
SafetyAnswer = Literal["safe", "unsafe", "declined", "unclear"]


class SafetyRead(BaseModel):
    """Mani's reading of their message for safety, made before the reply is written (muhammad, 2026-11-06). Code owns
    what it moves (chat/safety.after); the model only reads."""

    model_config = ConfigDict(extra="ignore")

    signals: list[SafetySignal] = Field(
        default_factory=list,
        description=(
            "Every sign in their message, read with the whole conversation, that they may not be safe. possible: words "
            "that may mean it and may not, such as \"I'm done\" or \"I don't know how much more I can take\". "
            "wish_to_be_dead: wishing to disappear, not to wake up, that others would be better off without them. "
            "suicidal_thoughts: thinking about ending their life, or how much easier it would be not to be alive. "
            "self_harm: thoughts of hurting themselves. means: something near them they could use. intent: they mean "
            "to act, or are scared of what they might do. plan: how or when. acted: they have already hurt themselves "
            "or taken something. cannot_stay_safe: they say they cannot keep themselves safe. harm_to_others, abuse: "
            "someone in danger from them, or them from someone. medical_emergency. A negated or past-tense mention "
            "(\"I'm not going to hurt myself\") is not the sign itself; ordinary sadness, frustration or physical pain "
            "is none of these. Empty when there is none."
        ),
    )
    answer: SafetyAnswer | None = Field(
        default=None,
        description=(
            "Only while safety in [ctx] is open or unsafe: how their message stands on their safety. safe: what they "
            "say, read with everything before it, shows they are not in danger now; a bare reassurance right after a "
            "plan, the means or fear of acting is unclear, not safe. unsafe: they are in danger now. declined: they "
            "refuse or push the question away. unclear: anything else, including talking about something else."
        ),
    )

    @field_validator("signals", mode="before")
    @classmethod
    def _known_signals(cls, value: object) -> object:
        allowed = set(get_args(SafetySignal))
        return [v for v in value if v in allowed] if isinstance(value, list) else []

    @field_validator("answer", mode="before")
    @classmethod
    def _known_answer(cls, value: object) -> object:
        return value if value in get_args(SafetyAnswer) else None


_SAFETY_DESCRIPTION = (
    "Read their message for safety before anything else, and fill this first: it decides what your text is for. Null "
    "only when there is no sign at all and safety in [ctx] is not open."
)


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
            "while the children are there\". new: a new, more balanced way of seeing it they reached, or evidence they "
            "found against what they tell themselves, such as \"your manager has praised your projects\"; never filed as "
            "a thought."
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


# What a feeling may depend on, in the order Mani would explore it (the client meeting, 2026-11-03: muhammad's funnel,
# narrowing down what it depends on instead of asking around it). `side` is checked by code, as CLOSED SETS says.
class TiedTo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    what: str = Field(description="What it may depend on, a few words said to them as you, such as \"your manager's comments\".")
    side: str = Field(
        description="outside: a person, a situation or something they depend on. inside: a value, a need or a fear of theirs.",
    )


def _tied_to_required(schema: dict) -> None:
    """tied_to is asked of the model like every reading field, while a reply without it still reads as empty."""
    schema.setdefault("required", [])
    if "tied_to" not in schema["required"]:
        schema["required"].append("tied_to")


# Mani's whole reading of them, given every chat turn before the reply is written (muhammad, 2026-10-29, approach
# A): the partner chat named "am I settling" in its first message, and five turns later the picture still held no
# core, want, need or desire, because the picture is only what each message adds and every reading was optional.
# The reading is never a delta: it is re-read from the whole conversation, the first message included, and every
# field is filled, "unclear" only when nothing they said points to it. Applied over the picture by chat/picture.py.
class Reading(BaseModel):
    model_config = ConfigDict(extra="ignore", json_schema_extra=_tied_to_required)

    underneath: list[UnderneathEntry] = Field(
        description=(
            "Every feeling you read under the ones they named, across the whole conversation, each with the words "
            "of theirs it rests on. Usually one to three. Empty only when nothing they said supports a reading."
        ),
    )
    wants: str = Field(
        description=(
            "Everything they said they want, in their own words, from anywhere in this conversation, never from what "
            "you know of earlier ones unless they say it again here, including how "
            "they would like it to happen, such as \"closer friendships with my colleagues; to feel wanted without "
            "having to ask\". \"unclear\" only when they have said nothing about it."
        ),
    )
    reactions: list[str] = Field(
        description=(
            "What they do or how they react after it hurts, a few words each, from anywhere in the conversation, such "
            "as \"pretends it's no big deal\", \"overthinks how they act around them\", \"feels self-conscious\", "
            "\"holds back from asking\". Empty when they have said nothing about it."
        ),
    )
    needs: str = Field(
        description=(
            "What they need underneath what they want, your reading of this conversation, such as \"belonging and genuine connection\" or "
            "\"to feel close and chosen\". The need itself, never the way they would prefer it met: \"to be invited "
            "without asking\" is a preference and stays in wants, so one way is never treated as the only way. "
            "\"unclear\" only when nothing they said points to it."
        ),
    )
    desire: str = Field(
        description=(
            "The life or relationship they long for, your reading of this conversation, in a line, and any gap between it and what they "
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
    tied_to: list[TiedTo] = Field(
        default_factory=list,
        description=(
            "What their feeling may depend on, outside them and inside them, most relevant first: the one you would "
            "explore next comes first. Re-read every reply. Never what your picture holds as ruled out, and never what the "
            "note lists as already explored, in any words: the same person, event or worry counts as explored, unless "
            "their message reopened it. Empty when "
            "the feeling has no clear cause, or nothing they said points to anything yet."
        ),
    )
    core: str = Field(
        description=(
            "The belief their thoughts lead to, said to them as you, such as \"you might be settling for something "
            "that isn't fulfilling anymore\". Keep any distinction the conversation uncovered, such as feeling part of "
            "the team at work but not of their circle outside it. When they have said what they tell themselves, about themselves, their "
            "relationship, their life or their choices, there is a core: name it. \"unclear\" only when they have "
            "said nothing of the kind. It sits under their main concern, never under a 'should' or guilt about "
            "having the feeling while the feeling itself is still unexplained."
        ),
    )
    core_from: str = Field(description="The words of theirs the core rests on, quoted. \"unclear\" when the core is.")
    core_feeling: str = Field(
        description=(
            "The feeling under the core, your reading, one or two feelings when both are supported, such as "
            "\"inadequacy\" or \"insecurity and fear of rejection\". \"unclear\" when you cannot tell."
        ),
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
            "the feeling underneath. Never a more balanced way of seeing it: inside a set of questions, report a core "
            "only when they reveal a deeper belief under the one being looked at. Null otherwise."
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
    asked_for: str | None = Field(
        default=None,
        description=(
            "What they asked you to help with, in their words, when it is practical, such as \"how to bring it up "
            "with my boss without looking petty\". When they first ask or it changes. Null otherwise."
        ),
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
    ruled_out: list[str] | None = Field(
        default=None,
        description=(
            "What their message shows their feeling does not depend on: something you asked about or named that they "
            "say is not it, or does not matter to them, a few words each. Null when none."
        ),
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


# corrected (the client meeting, 2026-11-03): the offer says the core back, and they correct it there; Mani says the
# corrected reading back and may offer again sooner than after a no.
OfferAnswer = Literal["yes", "no", "asked", "moved_on", "corrected", "wants_other"]
CheckAnswer = Literal["yes", "no"]
BodyBranch = Literal[
    "yes", "no", "chest", "stomach", "head", "jaw_face", "hands", "eyes", "feet", "toes", "arms", "other",
    "nearest", "none", "pain", "better", "same", "worse", "helped", "somewhat", "not_really", "finish", "unclear",
]

# What a reply moves forward (muhammad, 2026-11-06: "make every question earn its place"): every turn should make at
# least one kind of progress, and code keeps what recent replies added so the next never adds the same.
ProgressKind = Literal["discover", "deepen", "belief", "connect", "need", "pattern", "insight", "toward_goal"]
# The parts of a person's experience a conversation can open (muhammad, 2026-11-06): what has been explored and what is
# worth exploring next, read after each reply.
Area = Literal[
    "emotion", "belief", "behaviour", "external", "outcome", "need", "attempts", "pattern", "relationships", "meaning",
    "function", "identity",
]


class Progress(BaseModel):
    """What this reply moves forward."""

    model_config = ConfigDict(extra="ignore")

    kinds: list[ProgressKind] = Field(
        default_factory=list,
        description=(
            "What this reply does that moves the conversation: discover (something not known before), deepen (a "
            "feeling or experience), belief (identify or clarify one), connect (a feeling to what is happening), need "
            "(a need, desire or conflict surfaces), pattern (they can see one), insight (a new way to see it), "
            "toward_goal (closer to what they came for). Empty when it only repeats."
        ),
    )
    adds: str | None = Field(
        default=None,
        description="What this reply adds that the conversation did not have yet, in a short line of your own words.",
    )

    @field_validator("kinds", mode="before")
    @classmethod
    def _known_kinds(cls, value: object) -> object:
        allowed = set(get_args(ProgressKind))
        return [v for v in value if v in allowed] if isinstance(value, list) else []


class NextArea(BaseModel):
    model_config = ConfigDict(extra="ignore")

    area: str = Field(description="One of the areas: emotion, belief, behaviour, external, outcome, need, attempts, pattern, relationships, meaning, function, identity.")
    why: str = Field(description="Why exploring it now would help them, in a short line.")


class Exploration(BaseModel):
    """What the conversation has explored of their experience, what is worth exploring next, and what Mani can infer
    but has not said (muhammad, 2026-11-06)."""

    model_config = ConfigDict(extra="ignore")

    explored: list[str] = Field(
        default_factory=list,
        description=(
            "The areas of their experience the conversation has really explored, not just touched: emotion (what "
            "they feel), belief (what they tell themselves), behaviour (what they do or avoid), external (what is "
            "happening around them, other people), outcome (what they want to happen), need (what they need "
            "underneath), attempts (what they have tried), pattern (whether it has happened before), relationships "
            "(how it touches the people close to them), meaning (what it says to them about themselves), function (what "
            "a behaviour does for them in the moment, such as relief, and so what keeps the pattern going), identity "
            "(what they believe it makes them, such as a 'bad son or daughter', and what being good means to them)."
        ),
    )
    next: list[NextArea] = Field(
        default_factory=list,
        description="Up to three areas worth exploring next, most useful first. Never one already explored.",
    )
    connections: list[str] = Field(
        default_factory=list,
        description=(
            "Up to three connections you can infer from what they said and have not said to them yet: between a "
            "feeling and something happening, a belief and what they do, inside and outside them. Each a possibility "
            "in a sentence, never a fact, never one already given."
        ),
    )

    @field_validator("explored", mode="before")
    @classmethod
    def _known_areas(cls, value: object) -> object:
        allowed = set(get_args(Area))
        return [v for v in value if v in allowed] if isinstance(value, list) else []

    @field_validator("next", mode="before")
    @classmethod
    def _known_next(cls, value: object) -> object:
        allowed = set(get_args(Area))
        if not isinstance(value, list):
            return []
        area = lambda v: v.get("area") if isinstance(v, dict) else getattr(v, "area", None)
        return [v for v in value if area(v) in allowed][:3]

    @field_validator("connections", mode="before")
    @classmethod
    def _few_connections(cls, value: object) -> object:
        return [v for v in value if isinstance(v, str) and v.strip()][:3] if isinstance(value, list) else []
# explore (the client meeting, 2026-11-03): a stage said back with something meaningful added, explored before the walk
# moves on, rather than a "yeah, yeah" through stages the chat already answered.
StageAnswer = Literal["agreed", "answered", "corrected", "explore", "stop", "not_yet"]
Heart = Literal["exploring", "core_named", "ready"]
# The three shapes of a chat reply (the client's test, 2026-10-29): acknowledge and ask openly while there is not enough
# to go on; open the window when a feeling is tied to something outside them; add the insight when there is enough.
# reflect (the client's review, 2026-10-29): now and then an acknowledgment and an observation that lets them go on,
# without a question, so the reply is not the same formula every turn. Never two in a row.
Shape = Literal["open_ask", "window", "insight", "reflect", "acknowledge", "practical"]
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
        "offer_answer", "check_answer", "heart", "body", "stage_answer", "framework_fit", "shape", "move",
        mode="before",
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
    safety: SafetyRead | None = Field(default=None, description=_SAFETY_DESCRIPTION)
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
            "Where your reading of the core of it stands, from the whole conversation including their message. exploring: you do not know the core yet, the belief the other thoughts lead to and the feeling underneath. core_named: you said the core back to them as an invitation and they did not correct it; carrying on or answering your next question counts, and it stays named unless they say that is not it. ready: it is named, and their message since confirmed it and brought nothing new that needs room. When their message deepens it, with something new or painful, it is core_named, not ready: stay with what they just said in this reply (the client meeting, 2026-11-05)."
        ),
    )
    offer_answer: OfferAnswer | None = Field(
        default=None,
        description=(
            "How they answered the offer in your last reply: yes, no, asked (about it, or what "
            "it involves), moved_on (they talked about something else), corrected (they said what the offer said "
            "back about them is not quite it, or changed it), or wants_other (they agree, but want something this set "
            "does not do, such as \"I just want to know why I feel so disconnected\" to a set that looks at a thought)."
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
            "How their message answers the stage in force. Judge it by whether what the stage asks is answered, never by "
            "how much they wrote: a full answer that also brings more is agreed or answered, and what it brings is "
            "carried into the next stage. agreed: yes to your check of what they said, with or without more added. "
            "explore: on a stage you said back, what they added leaves this stage's own question unclear, such as a "
            "second belief beside the first, with an update for it; the walk stays for one reply. answered: they gave what the stage needs, or picked one of "
            "your possibilities as theirs, with an update for it. corrected: a no with new words, with "
            "an update for it. not_yet: a plain no, unclear, unsure, I don't know, a question back about what you "
            "asked, or only part of what the stage needs, so the walk stays. stop: they clearly want to stop or leave the questions."
        ),
    )
    still_open: list[str] | None = Field(
        default=None,
        description=(
            "Only on the reply that ends the questions (next says the questions end): what they named that is still "
            "open for them, a few words each, such as a cost of the old belief they have not addressed or what they "
            "came for. Empty when nothing is. Null on every other reply."
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
    insight: str | None = Field(
        default=None,
        description=(
            "Only when this reply gives an insight, an aha they have not put together, earned by what they said: the "
            "insight in a sentence, as your reading. Never one you already gave (insights_given). Null otherwise."
        ),
    )
    explored_now: list[str] | None = Field(
        default=None,
        description="The ids from stage_explore this reply opens or that their message just covered. Null otherwise.",
    )
    progress: Progress | None = Field(default=None, description="What this reply moves forward.")
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


_CORE = ("safety", "reasoning", "picture", "text", "title")
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
        names = (names - {"reasoning"}) | {
            *_STAGES, *_REACH, "options", "framework_fit", "still_open", "insight", "explored_now", "progress",
        }
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
        description=(
            "Of tied_to, the one the feeling is most closely tied to: your question lands on it, with the feeling. "
            "When the note names one to explore next, it is that one, unless their message points elsewhere."
        ),
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


# What Mani reads of them after a chat reply has gone out (orchestrator.read_understanding): the whole reading and what
# their message adds to the picture. Asked for apart from the reply, after it is sent, because written before the text
# it was most of what the reply waited on and grew with the conversation, until a turn passed the chat deadline
# (Lolly's chats, 2026-11-03). The reply still reads the picture first: the note carries it as it stood before their
# message (muhammad, 2026-10-29, approach A: understanding before the text).
class ConversationUnderstanding(BaseModel):
    """Your reading of them and the picture, after their last message and your reply to it."""

    model_config = ConfigDict(extra="ignore", json_schema_extra=_reading_required)

    reading: Reading | None = Field(
        default=None,
        description=(
            "Your whole reading of them, re-read from the whole conversation including their first message, never "
            "only their last."
        ),
    )
    picture: PictureUpdate | None = Field(
        default=None,
        description="What their last message adds to or changes in the facts of your picture of them.",
    )
    exploration: Exploration | None = Field(
        default=None,
        description="What the conversation has explored, what is worth exploring next, and what you can infer but have not said.",
    )


# The reply whenever no framework, offer or check is open (orchestrator.converse). The model reads every
# description. What the turn calls for comes before the text, so the text follows from it.
class ConversationReply(_ReplyBase):
    """Mani's reply, and where the conversation stands after it. Your reading of them and the picture are in the note.
    Fill the fields in order: what this turn calls for, then the text, which follows from all of it."""

    safety: SafetyRead | None = Field(default=None, description=_SAFETY_DESCRIPTION)
    heart: Heart | None = Field(
        default=None,
        description=(
            "Where your reading of the core of it stands, from the whole conversation including their message. exploring: you do not know the core yet, the belief the other thoughts lead to and the feeling underneath. core_named: you said the core back to them as an invitation and they did not correct it; carrying on or answering your next question counts, and it stays named unless they say that is not it. ready: it is named, and their message since confirmed it and brought nothing new that needs room. When their message deepens it, with something new or painful, it is core_named, not ready: stay with what they just said in this reply (the client meeting, 2026-11-05). Say the core in this reply's text and it is core_named."
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
            "What kind of reply this turn needs, chosen from your reasoning, never by habit. open_ask: something you "
            "do not know and cannot infer would really change your understanding; one open question about a part not "
            "yet explored. window: a feeling is tied to something outside or inside them; ask about the feeling with "
            "what it is tied to. insight: there is a new connection to make, earned by what they said; never on your "
            "first reply; give it as your reading, with or without a question. reflect: something meaningful was said; "
            "an observation that lets them go on, with no question; never two in a row. acknowledge: something hard "
            "just came up; stay with it, with no question. practical: they asked for help or what to do; one small "
            "idea, then an offer to work it through together."
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
    progress: Progress | None = Field(default=None, description="What this reply moves forward.")
    plan: str | None = Field(
        default=None,
        description="Where this conversation is heading, one line: what you know, and what comes next toward the framework.",
    )
    text: str = Field(description="What Mani says to them, following from the fields above. Required.")
    core: str | None = Field(
        default=None,
        description=(
            "Once heart is core_named or ready: the core of it and the feeling underneath, one or two sentences said "
            "to them as you, the feeling underneath as your reading, such as \"One slip feels like proof that you can't "
            "change, and underneath the guilt there may be shame about who you are.\" Null otherwise."
        ),
    )
    checking: bool | None = Field(
        default=None,
        description="True only on the reply that moves to the set of questions, when the note allows it.",
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

# The client meeting (2026-11-03): no check of the summary before the framework. On a turn the note allows it, the
# reply may move straight to the set of questions: the client's offer says the core back, and they can correct it
# there. These fields exist only on that turn, filled before the text so the offer's slots are written first.
_TRANSITION = ("core", "checking", "heading_toward", "offer")


@functools.cache
def conversation_reply_for(*, may_move: bool, slots: Slots = Slots()) -> type[BaseModel]:
    """The chat's reply shape this turn: ConversationReply, and on a turn that may move to the set of questions, the
    set it heads toward and the offer's slots in this style. Without a template there is no offer to fill."""
    if not may_move or not slots.going_through:
        return ConversationReply
    lead = (
        "Your text is not sent when the offer is: its first line, in your words, takes its place."
        if slots.lead_line
        else "Your text goes before the offer, without its question: keep it to a short acknowledgment of their message."
    )
    overrides = {
        "checking": (
            bool | None,
            Field(
                default=None,
                description=(
                    "True only when this reply moves to the set of questions: then fill core, heading_toward and "
                    "offer. " + lead
                ),
            ),
        ),
        "heading_toward": (
            str | None,
            Field(
                default=None,
                description=(
                    "Only when checking is true: the id from the Framework Index in the note that fits the core best. "
                    "Null otherwise."
                ),
            ),
        ),
        "offer": (
            _offer_model(slots.going_through, slots.lead_line) | None,
            Field(
                default=None,
                description=(
                    "Only when checking is true: the set in heading_toward, for the core. The offer's words are the "
                    "client's: you fill only these parts, in their words. Null otherwise."
                ),
            ),
        ),
    }
    order = [n for n in ConversationReply.model_fields if n not in _TRANSITION]
    at = order.index("text")
    order[at:at] = list(_TRANSITION)
    fields = {
        name: overrides.get(name) or (ConversationReply.model_fields[name].annotation, ConversationReply.model_fields[name])
        for name in order
    }
    return create_model("ConversationReply", __base__=_ReplyBase, **fields)


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


class ProgressMemory(BaseModel):
    """What they worked through, carried into later conversations (muhammad, 2026-11-06): a layer of its own beside the
    patterns, so Mani builds on what they reached instead of starting from zero. Only what they said themselves, in
    their words: never Mani's reading of them, never a label. The fold replaces it whole, so what has changed is
    updated and what no longer holds is dropped."""

    model_config = ConfigDict(extra="ignore")

    realised: list[str] = Field(
        default_factory=list,
        description=(
            "A new way of seeing it they put into words themselves, such as \"I can appreciate my family without being "
            "available every time\". Never your interpretation of what lies underneath."
        ),
    )
    trying: list[str] = Field(
        default_factory=list,
        description=(
            "Something they said they would try, in their words, such as \"be honest when I need rest instead of "
            "automatically agreeing to help\". Drop it once they say it is done or no longer theirs."
        ),
    )
    working_on: list[str] = Field(
        default_factory=list,
        description=(
            "What they said is still hard or unchanged, such as \"sometimes I want to take back my no to make the guilt "
            "go away\". Update or drop it when they say it has changed."
        ),
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
    progress: ProgressMemory = Field(
        default_factory=ProgressMemory,
        description="What they worked through: what they realised, what they plan to try, what they are still working on.",
    )
