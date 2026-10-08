# ABOUTME: The one tool the model may call - picking the exercise that follows a framework.
# ABOUTME: Everything else in this service is structured output, never a tool call.

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


# Bound and forced on exactly one turn shape: a framework has just completed and at
# least one exercise names it. The model's only job is choosing which one fits - not
# deciding whether to offer an exercise at all, which the ordinary reply already does.
# What exercise_id means is said in exercise_select.md.
class StartExercise(BaseModel):
    model_config = ConfigDict(extra="ignore")

    exercise_id: str
