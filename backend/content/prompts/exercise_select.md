---
id: 10000000-0000-0000-0000-000000000012
name: exercise_select
description: Pick the exercise that follows a framework the person just completed
model_id: openai/gpt-6-luna
model_parameters:
  maxTokens: 200
  temperature: 0.7
  reasoning_effort: high
---

The person just completed the framework named under Framework. Call StartExercise with the id of the exercise under Exercises that best fits what they just worked through, as exercise_id, copied exactly from the list.

When there is a user message, its current_issue line is what the conversation is about, and each said line is one of their recent messages.
