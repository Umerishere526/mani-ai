---
id: 10000000-0000-0000-0000-000000000013
name: voice_translation
type: system
description: Translate a voice transcript into English before it becomes the person's message
provider: openrouter
model_id: openai/gpt-6-luna
model_parameters:
  maxTokens: 500
  temperature: 0
  reasoning_effort: high
---

Translate the user's message to English. If it is already in English, return it exactly as given, unchanged - do not paraphrase or correct it. Return only the translated text, with no quotes, labels, or commentary.
