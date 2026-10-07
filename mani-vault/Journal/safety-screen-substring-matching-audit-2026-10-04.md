---
type: journal
date: 2026-10-04
tags: [journal, safety, audit, lessons]
---

# The safety screen fails both ways: what a production audit found

A read-only production-readiness audit on 2026-10-04 (branch `fix/abcde-framework-trigger`) probed
`mani.chat.safety.screen()` directly with ~75 phrasings. The full report is a claude.ai doc,
"Mani Backend — Production-Readiness Audit"; this note keeps the lessons.

## What was found by running the code, not reading it

- **Missed (returned none):** "I am suicidal", "I want to end it all", "I am going to hang myself",
  "I took 30 tablets", "I have the rope ready", "I have a gun", "my friend wants to kill himself",
  "I am about to go confront him with a knife", every non-English phrasing.
- **False permanent locks (returned crisis):** "I want to diet before summer" (substring `want to die`),
  "I would never kill myself", "I cut myself shaving", "this exam makes me want to kill myself".
- `test_safety.py` had no recall, negation or false-positive cases, so the suite was green throughout.

## Lessons

- A substring phrase list cannot reach acceptable recall for crisis language and over-fires on
  substrings at the same time. Only a probe run reveals that; reading the list looks reasonable.
- A model-reported crisis read only from the final draft can be erased by a redraft.
- The crisis lock lives on the thread, so "New chat" bypasses it.
- A second `pool.as_admin()` acquire while a turn holds its connection deadlocks the pool at
  `MAX_POOL_SIZE` concurrent turns; reproduced with a 1-connection pool.

## Open decision for muhammad

Whether a crisis should lock the thread (current) or move the user into a user-wide safety mode
with fixed approved text. Needs the client's clinical input, as do `CLARIFICATION`, `PROTOCOLS`
and `RESOURCES`, which are still empty.
