---
type: journal
date: 2026-10-08
tags: [journal, offers, prompts, styles, client]
---

# The late offer was the prompt, not the code

muhammad's chat tester run, Direct style: the person gave the event and the feeling ("my manager pointed me out in front of the CEO", embarrassed) in the first message, and the Thought Reframe offer still came at turn 8. Mani even asked "Would it help to take a brief look at that thought?", got a yes, and kept asking.

## Cause

- Not the timing code. `clear_offer_after` was already 2, and `cooldown_passed` is only a hint that nothing enforces.
- The prompt. Thought Reframe's `Starts when` line wants the thought, the moment, why it matters **and** "they want a brief look". `mani_base.md` adds "Every question also reaches, unseen, for what the likeliest set needs to learn" and "If two fit, ask one question that tells them apart first". Each of these rules makes the model ask one more question.
- Tone. The Direct style line says "Start with what they feel". That made Direct restate the feeling every turn, which is Reflective behavior. The client's Direct leads: "Tell me what is happening right now."

## muhammad's rules from this (2026-10-08)

- Keep the guardrails. Removing code was never the fix.
- Reach the client's outcome by cutting and clarifying prompt rules, never by adding them. Rule bloat makes the model hallucinate.
- The offer shows `Framework: <name>`. This is against the client intro doc's "do not give them the name", and the client is to be told.

Scoped as Slice 5 (features 14, 15 and 16) in `docs/scope/scope.md`. The client's targets are in `docs/client-share-docs/`: offer in about 2 to 4 exchanges, one behavior list per style, no labeling, and three offer buttons.

Related: [[offers-follow-the-chat-build-2026-10-08]], [[stage-skip-blocked-by-its-own-gate-2026-10-08]]
