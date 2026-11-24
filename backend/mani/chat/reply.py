# ABOUTME: The turn's one reply as the model fills it: its plan for the question, what Mani says, what happens next,
# ABOUTME: its safety judgment and its own notes. Field descriptions are what the model reads, so they match mani.md's last section.

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


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


class TurnReply(BaseModel):
    question: Question = Field(default_factory=Question, description="Your plan for this reply's question, before you write.")
    text: str = Field(description="What you say to them, exactly as they will read it.")
    action: Literal["none", "offer", "finish", "stop", "library"] = Field(
        default="none", description="What happens after this reply."
    )
    framework: str | None = Field(default=None, description="The id of the set you offer, only with action offer.")
    stage: str | None = Field(default=None, description="The stage whose question this reply asks, while a set runs.")
    safety: Safety
    notes: str = Field(description="Your private working notes for your next turn, under 150 words.")
    title: str | None = Field(default=None, description="Only when the facts ask for a title.")
    corrected: bool = Field(default=False, description=(
        "True when their latest message corrects something you said or understood about them."))
