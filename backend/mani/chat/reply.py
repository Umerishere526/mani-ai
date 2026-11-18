# ABOUTME: The turn's one reply as the model fills it: what Mani says, what happens next, its safety judgment
# ABOUTME: and its own notes. Field descriptions are what the model reads, so they match mani.md's last section.

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Safety(BaseModel):
    """The model's judgment of their message, which the kept pause rules read."""

    level: Literal["none", "unsure", "danger"] = Field(description="See Safety in your instructions.")
    about: Literal["themselves", "someone_else", "from_someone", "body"] | None = Field(
        default=None, description="Whose danger, when there is any."
    )
    help_in_place: bool = Field(default=False, description="Someone who can help is with them now, or help is coming.")
    declined: bool = Field(default=False, description="They refused the help you offered for this danger.")
    symptom_now: Literal["yes", "no", "unsaid"] | None = Field(
        default=None, description="With about body: whether the symptom is happening right now."
    )
    still_there: bool = Field(default=False, description="Their message itself says the danger is still there.")
    why: str | None = Field(default=None, description="One short line on what you judged.")


class TurnReply(BaseModel):
    text: str = Field(description="What you say to them, exactly as they will read it.")
    action: Literal["none", "offer", "finish", "stop", "library"] = Field(
        default="none", description="What happens after this reply."
    )
    framework: str | None = Field(default=None, description="The id of the set you offer, only with action offer.")
    stage: str | None = Field(default=None, description="The stage whose question this reply asks, while a set runs.")
    safety: Safety
    notes: str = Field(description="Your private working notes for your next turn, under 150 words.")
    title: str | None = Field(default=None, description="Only when the facts ask for a title.")

    @classmethod
    def fallback(cls, text: str) -> TurnReply:
        """The fixed reply that stands in when no host answered: it judges nothing and keeps no notes."""
        return cls(text=text, safety=Safety(level="none"), notes="")
