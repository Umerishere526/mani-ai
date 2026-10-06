---
type: decision
status: accepted
date: 2026-10-05
apps: [backend]
tags: [decision, ai, frameworks, conversation]
---

# ADR-015: What the person said before accepting a framework is not asked again

**Status:** accepted, 2026-10-05 (muhammad: "do whatever to fix it", no client sign off needed). One real replay of his chat read by him is still to come.
Amends [[ADR-013-a-framework-stage-moves-on-after-one-answer]] (the first stages can be skipped) and [[ADR-012-mani-speaks-plainly-and-tone-is-the-prompts-job]] (scripted phrases are redrafted once, in code).
**Affects:** backend (`techniques.py`, `context.py`, `repairs.py`, `redraft.py`, `orchestrator.py`, `router.py`, migration 012, the six framework files, `somatic.md`, `mani_base.md`)

## Context

A real Direct chat ([[idiot-concert-chat-why-mani-reads-as-a-worksheet-2026-10-05]]) had the person say "what?" three times and re-explain the event after "Try it". The cause was in structure, not tone: the stage questions were worksheet sentences that presupposed things ("It affected everything"), the facts the router had kept at the offer were thrown away so the first stages were asked again, a bare "what?" was not recognised as "I did not follow", and the rephrase was left to the model.

## Decision

- The router's kept facts, with the person's own words, are stored on the offered technique row (`known`). A stage names the fact that answers it (`answered_by`; ABCDE's `activate` is `event`, `belief` is `meaning`). On accepting, by tap or by a typed yes, an unbroken run of answered stages from the first is not asked: `[ctx]` shows `already_told` with the words, and the reply says them back in a clause and asks the first open stage. The stored stage is never earlier than that stage.
- Every stage question is one plain question with nothing presupposed, in all six frameworks, and every stage has an authored `ask_simpler`, which the model uses when the person says they did not follow. Offer descriptions are one plain sentence each. The body-check lines no longer name "anxiety".
- A bare "what?", "huh", "??" counts as not following.
- "It sounds like", "It seems like", "I hear you", "That makes sense" and "I am here with you" are a redraft reason in code (once, like the feeling words).

## Consequences

- A person who has told Mani the event and what it meant starts ABCDE at the consequence. Other frameworks are not yet mapped (`answered_by` is one line per stage).
- The stage questions no longer carry the client's lead-in sentences; styles now differ less in the questions themselves.
- One more redraft call when a draft uses a scripted phrase (measured: 3 extra calls in 12 turns on the replay).
- Reversal: restore the framework files and prompts from the commit before, `git revert`, reseed. The column can stay.
