---
type: decision
status: accepted
date: 2026-10-01
apps: [backend]
tags: [decision, ai, prompts, frameworks]
---

# ADR-007: Offers follow Mani's confidence, and the closest fit is owed by message four

**Status:** accepted by muhammad, 2026-10-01. Replaces the first offer cadence set by muhammad on 2026-09-24
(`FIRST_OFFER_AFTER`: Direct 2, Supportive 4, Reflective 4), which was a code comment and not an ADR.
**Affects:** backend

## Context

The cadence held Supportive and Reflective until the person's fourth message, whatever Mani had
learned. Measured over three runs of four scenarios, Mani was ready to offer at the second or third
message in most conversations: the code dropped 58% of Supportive and 33% of Reflective first
offers as too early, which left replies with no question. Two causes sat underneath:

1. **The context block lied.** With no framework yet offered it said `cooldown_passed: yes` on every
   message, so the model was told it could offer and the code then refused.
2. **Nothing owed an offer.** In the grief scenario the model leaned toward ACT on every reply, in
   every style, and never offered; only 1 of 3 runs offered at all.

The product wants Mani to steer from the first message and offer as soon as it is confident, with an
honest way out when no framework fits well: offer the closest, or keep chatting.

## Options considered

### Option A — Keep the style cadence and make Mani obey it
- Pros: it is the client's cadence. No behaviour change.
- Cons: forty to sixty per cent of Supportive conversations were ready earlier; more redrafts to
  hold the model back; no answer for grief.

### Option B — Mani's confidence opens the gate; the closest fit is owed at message four
- Pros: a confident offer comes at the person's second message in every style. A reply field,
  `offer_fit` (clear or closest), says which. Nothing fitting well still ends in an offer, labelled
  honestly, with Keep chatting beside it. The context block now tells the truth.
- Cons: Mani decides its own confidence. A floor of two messages and the existing vetoes (pain,
  grief, safety) are the only code limits on a clear offer.

### Option C — Router confidence only
- Pros: deterministic.
- Cons: the router is phrase matching and found nothing in the grief or exam chats.

## Decision

Option B. A clear offer is allowed from the person's second message in every style (urgent actions
still skip the wait). The closest fit is due at the fourth message: `[ctx]` says `closest_fit: due`,
the model offers it with `offer_fit: closest`, the button reads "Try the closest fit", and a
redraft asks once if the model does not. After Keep chatting a clear offer may return after two more
exchanges and the closest after three. An empty `offer_fit` means clear. Safety concern, the pain
question, the grief veto (`never_offer_when_said`) and the framework's own contraindications still
apply first. Amends [[ADR-006-a-turn-may-be-redrafted-once]]: a due closest fit is one more reason to
redraft.

## Consequences

- Measured over three runs of four scenarios, every style, 36 conversations: all 36 reached an
  offer (before: 10 of 21 in the earlier baseline, grief 1 of 9). First offers came at message 2 in
  21 of 36 and at 4 in 3 (the closest fit, marked with the new button). Redrafts were 7% of replies.
- The client's cadence is no longer a rule. If the client wants Supportive or Reflective held back, it
  is one number, `CLEAR_OFFER_AFTER`, and a style table can come back.
- A confident but wrong offer is possible and is the cost of the choice. The person can tap Keep
  chatting, and the closest fit says it is not a perfect match.
- Reversing it: restore a per style count in `context.cooldown_passed` and drop `offer_fit`.

## Open after acceptance

- This departs from the client's written cadence (about four rounds before an offer, Direct sooner).
  The client has not been told yet. Suggested: tell them, and ask them to read about five real
  Supportive and Reflective transcripts. Everything measured so far is timing and format; whether an
  early offer feels pushy to a real person is not measured.
- Practical problems only, early, was considered and not chosen; `CLEAR_OFFER_AFTER` is the one number
  that restores a delay.

## Links

- Amends: [[ADR-006-a-turn-may-be-redrafted-once]]
- Related: [[framework-files-what-the-model-actually-reads]]
