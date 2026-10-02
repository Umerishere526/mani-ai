---
type: decision
status: accepted
date: 2026-10-01
apps: [backend]
tags: [decision, ai, prompts, conversation, frameworks]
---

# ADR-010: A person in panic is guided, not quizzed

**Status:** accepted by muhammad, 2026-10-01. Adds to [[ADR-007-offers-follow-confidence-and-the-closest-fit-is-owed]] and
[[ADR-008-every-reply-before-an-offer-asks-a-question]]; replaces nothing.
**Affects:** backend (`context.py`, `repairs.py`, prompts, Structured Problem Solving)

## Context

muhammad's lost wallet chat (cards, ID and cash gone, "panicking and anxious", Direct style, Structured
Problem Solving offered). The replies were better, and three things still failed:

1. After Try it, Mani asked "is this the specific problem you want to resolve?" of someone who had just
   described it.
2. In panic the person does not know what to do. "I don't know" got the same question again, in other words.
3. The cards were still active and nothing said to block them with the bank. Reporting to the police came late.

Two causes beyond the prompt. The context block handed the model the first stage's question to copy, and an
example in `mani_base.md` showed the answer being "checked back". And `registry.clamp` let a reply move only one
stage past the offer, so the first reply had to be the first stage's question.

## Options considered

- **Confirm what they said, then ask** (what it did). Costs a turn and reads as not listening.
- **Skip stages when they already answered.** Faster, but the client's flow is a sequence and the later
  stages exist to slow a panicking mind down. Not adopted.
- **Say it and move straight on, keep every stage, make each question easier.** Chosen.

## Decision

- **No confirmation.** The reply to Try it says their problem back in a clause and asks the second stage's
  question. The first stage counts as answered by what they already said. Several problems: ask which to begin
  with. Applies to every framework.
- **Cannot say.** At the first "I don't know" or "guide me" while choosing what to do, offer up to three
  realistic options, or a draft answer to accept or change, most urgent first. Never a longer list, never
  choose for them. Structured Problem Solving gained a branch for this at the problem, control, outcome,
  options and first action stages.
- **An unprotected, time critical risk** (cards still usable): name the protective step as a suggestion as
  soon as it is clear, pointing to who can do it (the bank, the police), then ask whether they have.
  Not general advice.

In code: on the turn a framework starts, `context.build` shows the first stage as answered with its question
withheld, and the second stage's question as the one to ask; `repairs.apply` allows that reply to report the
second stage. Every other transition is still one stage at a time.

## Consequences

- Measured on `lost_wallet_panic`, three runs, all styles: the confirmation question went from 9 of 9 replies
  after Try it, to 0 of 6 that reached it. The bank step arrives in the first or second reply in all runs.
  At the first "I don't know" Mani mostly narrows to the bank step; three options mostly came at "guide me".
  Prose rules did not move that further.
- This departs from the client's literal Structured Problem Solving example, where the first stage is always
  asked. **Tell the client.**
- The recorded stage can read `problem` when the question asked was the second stage's; the person never sees
  it.
- Reversing it: drop the shift in `context.build` and the `previous` rule in `repairs.apply`.

## Links

- Related: [[ADR-007-offers-follow-confidence-and-the-closest-fit-is-owed]], [[framework-files-what-the-model-actually-reads]]
