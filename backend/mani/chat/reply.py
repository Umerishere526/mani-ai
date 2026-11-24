# ABOUTME: The turn's one reply as the model fills it: its plan, people and events, what Mani says and gives, what
# ABOUTME: happens next, its safety judgment and notes. Field descriptions are what the model reads; they match mani.md.

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Safety(BaseModel):
    """The model's judgment of their message, which the kept pause rules read."""

    level: Literal["none", "unsure", "danger"] = Field(description="See Safety in your instructions.")
    about: Literal["themselves", "someone_else", "from_someone", "body"] | None = Field(
        default=None, description="Whose danger. Always filled when level is unsure or danger."
    )
    help_in_place: bool = Field(default=False, description="Someone who can help is with them now, or help is coming.")
    declined: bool = Field(default=False, description="They refused the help you offered for this danger.")
    symptom_now: Literal["yes", "no", "unsaid"] | None = Field(
        default=None, description="With about body: whether the symptom is happening right now."
    )
    still_there: bool = Field(default=False, description="Their message itself says the danger is still there, or that they are not safe.")
    why: str | None = Field(default=None, description="One short line on what you judged.")

    @model_validator(mode="after")
    def _says_whose_danger(self) -> Safety:
        """A worry with no kind could not be held to its kind's pause rule, so the reply fails and is asked for again."""
        if self.level != "none" and self.about is None:
            raise ValueError("about is required when level is unsure or danger")
        return self


class Question(BaseModel):
    """What the reply's question is for, decided before the words. Plain text, so an odd value never fails the reply;
    code reads `latest` and keeps `intent` beside the question it asked."""

    latest: str = Field(default="", description=(
        "Their latest message, in one word: answer, adds_more, asks_mani, frustrated (with you), wants_to_stop or other."))
    intent: str = Field(default="", description=(
        "What this reply's question is for: situation, feeling, belief, wants or step. none when it asks nothing."))
    why_now: str = Field(default="", description=(
        "One short line: why this question fits here, from what they just said and what you already know, or why "
        "this reply asks nothing."))


class Person(BaseModel):
    """Someone they spoke of in this conversation, kept as they put it so no detail moves to someone else."""

    called: str = Field(description="How they name this person, in their words.")
    relation: str = Field(description=(
        "Who this person is to them, only as they said it; unsaid when they haven't said."))
    told: str = Field(description=(
        "What they said about this person, in their words, under 25 words. Never your reading."))


class Event(BaseModel):
    """Something that happened, is happening or is coming, kept as they said it so past and upcoming never swap."""

    what: str = Field(description="What happened or will happen, in their words, under 20 words.")
    when: Literal["past", "now", "upcoming", "unsaid"] = Field(description=(
        "past when it already happened, now when it is going on, upcoming when it has not happened yet, unsaid when "
        "they haven't said."))


class Said(BaseModel):
    """What the reply gives them, kept so a later reply does not give it again. Plain text, so an odd move never fails
    the reply."""

    move: str = Field(default="", description=(
        "This reply's main move: acknowledge, reflect, reassure, highlight, summarize or help."))
    gist: str = Field(default="", description="What it gives them, in 8 words or fewer.")


class TurnReply(BaseModel):
    question: Question = Field(default_factory=Question, description="Your plan for this reply's question, before you write.")
    people: list[Person] = Field(default_factory=list, description=(
        "Everyone they have spoken of in this conversation, rewritten whole each turn from the list in the facts and "
        "their latest message. Change an entry only when they add to it or correct it. At most 8."))
    events: list[Event] = Field(default_factory=list, description=(
        "What happened, is happening or is coming, as they said it, rewritten whole each turn the same way. An upcoming "
        "event becomes past only when they say it happened. At most 10."))
    text: str = Field(description="What you say to them, exactly as they will read it.")
    said: Said = Field(default_factory=Said, description="What your text gives them.")
    action: Literal["none", "offer", "finish", "stop", "library"] = Field(
        default="none", description="What happens after this reply."
    )
    framework: str | None = Field(default=None, description="The id of the set you offer, only with action offer.")
    stage: str | None = Field(default=None, description="The stage whose question this reply asks, while a set runs.")
    safety: Safety
    notes: str = Field(description=(
        "Your private working notes for your next turn, under 100 words. People, events and what you said go in their "
        "own fields."))
    title: str | None = Field(default=None, description="Only when the facts ask for a title.")
    corrected: bool = Field(default=False, description=(
        "True when their latest message corrects something you said or understood about them."))
