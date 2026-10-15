# ABOUTME: The JSON shape Mani must reply in, and the field descriptions sent with it.
# ABOUTME: Every description is prompt surface - the model reads them, so wording matters.

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
            "The stage this reply works on, from framework_stages in [ctx]: the first they have "
            "not yet answered or confirmed. One stage in a reply; a stage their words answer is "
            "said back and checked, not skipped. The closing and the body route are never skipped."
        )
    )
    accepted: bool | None = Field(
        default=None,
        description=(
            "Set to true when the user accepts a technique offer in free text "
            '(e.g., "yeah let\'s do it", "sure", "ok"), or asks for one they declined '
            "earlier in this conversation. Set to false when they decline an offer in free "
            "text, or carry on talking without answering it: that is Keep chatting. While an "
            "offer of yours is waiting for an answer, leave it null only when their message "
            "asks about that offer itself, such as what it involves or how it works, which "
            "keeps it open; anything else they say is false. On a turn with no offer waiting, "
            "leave it null."
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


class StageKnown(BaseModel):
    """One stage of the running framework, and what the conversation already holds for it."""

    model_config = ConfigDict(extra="ignore")

    stage: str = Field(description="The stage id, from framework_stages in [ctx].")
    known: str | None = Field(
        default=None,
        description=(
            "What they have already said, here or in the Conversation Context, that this stage "
            "asks for, in their own short words. Part of it is fine. Null when they have said "
            "nothing for it."
        ),
    )
    status: Literal["known", "partial", "confirm", "missing"] | None = Field(
        default=None,
        description=(
            "known: they have confirmed it, so you go on to the next stage. confirm: you have an "
            "answer for it, from what they said, and are checking it with them now. partial: they "
            "said some of it, so ask only for the gap. missing: they said nothing for it, so ask it."
        ),
    )
    met: bool | None = Field(
        default=None,
        description="Optional. True when status is known.",
    )

    @model_validator(mode="after")
    def _status_and_met_agree(self) -> StageKnown:
        """Either field may be given; the other follows, so a ledger is always read one way."""
        if self.status is None:
            self.status = "known" if self.met else ("partial" if self.known else "missing")
        self.met = self.status == "known"
        return self


class WorkingRead(BaseModel):
    """What Mani makes of the person so far, in slots, so no part of it can quietly drop out or
    be added between turns. Their own words where it says so; Mani's possibility where it says so."""

    model_config = ConfigDict(extra="ignore")

    situation: str | None = Field(
        default=None, description="What is happening, in their words. Null until they have said."
    )
    feeling: list[str] = Field(
        default_factory=list,
        description=(
            "The feeling words they used themselves, word for word, such as frustrated. Only "
            "words in their own messages. Empty when they have named none; never a feeling you "
            "think they have."
        ),
    )
    meaning: str | None = Field(
        default=None,
        description="What they have concluded or believe about it, in their words. Null if not said.",
    )
    since: str | None = Field(
        default=None,
        description=(
            "How long it has been going on, only as they said it, such as for months or since "
            "the new manager. Null when they have not said; never assume it is recent."
        ),
    )
    impact: str | None = Field(
        default=None,
        description=(
            "What it has changed or cost them, as they said: their hours, work, sleep, relationships, "
            "motivation. Null until they have said. Never the situation restated, and never an "
            "effect you assume."
        ),
    )
    response: str | None = Field(
        default=None,
        description=(
            "What they do about it, as they said, such as confront, take it on themselves, avoid "
            "it or keep chasing. Null until they have said."
        ),
    )
    wants: str | None = Field(
        default=None,
        description=(
            "What they hope for from this, in their words, such as for it to stop or to be "
            "understood. Null until they have said; never a goal you picked for them."
        ),
    )
    support: Literal["not_asked", "asked", "heard", "help"] = Field(
        default="not_asked",
        description=(
            "Whether they want to be heard or want help working it out. not_asked until you have "
            "put that to them. asked in the reply where you do, once and plainly, and never "
            "again. heard or help once their answer, or what they have plainly said, shows which."
        ),
    )
    underneath: str | None = Field(
        default=None,
        description=(
            "What you think may be going on beneath what they said, tying the feeling they named "
            "to what in their situation explains it. Your possibility, held loosely, and the size "
            "they gave it, so a hard week stays a hard week."
        ),
    )
    unknown: str | None = Field(
        default=None,
        description=(
            "The one thing you still need to know to tell whether you have it right, and the two "
            "readings it would decide between. Never a pairing you have already put to them."
        ),
    )

    @classmethod
    def stored(cls, value: str | None) -> WorkingRead | None:
        """The read as it was stored, or None when nothing was stored or what is there is not a
        read: a value written before the read had slots is plain text."""
        if not value:
            return None
        try:
            return cls.model_validate_json(value)
        except ValueError:
            return None


# The slots of the read that hold what they told Mani, in their words, as opposed to Mani's own
# possibility (`underneath`, `unknown`). Never asked for again, and never lost once said.
THEIR_SLOTS = ("situation", "meaning", "since", "impact", "response", "wants")


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
    heading_toward: str | None = Field(
        default=None,
        description=(
            "Choose before writing text: the id from the Framework Index that this "
            "conversation is most likely heading toward, or null when nothing has pointed "
            "anywhere yet. It decides which set you offer, and your questions may reach for what it still needs. Not shown to "
            "the user."
        ),
    )
    understanding_said: Literal["not_yet", "this_reply", "earlier"] | None = Field(
        default=None,
        description=(
            "Choose before next_move. Where you have said what you think is going on underneath "
            "what they told you - the pattern, the bind, what it costs them - offered as yours "
            "for them to correct. not_yet: no earlier reply of yours has said it. this_reply: "
            "the reply you are writing now says it, so they can confirm or correct it. earlier: "
            "an earlier reply said it and they have answered since. None of these count as "
            "saying it: their own last message in other words, a general line such as that "
            "sounds frustrating, a question on its own, or naming a feeling. Not shown to the "
            "user."
        ),
    )
    working_read: WorkingRead | None = Field(
        default=None,
        description=(
            "Fill before next_move. Not shown to the user. What you make of them so far, slot by "
            "slot. Where working_read is in [ctx], that is your read as of last reply: keep every "
            "slot it already has, change a slot only where what they just said changes it, and "
            "never start it over. The feeling they named stays in feeling for the whole "
            "conversation unless they take it back. When they have given you almost nothing, "
            "underneath is where what you know about people in their position does the work, "
            "held loosely."
        ),
    )
    describes_body_improvement: bool | None = Field(
        default=None,
        description=(
            "Whether the person's message you are replying to describes their body feeling "
            "better, lighter, calmer, or more at ease, without necessarily naming where - "
            "distinct from naming a specific place (chest/head/stomach/elsewhere), which is "
            "handled separately. Null when not applicable (no body route is active)."
        ),
    )
    questions_answered: int | None = Field(
        default=None,
        description=(
            "How many of the questions in the person's last message this reply addresses. 0 if "
            "their message asked something and this reply addresses none of it. Null when their "
            "message asked nothing at all."
        ),
    )
    next_move: Literal["ask", "acknowledge", "offer", "answer_request"] | None = Field(
        default=None,
        description=(
            "Choose before writing text, after understanding_said. ask: one question that would "
            "change what you understand of their concern. acknowledge: no question, only when any "
            "question here would be unreasonable. offer: a set fits and understanding_said is "
            "earlier, so you offer it in this reply. answer_request: they asked you for "
            "something, so you answer it in this reply. Never decided by how many messages have "
            "passed. Not shown to the user."
        ),
    )
    stages_known: list[StageKnown] | None = Field(
        default=None,
        description=(
            "Only while the questions run (active_framework is in [ctx]); null otherwise. Fill "
            "it before text. One entry per stage, in order, starting with the stage in force "
            "and stopping at the first that is not met. That stage is the one this reply works on, "
            "and state.step must name it: confirm says what you understand and checks it, partial "
            "asks only for what its known does not already hold, missing asks it. Not shown to the "
            "user."
        ),
    )
    text: str = Field(description="Your conversational response to the user. Required.")
    prompts: list[SmartPrompt] | None = Field(
        default=None,
        description=(
            "Tappable buttons, only where your instructions say: the Try it button when you offer "
            "a set of questions, and the choices at the end of one. Null everywhere else, open "
            "questions included. Each prompt has a \"label\" field (required). ONLY include "
            "\"technique\" field when INITIALLY ASKING if user wants to try a technique. Include "
            "\"library\" ONLY on a button that opens the library. Labels in USER voice. Three at "
            "most."
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
            "Set when the person shows a genuine safety concern - suicidal thoughts, an intent "
            "to self-harm, or a wish to die. This does NOT cut off the conversation; it flags "
            "the moment so the framework pauses and the reply stays with them. Do NOT set it "
            "for ordinary sadness or frustration, hopelessness or exhaustion (\"I can not do "
            "this anymore\"), physical pain or injury (\"I broke my arm\", \"I fell and hurt "
            "myself\"), or an ambiguous \"I need help\". For a physical injury, ask whether they "
            "have been able to get it seen to and how it is affecting them, then support the "
            "emotional side. For anything else ambiguous, ask one gentle question to learn "
            "whether they are in danger or hurting emotionally first. Set to null when there is "
            "no safety concern."
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
    techniques_tried: list[ExtractedTechnique] = Field(
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
