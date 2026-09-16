---
id: 10000000-0000-0000-0000-000000000009
name: summarization
type: system
description: Compress old messages for context continuity
provider: openrouter
model_id: openai/gpt-oss-120b
model_parameters:
  temperature: 0
  maxTokens: 500
---

# Task

Summarize the conversation for context continuity.

# Include

- Key emotional states expressed
- Specific situations or events mentioned
- Decisions or realizations the user had
- Support approaches that worked or didn't
- Overall conversation arc

# Exclude

- Mani's responses verbatim
- Minor back-and-forth details
- Redundant information

# Format

Single paragraph, under 1000 tokens, third person ("The user discussed...").

# Messages

{{messages}}
