---
type: decision
status: proposed
date: 2026-10-05
apps: [backend]
tags: [decision, ai, frameworks, conversation]
---

# ADR-018: A person who stays stuck is offered ABCDE

**Status:** proposed, 2026-10-05 (built; the real model run, shared with spec 0008's AC-9 as nine conversations, is still to come and muhammad has to say yes before it runs).
Amends [[ADR-014-a-framework-is-offered-only-when-the-facts-fit]] (a new fit set, counted below every other) and [[ADR-017-questions-are-asked-plainly]] (the stuck check may now lead to an offer).
**Affects:** backend (`router.py`, `techniques.py`, `context.py`, `orchestrator.py`, `redraft.py`, `composer.py`, `abcde.md`, `mani_base.md`, `eval_replies.py`, `eval_conversations.yaml`)

## Context

In the October 2026 meeting the client said a person in pain who keeps answering "I don't know" or "I can't think", or loops, should be offered ABCDE so its steps can guide them. Under ADR-014 nothing could be offered to that person: ABCDE needs an event and what they made of it, and a bare "I don't know" makes no fact. The client's written overview lists "stuck" under Behavioral Activation, so the meeting and the documents disagree. Spec 0009 holds the options and reasoning.

## Decision

- A new fact, `stuck`, reported by the model with the person's words. Code keeps it only once one of Mani's recent messages asked "Are you feeling stuck?" (matched after `normalize`).
- ABCDE's `fits_when` gains `[stuck]`. A set holding `stuck` fits only when no other set fits, so a painful thought still gets Thought Reframe and an action about to happen still gets DBT STOP. `Fit.stuck_route` marks such a pick.
- On the turn right after the check, ABCDE's offer lines and its `stuck` branch go into `[ctx]`, gated like DBT STOP's (no framework running, earliest message, not ruled out). The redraft's offer guidance uses the same branch.
- With `stuck` known and no event, ABCDE passes over "What happened?" with nothing said back (`techniques.passed_over_stages`) and asks "What goes through your mind when you feel this?" through `belief`'s `stuck` branch, tapped or typed.
- Pain in the body does not hold back a due offer on the stuck route (muhammad's call, against my advice); every other offer keeps the hold. `pain_mentioned` now matches whole words, so "painful" no longer holds offers back.
- No migration, no new model call.

## Consequences

- A stuck person gets a guided set of questions once they confirm they are stuck.
- It rests on a spoken instruction that contradicts the client's overview; the client is asked to confirm it in writing.
- A person whose only stuck answers were one word ("idk") cannot produce a valid quote, so the check can be answered yes with nothing offered.
- ABCDE can be offered to someone whose pain is a medical problem not yet seen to; the safety screen covers emergencies only.
- Reversal: drop `[stuck]` from `abcde.md` and reseed; the rest is inert without it. Revert the two `mani_base.md` lines.

## Links

- Spec: `docs/specs/0009-stuck-person-offered-abcde/index.md`
- Related: [[ADR-014-a-framework-is-offered-only-when-the-facts-fit]], [[ADR-015-what-the-person-said-before-accepting-is-not-asked-again]], [[ADR-017-questions-are-asked-plainly]]
- Journal: [[questions-easy-to-answer-old-mani-chat-2026-10-05]]
