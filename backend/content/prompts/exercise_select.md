---
id: 10000000-0000-0000-0000-000000000012
name: exercise_select
type: system
description: Pick the exercise that follows a framework the person just completed
provider: openrouter
model_id: openai/gpt-6-luna
model_parameters:
  maxTokens: 200
  temperature: 0.7
  reasoning_effort: high
---

The person just completed the framework named under Framework. Call start_exercise with the id of the exercise under Exercises that best fits what they just worked through.
