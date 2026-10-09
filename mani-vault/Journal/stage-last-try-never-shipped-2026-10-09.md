---
type: journal
date: 2026-10-09
tags: [journal, frameworks, stages, ledger, prompts, specs]
---

# stage_last_try was never built, though spec 0010 says it was

Found building spec 0010 task 3. The amended spec's *Prompt wording* says task 1 shipped the `[ctx]` line for `stage_last_try`; it did not. Task 1 only built `stage_ledger`, and the amendment dropped the original draft:

> stage_last_try: this is the last try at stage. If it is still not known after their message, leave it without a word and ask the next stage not known in this reply.

So AC-9 (send `stage_last_try: yes` on the last try, explained in `response_format.md`) clashes with AC-11 (neither prompt file gains a line) and with muhammad's rule that prompt changes cut, never add.

muhammad's call (2026-10-09): build the count, `passed` and the caps without it, then settle it in `/architect`. Settled the same day: `stage_last_try` is dropped and `stage_turn_cap` goes from 4 to 3. The turn that reaches the cap still asks the stage once more, as [[stage-ledger-design-2026-10-08]] warned, so a stuck stage is asked 4 times with no prompt line. The cost, from the cross check: the answer to that 4th ask cannot mark the stage known, and it counts as the next stage's first turn, so in a stall that runs on, the stage after a passed one gets 3 asks.

Changed the same day after muhammad's chat (thread f8449c64): the answer to that 4th ask is now judged. A passed stage turns `known` when a later reply says so, and a stage at the cap is never moved back, so the bound holds. It still counts as the next stage's first turn. See [[or-stage-read-as-two-halves-2026-10-09]].

Lesson: when a spec says "already shipped", grep for it before building on it.

Related: [[stage-skip-and-short-questions-scope-2026-10-09]]
