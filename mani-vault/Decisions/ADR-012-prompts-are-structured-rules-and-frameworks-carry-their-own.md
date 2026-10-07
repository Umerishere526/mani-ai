---
type: decision
status: accepted
date: 2026-10-07
apps: [backend]
tags: [decision, ai, prompts, persona]
---

# ADR-012: The base prompts are structured rules, short, and frameworks carry their own

**Status:** accepted by muhammad, 2026-10-07. Phases 2 and 3 are done; phases 4 to 7 are still to do.
**Affects:** backend (`content/prompts/mani_base.md`, `content/prompts/response_format.md`, later the framework files,
`composer.py` and `context.py`)

## Context

Every reply call carried about 15,000 tokens of static prompt: `mani_base` 8,100, the generated Framework Index
3,000, `response_format` 2,500, the Reply schema 1,500. Much of it was prose, three full example conversations, and
instructions that contradicted each other: the Reflective style was told to name a sensed feeling as a question,
while the same prompt and the redraft in code forbid naming any feeling the person has not named. muhammad wants
the model to have room to write, a persona that holds the chosen style, therapeutic but a warm companion, neutral,
never labelling or advising unasked, and questions in plain everyday words that move the conversation.

## Options considered

### Option A: trim the prose in place
- Pros: smallest diff.
- Cons: keeps prose that is hard to audit line by line, and keeps every framework's rules in the shared prompt.

### Option B: structured rules, a short shared base, rules per framework
- Pros: each rule is one line that can be traced to its source; the shared base holds only what is common; a
  framework's own rules reach the model only while it is offered or running.
- Cons: a rule that only the prose held may be lost; measured before and after to catch that.

## Decision

Option B.

- `mani_base.md` and `response_format.md` are YAML keys and arrays, sent to the model as written. No new parser.
- Persona: "the judgment of a therapist with forty years of listening to people", never said to the person, never
  clinical. The client spec forbids the word.
- Questions only, with three advice exceptions kept: options when they cannot say, one small step when they ask
  Mani to pick (ADR-011), the protective step on a time-critical risk.
- Every line traces to the client spec, an ADR or journal decision, or the prompt before this change. The trace is in
  [[prompt-restructure-2026-10-07]]. Strings the code matches by text are not reworded.
- Each framework file will carry its own 7 to 8 `agent_rules` (phase 4). The model chooses among the six by meaning
  in the same reply call; the keyword router stays a hint (phase 5). No schema change for dialogue inside a
  framework (phase 6).

## Consequences

- `mani_base` went from about 8,100 to 2,900 tokens and `response_format` from 2,500 to 2,000; together about 10,600
  to 4,850.
- The size words that code does not redraft (a lot, so much, tough, carrying, the weight of) stay listed, because
  only the prose holds them.
- Prompt caching works on this provider: 92% of input tokens were cached in the first measurement. Content that
  moves into `[ctx]` leaves the cached prefix, so phases 4 to 6 weigh that.
- To reverse: reseed the previous files from git (`2b426f6`).

## Links

- Related: [[ADR-007-offers-follow-confidence-and-the-closest-fit-is-owed]], [[ADR-008-every-reply-before-an-offer-asks-a-question]],
  [[ADR-011-first-stage-by-its-own-test-and-one-draft-when-asked-to-pick]], [[prompt-restructure-2026-10-07]]
