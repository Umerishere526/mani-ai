---
type: decision
status: proposed
date: 2026-10-06
apps: [backend]
tags: [decision, ai, frameworks, conversation]
---

# ADR-019: Mani follows the client's documents

**Status:** proposed, 2026-10-06 (muhammad chose each part; built under spec 0010; muhammad's live checkpoint in chat-tester, AC-14, is still to come).
**Affects:** backend (the prompts, `context.py`, `repairs.py`, `router.py`, `techniques.py`, `orchestrator.py`, the framework files, migrations 013 to 015)

## Context

The client said Mani is moving in a direction they do not want: it questions people rather than listening. Over the previous month every failure had been answered with a rule: word bans, question rules, redrafts (a second model call asking for the reply again), a fact list the model had to quote, fit tables, an owed offer, and a stage machine that moved by count. Each rule had its own ADR, so improving Mani meant arguing past them. Several contradicted the client's own example replies. On 6 October Lolly wrote that Mani may state a conclusion the person has already established, should never force a framework to completion, and must always move into the somatic check, whose answer is the signal of whether the conversation helped.

## Options considered

### Option A: loosen the rules one by one
- Pros: smallest change; code still catches a wrong framework choice.
- Cons: keeps the gates that produce the questioning; Lolly asks for judgment that a gate cannot express.

### Option B: the client's documents are the only conversation rules
- Pros: one source, matching what the client wrote; one model call a turn; about a hundred rules gone.
- Cons: a wrong or early framework choice is no longer caught in code.

### Option C: build the new rules beside the old behind a flag
- Pros: side by side comparison, instant rollback.
- Cons: two conversation layers while the client waits; nothing is deployed to protect; the comparison needs paid runs.

## Decision

Option B. Where the client's documents disagree, the newer wins: Lolly's email of 6 October 2026, the "Good, Acceptable, Bad Conversations" PDF, the style document, the six frameworks document. The client's spoken instructions from the October meeting count like a document (ADR-018 stays).

- The model judges whether and which framework to offer, from the selection table and distinctions in the prompt. Code refuses an offer only on their first message, under a safety concern, when the grief veto applies, within four messages of a decline, after a framework was finished in the thread, or while one runs.
- The offer is the style document's: Mani's own sentence, the style's permission question, **Yes, let's try it**, **Tell me more**, **I want to keep talking**.
- The model judges when a framework step is done and may move past steps already answered; code allows one more attempt per step and never a step back. A framework may end resolved, pivoted or stopped, and every ending goes to the somatic check.
- Mani may state an observation or conclusion when it could point to the person's own words as its basis, and checks only when it is inferring.
- No code enforces tone, and a turn is one chat model call (ADR-002).
- How the person feels after the somatic practice is stored in `public.framework_outcomes`.

Deleted with their rules: ADR-006, 007, 008, 011, 012, 013, 014, 015, 016 and 017, and specs 0002 to 0009 (muhammad, 2026-10-06). Git keeps them.

## Consequences

- The rules Mani follows are in one place and match the client's writing.
- Replies are one model call, so faster and cheaper.
- Framework choice and step completion rest on the model; a bad pick shows only in the evals, the call log's `decision` column and the checkpoint. The answer to a bad pick is the model or the prompt guidance, not a new gate.
- A step judged complete by mistake is skipped for good, since steps never move back.
- The safety flag code (spec 0004) and the model comparison runner (spec 0006) lose their documents; the code stays.
- Reversal: revert the branch that built spec 0010; the new table and columns are inert without the code.

## Links

- Spec: `docs/specs/0010-mani-follows-client-documents/index.md`
- Related: [[ADR-002-one-model-call-per-chat-turn]], [[ADR-018-a-stuck-person-is-offered-abcde]], [[ADR-010-a-person-in-panic-is-guided-not-quizzed]]
- Journal: [[stuck-yes-dropped-and-say-back-lost-2026-10-06]]
