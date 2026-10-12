---
type: journal
date: 2026-10-11
apps: [backend]
tags: [journal, backend, prompts, debugging, evals]
---

# Replay one turn against the real model by seeding the thread

A reply in the local ABCDE thread suggested a belief the person had not stated. Reading the stored
messages could not say why: the model's reasoning and stage ledger are not stored, only returned
with `AI_DEBUG_MODE`.

## What worked

Replaying the whole conversation diverged at once. The model did not offer on the first message this
time, so "Try it" arrived as plain text and the path was a different one. A conversation is not
reproducible by retyping it.

Seeding the thread was. Insert the first 11 messages verbatim, set `conversation_style`, and write the
`thread_technique_state` row the real thread had (ABCDE accepted, on the belief stage). Then send the
one message under test through `orchestrator.send` and read `turn.reasoning` and `turn.ledger`. Run it
in separate threads, nine times, and count. The reasoning said what the model was doing and why:
"offer one tentative thought ... and check whether it fits".

## What it found

The belief stage's boundaries forbid interpreting a belief "beyond what they said", which assumes a
belief exists. Nothing covered a person who has none, so the model filled the gap with the confirm
mechanism that only some stages' own lines allow. About 4 of 9 tries did it. One sentence in the stage
note, saying a person who is not sure is asked the same thing more easily and never handed an answer,
took it to 0 of 9. This is the fix [[measure-before-tuning-prompts]] asks for: counted before and after,
not judged from one run.

## Things to remember

- A regex that flags "supplies an answer" undercounts. It missed "Did you feel you had to keep working,
  or was it something else?". Read every reply when the number is small.
- The pool already registers a JSON codec. Seeding `prompt_options` with `json.dumps(...)` stores a JSON
  *string*, and the next read fails validation. Pass the list.
- `LLM_TIMEOUT_SECONDS` bounds silence between bytes, not total time, so a call can outlast it. Every
  provider call now also has a deadline of twice that (`client.DEADLINE_FACTOR`).
- A redraft discarded its call, so the stored reply linked to the first draft's cost row in about 12% of
  hosted turns. Find that kind of gap by counting rows that never got a link.

Related: [[stages-are-skipped-not-confirmed-2026-10-09]], [[disarm-where-text-enters-the-prompt-2026-10-11]].
