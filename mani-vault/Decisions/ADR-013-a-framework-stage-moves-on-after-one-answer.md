---
type: decision
status: accepted
date: 2026-10-04
apps: [backend]
tags: [decision, ai, frameworks, conversation]
---

# ADR-013: A framework stage moves on after one answer, with at most one counted extra turn

**Status:** accepted, 2026-10-04 (muhammad). He read one transcript per framework twice (spec 0003, AC-9 and AC-9a) and passed all six both times. The numbers are in [[stage-moves-on-holds-measured-2026-10-04]]. Open follow up work on redirects is listed in the spec.
Amends [[ADR-010-a-person-in-panic-is-guided-not-quizzed]] (its "cannot say" point: up to three options or a draft goes) and [[ADR-011-first-stage-by-its-own-test-and-one-draft-when-asked-to-pick]] (the draft step goes; the first stage's own readiness test stays). Spec: `docs/specs/0003-stage-moves-on-one-answer/`.
**Affects:** backend (`context.py`, `repairs.py`, `techniques.py`, `orchestrator.py`, `threads.py`, `llm/schema.py`, migration 011, the six framework files, `mani_base.md`, `response_format.md`)

## Context

The client found Mani quizzing: inside a framework the model decided when a stage was done and often asked the same question again in other words. Today's rules also told it to offer up to three options or a draft when someone said "I don't know". The full reasoning and the branch inventory are in the spec's `rationale.md`.

## Decision

The code moves the stage on before the model is called. After a reply, `[ctx]` shows the answered stage without its question and the next stage with its question, so there is nothing old to repeat. What the reply may record is the next stage, or a hold on the answered one. A lost or garbled state records the next stage too.

A stage may take at most one extra turn, counted in `thread_technique_state.holds`: saying a question again once in simpler words, offering one of the person's own options at a stage that picks among options, and DBT STOP's acting branches. A redirect (safety, a framework that does not fit, one of the client's lines) is not counted, and the code, not the model, recognises it: the reply, or Mani's message just before it, carries the words of a redirect branch of the answered stage or one of the client's three lines. A second counted hold records the next stage.

Stages whose question depends on an earlier answer carry an authored `if_earlier_missing` question. `ready_when` stays only on the first stage. ABCDE's `examine` and Thought Reframe's `facts` are each split in two.

## Consequences

- A repeated stage question is structurally hard: the old one is not in `[ctx]` and the record cannot go back.
- Every framework reaches the body check in a bounded number of turns. 54 of 54 real conversations did, with no hold limit reached.
- Later stages work with less. The authored `if_earlier_missing` question carries the framework when an answer never came. The client has not confirmed this trade.
- The model's own redirect mark was wrong in all 24 cases of the first measurement, so it was removed. A real redirect the model paraphrases is counted, and a second hold at that stage records the next stage. No scenario contains a real redirect yet, so how often the model quotes them is unmeasured, and ending the framework on a safety branch is open follow up work.
- Reversing: revert the commit, reseed, restart. The column can stay.

## Links

- Spec: `docs/specs/0003-stage-moves-on-one-answer/`
- Journal: [[stage-moves-on-design-2026-10-04]], [[stage-moves-on-first-real-runs-2026-10-04]], [[stage-moves-on-holds-measured-2026-10-04]]
