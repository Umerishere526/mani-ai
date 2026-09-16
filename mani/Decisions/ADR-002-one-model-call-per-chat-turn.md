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

That analysis predates the prompt-caching measurement. A live turn was measured at
**8,260 input / 195 output / 3,572 cached / 4,633 ms / exactly one provider call**. The
cached fraction is 43%, and it is 43% rather than higher only because two volatile layers
(`title_generation`, `techniques_used`) sit above the 3,070-token `response_format` layer
in `composer.py`'s fixed order and invalidate the prefix behind them.

The port's single largest win was collapsing ~21 provider calls per turn to one.
`tests/integration/test_turn.py::test_a_turn_costs_exactly_one_provider_call` asserts it.

## Options considered

### Option A — One call per turn, stage content in the `[ctx]` block

- Pros: keeps the invariant and its test. With the layer reorder the prompt projects to
  ~5,880 tokens at ~91% cached — roughly 530 tokens billed at full rate, *cheaper than
  today* while carrying three times the framework content. One round trip, so latency is
  unchanged. Framework selection stays measurable: the router question can be run as an
  **offline** eval against the routing set, which yields the accuracy number without
  paying for a second call in production.
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
Prompt caching does the work the router was meant to do on cost, and does it better —
because the expensive content is static and cacheable while the router prompt would not
have been. Adding a seventh framework stays a content change.

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
