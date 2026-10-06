---
type: decision
status: proposed
date: 2026-10-05
apps: [backend]
tags: [decision, ai, frameworks, router]
---

# ADR-014: A framework is chosen from facts the model states, and offered only when they fully fit

**Status:** proposed, 2026-10-05. muhammad accepted the design (spec 0005, including its update of the same day). It becomes accepted once both real model checks have been run and read: spec 0005's AC-15 (done, see the journal) and AC-17 (the re-check after full fits only).
Supersedes the owed closest fit of [[ADR-007-offers-follow-confidence-and-the-closest-fit-is-owed]]: no nearest offer is made at the fourth message or ever; clear offers from the second message, ADR-007's other half, stay. Keeps [[ADR-010-a-person-in-panic-is-guided-not-quizzed]]'s lost wallet case with Structured Problem Solving. Uses the one redraft of [[ADR-006-a-turn-may-be-redrafted-once]]; [[ADR-002-one-model-call-per-chat-turn]] is unchanged. Spec: `docs/specs/0005-framework-fit-from-stated-facts/`.
**Affects:** backend (`router.py`, `redraft.py`, `orchestrator.py`, `context.py`, `repairs.py`, `llm/schema.py`, `prompts/composer.py`, the six framework files, `mani_base.md`, `response_format.md`, `scripts/eval_replies.py`)

## Context

Framework choice rested on hand written phrase lists. Two chats on 2026-10-05 matched no phrase, and the closest fit owed at the fourth message (ADR-007) produced a guess: Structured Problem Solving for stress about work, parents and society before anything specific was named, and ACT for "I might have a panic attack", which the client's overview puts under DBT STOP. No code checked the model's choice against what the person said.

The first real runs of the facts design then showed the owed nearest offer still produced unearned offers: the stress chat got Structured Problem Solving as the nearest at the fourth message, and once ACT from general pressure marked as `cannot_control`.

## Options considered

### Option A — The model states facts, code applies the client's table (chosen)
- Pros: reads meaning, including "nothing named yet"; no new provider, storage or call; the choosing rules are tested from fake facts for free.
- Cons: rests on how well the model fills the checklist, which only a paid run measures; a mismatch costs a second call.

### Option B — An embedding router (muhammad's research)
- Pros: matches paraphrases; deterministic once embedded.
- Cons: topic, not the structure the client's table turns on; always returns a nearest guess; needs an embedding provider, storage and a tuned cutoff.

### Option C — Widen the phrase lists
- Pros: smallest change.
- Cons: fixes today's wordings, none of tomorrow's.

### Option D — A separate classification call
- Pros: isolated, easy to evaluate.
- Cons: a second paid call on every turn, against ADR-002.

On the closest fit, after the first runs: keeping it but never owed, accepting the nearest for named pressures, and stricter facts in code were weighed; full fits only was chosen (spec 0005, rationale).

## Decision

Each reply carries `facts`: ten ids from the client's selection table, each with the person's own words. A fact counts only when its words are in one of their messages (two words at least; the two "right now" facts only from their last two messages). Each framework file's `fits_when` names the fact sets that make it fit, and six ordered tie rules in `router.py` carry the client's distinctions; `about_to_act` is absolute, and `overwhelmed_now` puts DBT STOP above the reflective frameworks but not above a full Structured Problem Solving fit.

Only a framework the facts fully fit, the pick, is ever offered. A framework they only point to steers the question and is never offered; there is no "Try the closest fit". An offer that is not the pick is asked again once, with the right framework's own offer wording or a question about what is missing, and removed if the second draft still offers it. From the fourth message, a pick the model has not offered is asked for; nothing in `[ctx]` says an offer is owed. The phrase scoring is removed; the imminent action phrases and the never offer vetoes stay. DBT STOP takes the client's overview wording and a `panic` branch on each stage for someone panicked with no action named.

## Consequences

- Any wording that means an event, a thought or panic can reach the right framework; a vague chat keeps talking instead of being handed a guess.
- A chat whose facts never fully fit gets no offer however long it runs. The chats ADR-007's owed offer was written for (grief, an exam) now depend on the model marking `cannot_control`, or a practical problem with not knowing what to do.
- The model can still mark a fact loosely without any push; the plain meanings are the only defence, and AC-17 measures it.
- ADR-007's rule of three replies after Keep chatting, which applied only to the closest fit, goes with it; clear offers keep their two exchanges.
- The DBT STOP panic wording and the "not above Structured Problem Solving" rule are ours until the client signs them off (scope row 29).
- First drafts no longer see the offering stage's wording except for an action about to happen; it arrives with a redraft.
- Reversing: revert the commit, reseed, restart. Nothing is stored.

## Links

- Spec: `docs/specs/0005-framework-fit-from-stated-facts/`
- Journal: [[framework-fit-from-facts-design-2026-10-05]], [[framework-fit-from-facts-first-runs-2026-10-05]]
