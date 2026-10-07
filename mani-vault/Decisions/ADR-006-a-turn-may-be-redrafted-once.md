---
type: decision
status: accepted
date: 2026-10-01
apps: [backend]
tags: [decision, ai, prompts, cost, safety]
---

# ADR-006: A chat turn may be redrafted once

**Status:** accepted by muhammad, 2026-10-01. Amends [[ADR-002-one-model-call-per-chat-turn]]; does not supersede it.
**Affects:** backend

## Context

[[ADR-002-one-model-call-per-chat-turn]] keeps a turn to one provider call and already allows one
retry when the reply does not parse. Three rules about what a reply may say turned out not to hold
when they were only lines in the prompt, and the code could only look at the draft afterwards:

1. **A feeling the person never named.** "That sounds incredibly stressful" reached someone who had
   not said stressed. The code check only wrote a log note, and its word list was a fixed few dozen.
   The specifications say Mani never introduces a feeling word the user did not use.
2. **An offer before the client's cadence allows it.** The model offered at the person's second or
   third message in 21 of 36 Supportive and 12 of 36 Reflective test conversations. The code dropped
   the offer, which left a reply that asked nothing.
3. **An offer what they said rules out.** Behavioral Activation was offered to someone whose dog had
   just died, though the framework's own guard names early grief. A prose rule did not hold.

Dropping or trimming in code is cheap but can leave a reply with no question, or no reply to give.
The model is the only thing that can write a better one.

## Options considered

### Option A — Keep one call, correct in code only
- Pros: the invariant holds exactly. No extra cost or latency.
- Cons: trimming a sentence can leave a reply that answers nothing; dropping an offer leaves a
  reply with no question. This is the state that was shipping.

### Option B — Redraft once, then correct what still fails
- Pros: the person reads a reply the model wrote with the reason in front of it. The second draft
  is told exactly which words or which offer to avoid. The code corrections stay as the backstop.
- Cons: a second call on some turns: about 5% to 7% overall. One more round trip of latency on those turns.

### Option C — Redraft until it passes
- Pros: strongest guarantee.
- Cons: unbounded cost and latency, and the second draft is the same model with the same habit.

## Decision

Option B. When a draft names a feeling the person has not used, offers a framework before the
cadence allows it, or offers one that the framework's `never_offer_when_said` phrases rule out, the
orchestrator asks the model once more, with one `rewrite:` line per reason in the `[ctx]` block
(`mani/chat/redraft.py`, `context.with_rewrite_notes`). A second draft that still fails is corrected
by `repairs.apply`: the offending sentence is dropped when a question survives, and a ruled out or
early offer is dropped.

The reasons are pure functions of the draft and the person's messages, so each is a unit test. New
rules of the same kind are a content change where they can be: a framework lists its own
`never_offer_when_said`.

## Consequences

- A turn is one provider call, or two. `test_a_turn_costs_exactly_one_provider_call` still holds for
  a draft that needs no redraft, and it was the reason ADR-002 existed; new tests pin the two-call
  cases.
- Measured on the same rule over saved eval conversations: 6.4% of replies named an unsaid feeling
  before (28 of 440), 0 of 130 after, with a redraft on about 5%.
- Cost and latency rise on the redrafted turns only. Measured after [[ADR-007-offers-follow-confidence-and-the-closest-fit-is-owed]]
  made the context block tell the model the truth about the offer gate: 13 redrafts in 180 replies
  (7%), 12 of them for feeling words. Before that fix it was 15%, mostly early offers. Watch
  `admin.llm_calls` for two chat rows within seconds on one thread; a rate above about 10% means
  the prompt, not the redraft, needs work.
- The rewrite line is part of the model's input on the second call only, never stored, like the
  rest of `[ctx]`.
- Reversing it: delete the redraft call in `orchestrator.py`; `repairs.apply` still corrects every
  case, at the cost of the replies this ADR describes.

## Decisions taken on acceptance

- The redraft stays whole: feeling words, early or repeated offers, offers a person's words rule out,
  and a closest fit that is due. It was not narrowed to feeling words and vetoes.
- The grief veto on Behavioral Activation stays as built: `never_offer_when_said` phrases (died, passed
  away, passed on, funeral, put to sleep, no longer with us, bereaved, bereavement, grieving, grief)
  anywhere in the conversation. Known edge: "died" also matches "my phone died". Revisit it with real
  transcripts, in particular whether a loss from long ago should still block.

## Links

- Amends: [[ADR-002-one-model-call-per-chat-turn]]
- Related: [[framework-files-what-the-model-actually-reads]]
