---
type: decision
status: proposed
date: 2026-10-05
apps: [backend]
tags: [decision, ai, frameworks, conversation]
---

# ADR-016: A framework ends with a conclusion and the body check, not a question

**Status:** proposed, 2026-10-05 (muhammad chose each part; the real model read of the endings, spec 0007 AC-8, is still to come and he has to say before it runs).
Amends [[ADR-013-a-framework-stage-moves-on-after-one-answer]] (the stages with an earlier answer question go from 27 to 21, and "I don't know" no longer always moves on at two stages) and the client's completion question (section 21 of each framework specification).
**Affects:** backend (`context.py`, `repairs.py`, `somatic.md`, `mani_base.md`, the six framework files, the content and integration tests, `eval_conversations.yaml`, `eval_replies.py`)

## Context

Every framework ended on a question ("Is that something you could realistically do?", "How does that sit with you?") and only then asked about the body. Two chats on 2026-10-05 showed the cost: the ACT person had just said they would go to their mother and got a form question back, and the ABCDE person said "i don't know myself. i've lost my confidence" and got "Is there anything you would add?", the fallback used when an earlier stage has no answer. A shared rule also skipped the body check whenever the last answer named an action, which is almost every ending in four of the six frameworks (scope row 19).

## Decision

- The `closing` stage is removed from all six frameworks. The last question stage is followed by `somatic_checkin`, which now writes a short conclusion (one or two sentences in the person's own words, an optional line that what they feel is okay) and has code append the client's fixed body question. Every question sentence in the model's text is dropped first, so the body question is the only one.
- The conclusion may say back up to two things the person told Mani they know, in their words, and, when the last stage got no usable answer, that they do not have to settle it today. It never says what those things mean about them. muhammad chose this on 2026-10-05 over his own suggested ending ("one comment doesn't define your ability", "give yourself space to process"), which would have had Mani write the conclusion the person could not reach.
- ABCDE and Thought Reframe ask for the balanced thought as "what would you say is true about this?", not "a fairer way", after a person asked what fairer meant.
- The conclusion's rules live once, in the `somatic_checkin` purpose and boundaries: no advice, no action or value chosen, no feeling they did not name, no claim that it worked or changed, no summary, no "It sounds like".
- The body check is always asked. The rule that skipped it when the last answer named an action is gone.
- At ABCDE `balanced` and Thought Reframe `reframe`, a first "I don't know" uses the stage's one counted extra turn for "That is fine. What is one thing about this that you do know is true?". A second one ends the framework.

## Consequences

- No framework ends on a form question, and the "anything you would add" fallback cannot appear.
- The body check follows every framework, which is what the client's worked examples show.
- The conclusion is model written, so only a read of real conversations proves it; AC-3 is unverified until that read.
- The six per framework closing boundaries become one shared list.
- The client's completion question is gone and they have not been told. A local thread stored at `closing` loses its stage; nothing real depends on it.
- Reversal: restore the framework files, `somatic.md` and `mani_base.md` from the commit before, revert the two `context.py` and `repairs.py` changes, reseed.
