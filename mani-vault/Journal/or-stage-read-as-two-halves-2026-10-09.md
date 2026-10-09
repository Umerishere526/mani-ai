---
type: journal
date: 2026-10-09
tags: [journal, frameworks, stages, ledger, prompts]
---

# A stage worded "felt or did" was graded as two halves

In muhammad's chat (thread f8449c64), ABCDE's C read "how it affected what they felt or did". The model got "depressed and anxious" and reported `consequences` partial three times running, hunting for the "did" half, until the cap passed it. The client's C is feelings **or** actions (`backend/docs/specs/framework-abcde.md`), so one was enough.

How it was found: `admin.llm_calls.reported_stages` for the thread, one row per turn, shows exactly when and how the model graded each stage. Read it before guessing.

Fix: cut C's line to "how it affected them". There are no halves left to hunt for. D stays two-sided on purpose: the client wants for and against.

Lesson: in a Stages line, a list joined by "or" reads to the model as a list of things to collect. If any one item is enough, name the whole instead of listing its parts.

Related: [[stage-last-try-never-shipped-2026-10-09]], [[stage-ledger-design-2026-10-08]]
