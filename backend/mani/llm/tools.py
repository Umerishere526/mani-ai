# ABOUTME: The one tool the model may call - picking the exercise that follows a framework.
# ABOUTME: Everything else in this service is structured output, never a tool call.

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class StartExercise(BaseModel):
    """Bound and forced on exactly one turn shape: a framework has just completed and at
    least one exercise names it. The model's only job is choosing which one fits - not
    deciding whether to offer an exercise at all, which the ordinary reply already does.
    """

    model_config = ConfigDict(extra="ignore")

    exercise_id: str = Field(
        description=(
            "The id of the exercise to offer, copied exactly from the candidate list "
            "given to you. Choose the one that best fits what the person just worked "
            "through."
        )
    )
