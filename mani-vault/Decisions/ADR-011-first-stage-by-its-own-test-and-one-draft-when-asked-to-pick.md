---
type: decision
status: accepted
date: 2026-10-01
apps: [backend]
tags: [decision, ai, prompts, conversation, frameworks]
---

# ADR-011: The first stage is judged by its own test, and a request to pick gets one draft

**Status:** accepted by muhammad, 2026-10-01. Amends [[ADR-010-a-person-in-panic-is-guided-not-quizzed]] (its first point) and
[[ADR-006-a-turn-may-be-redrafted-once]] (a repeated question is a reason to redraft).
**Affects:** backend (`context.py`, `redraft.py`, `orchestrator.py`, prompts, Behavioral Activation)

## Context

muhammad's chat of 2026-10-01 (someone comparing themselves with others online, Behavioral Activation, Supportive).
It went well until Try it, then:

1. Mani asked "why does getting back to doing things that feel productive matter to you?" The person had named a
   wish, not an activity, so the stage that asks what they have stopped doing was not answered. ADR-010 had
   made the first stage count as answered after Try it, and the model skipped it. The question that fit was
   "what things would you want to do to be more productive?"
2. "Yes, they do, what should I start with?" was read as a bare yes. The reply ignored the question inside it.
3. "Not sure, can you pick one for me" and "yes, but what should I start with?" each got the same three
   options back, reworded. Nothing at runtime noticed a repeat.

## Decision

- **First stage, by its own test.** The turn they say yes, the context block shows the first stage in full
  (question and `ready_when`) and the second stage's question. If what they said meets `ready_when`, Mani says
  it back and asks the second stage's question; if not, it asks the first stage's question built from their
  words. The reply may report either stage.
- **A request to pick gets one draft step.** Mani names one small step, from what they already told it, with a
  few words why, and asks whether it works or they would change it. Only for how small a step is or which of
  their own options to try first, never for what matters to them or which problem is theirs. Every framework;
  Behavioral Activation's choose stage says so.
- **A yes with a question inside** is answered first, then Mani goes on. Prompt rule.
- **A repeated question is redrafted once.** `redraft.repeats` compares the closing question's words (four
  letters or more) with the previous reply's; 0.7 of the shorter one's words in common counts as a repeat.
  The redraft is told to answer what they said, and if they asked Mani to choose, to offer one draft step.

## Consequences

- Measured on the chat, three runs, all styles: after Try it, the first question asked for specific things
  they had stopped doing (7 of 7 in the last runs), and a request to pick got one draft in 4 of 6 runs
  (the others offered a short list once, then a draft). Wallet chat, 5 starts: one asked for the problem
  again, from 9 of 9 before ADR-010. That is the price of judging readiness instead of always skipping.
- A scripted test model that repeats one reply now triggers redrafts; the tests give each reply its own question.
- Two to three redrafts on turns where the model stalls; watch the rate (ADR-006's line is about 10%).
- Reversing it: drop `last_mani_text` in `orchestrator._why`; the prompt rules still stand.

## Links

- Amends: [[ADR-010-a-person-in-panic-is-guided-not-quizzed]], [[ADR-006-a-turn-may-be-redrafted-once]]
