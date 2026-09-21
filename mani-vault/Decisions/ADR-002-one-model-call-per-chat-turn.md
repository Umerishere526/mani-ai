---
type: decision
status: accepted
date: 2026-09-16
apps: [backend]
tags: [decision, ai, prompts, cost]
---

# ADR-002: One model call per chat turn

**Status:** accepted
**Affects:** backend

## Context

Six specification documents define a conversational product far richer than what ships:
six therapeutic frameworks each specified per stage, three conversational styles with a
tonal variant at every stage, pacing rules, a somatic check-in, and a safety layer.
Concatenating that content naively is roughly 25,000 tokens per turn against a measured
8,260 today.

A stage-scoped prompt needs to know the stage. When a framework is running the database
knows it (`public.thread_technique_state`). At the moment of *selection* nothing does —
that is a judgement about the conversation. [[conversational-architecture]] §3, as written
on 2026-09-15, concluded that the decision must therefore precede generation, and proposed
**route-then-speak**: a small structured call that decides, then a second call that writes.

What the system prompt costs today is known exactly. The three layers every chat turn
carries measure 33,507 characters in `admin.prompts` — `mani_base` 8,923,
`techniques` 10,960, `response_format` 13,624 — which is **~8,380 tokens at 4 characters
per token**, before history, the `[ctx]` block or the user's message.

What it costs *after caching* is not known. `admin.llm_calls` holds two rows, byte-identical
at 8,230 in / 385 out / 4,200 ms, which is the scripted model in the integration tests rather
than a provider. **`cached_input_tokens` is 0 on both, and no live turn has ever been
recorded.** The plumbing is correct — `llm/client.py:205-210` asks OpenRouter for
`usage: {include: true}` and reads `prompt_tokens_details.cached_tokens` — so the field is
blind only because nothing has exercised it. The model is `google/gemini-3-flash-preview`.

This decision therefore rests on token *arithmetic*, which is verifiable, and not on a cache
hit rate, which is not yet. See Consequences.

The port's single largest win was collapsing ~21 provider calls per turn to one.
`tests/integration/test_turn.py::test_a_turn_costs_exactly_one_provider_call` asserts it.

## Options considered

### Option A — One call per turn, stage content in the `[ctx]` block

- Pros: keeps the invariant and its test. One round trip, so latency is unchanged. The
  prompt projects to ~7,900 tokens on a free-conversation turn and ~8,530 in-framework
  against ~8,380 today — **flat on raw tokens while carrying three times the framework
  content**, with ~7,650 of it in a static prefix that is cacheable where today's is not.
  Framework selection stays measurable: the router question runs as an **offline** eval
  against the routing set, which yields the accuracy number without paying for a second
  call in production.
- Cons: the turn on which Mani *offers* a framework is composed from a compact framework
  index plus activation conditions, not from full stage content. Selection quality rests
  on that index being good enough.

### Option B — Route then speak, two calls

- Pros: the generation prompt is stage-scoped at the moment of selection. The router is
  testable in isolation, and wrong framework selection is the highest-consequence failure
  this product has.
- Cons: a ~800-token router prompt falls below the 1,024-token minimum cacheable prefix
  the providers behind OpenRouter enforce, so it is billed **100% uncached on every
  turn**. Adds a full round trip to every turn — including framework-active turns, where
  the stage is already known from the database and the router's only job is "is this stage
  complete?". Breaks the one-call invariant and re-introduces variable per-turn call
  counts, which is the failure mode the port existed to remove.

### Option C — Router only when no framework is active

- Pros: pays for the second call only on the turns that need a judgement.
- Cons: per-turn call count becomes a range rather than an equality, so the invariant test
  degrades from an assertion to a bound. Adds a branch to the one path in the service that
  must stay easy to reason about.

## Decision

**One model call per turn.** Framework content is carried in the volatile `[ctx]` block on
the final user message, resolved from persisted state, not in the system prompt. Framework
selection is guided by a compact framework index in the cached static prefix, and its
accuracy is measured offline rather than by a runtime router call.

## Consequences

**Makes easy.** The invariant test stays an equality. Latency stays at one round trip.
Adding a seventh framework stays a content change.

**Robust to the open question.** The decision does not depend on caching working. If it
works, one call is far cheaper than two, because the expensive content is static and
cacheable while an ~800-token router prompt could never be. If it does not work, one call is
*still* cheaper than two, because two prompts are strictly more tokens than one. The cache
question changes how much the three-zone reorder in
[[conversational-architecture]] §3 is worth; it does not change the turn shape.

**Makes hard.** The offering turn has less context than a two-call design would give it.
If routing accuracy on the eval set proves unacceptable, the fix is not free.

**Accepted cost.** Selection quality on the offering turn depends on the framework index
and `activation_conditions` being well written. `admin.frameworks.activation_conditions`
exists, is seeded, and today reaches no prompt at all — wiring it is part of the work.

**Reversal path.** Option C is the fallback, and it is cheap to reach: the router prompt
already has to exist as an offline eval, so promoting it to a runtime call on `converse`
turns is wiring, not design. Take that step only if the eval says the index is not enough,
and change the invariant test to a bound in the same commit so the regression stays
visible.

## Links

- Supersedes the two-call proposal in [[conversational-architecture]] §3
- Related: [[2026-09-14-architecture-decisions]] #5 (no streaming in v1), [[ADR-001-project-knowledge-lives-in-two-places]]
