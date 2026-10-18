---
type: journal
date: 2026-10-14
tags: [journal, abcde, stages, schema, lessons]
---
> Superseded 2026-10-17 (a stage's judgement is its parts, `next_stage` reports parts, not a status and gap) — see [[stage-contract-parts-2026-10-17]]

# The stage the walk reaches is judged in its own field (2026-10-14)

muhammad's Directive run (thread 4b93d612): Mani asked C, D and E with the client's fixed questions, word
for word. "What Mani knows" already held the feeling "frustrated". The person had also said what
supports the belief: deadlines slip and everything falls on them. This was the fifth round of "asked
again though said" (see [[transcript-is-the-memory-2026-10-13]]).

## Cause

- **The instruction excluded the evidence.** The reach was scoped to "what they have said … since the
  check they confirmed". In this thread the feeling was message 1, and the evidence also came before
  the check. The check has no feeling part, so a feeling said early was out of scope in almost every
  thread. Nothing recorded why the clause was there. The client's ABCDE document says the opposite:
  "Use what the person has already shared".
- **Why this class keeps coming back.** The reach was an optional entry in `stage_updates`, which also
  carried the stage in force and corrections. Leaving it out was the default ("report nothing: its
  question is sent for you"). It also depended on the model predicting the move: `_TWO_TRIES` said
  "unless stage_ready_when says to stay" while code moved anyway. And in the logs, "never judged"
  looked the same as "judged missing", so every round was found by reading transcripts.

## What changed

- **`next_stage` is a field of its own.** It is filled before the text on every turn that can start
  or move the walk. Its status is known, possible, partial with a `gap`, or missing. It is applied
  only when the walk moves, and it is judged from everything they said about the confirmed issue,
  before or after the check.
- **"reach unjudged" is logged.** A null `next_stage` on a move goes into the reply checks, so
  `scenario_check.py` counts it.
- **`reached_reported` is gone.** Every reach is now one that `[ctx]` told the model about, so the
  model's text is used when it asks something.
- **Prompts were cut and clarified.** "since the check", "unless stage_ready_when says to stay" and
  "your text is not sent" are gone. The client's tail on "I don't know" is restored.

Reviewed twice by Fable 5.1 (the architecture reviewer). The second review caught real gaps:
- A's `possible` status;
- that the closing has no next content stage;
- an E floor I had proposed, which contradicted the client.

## Lessons

- A judgement that code depends on must never default to omission. Make "nothing" an explicit value,
  and log "not judged" apart from "judged nothing".
- When a prompt rule restricts what the model may use, grep for its reason. If there is none, check
  it against the client's document before trusting it.
- Prompt text and code must agree on what happens next. A model told it may stay will write for
  staying.

Still open: a live run of `frustrated_work_full` and `overtime_full` in three styles (muhammad's yes, spends
credits). Watch for a second-try reply that writes a stay follow-up although the walk moves.
