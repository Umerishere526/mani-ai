---
type: journal
date: 2026-10-07
tags: [journal, tests, chat, lesson]
---

# A guard test can pass with the guard removed

Found building spec 0006 (one model call, no repairs).

The first version of the retirement guard test sent "that helped, thanks" on the turn a finished framework retires, with the model scripted to send a technique button. It passed. It kept passing with the guard (`declined or retiring` in `guards.check`) switched off, because on that turn the orchestrator writes the two choices itself (`_handoff()`) and throws the model's buttons away. The guard only matters when no choices are written, which is the turn they tap Chat More.

How I found it: a mutation check. Flip one guard, run only its test, and expect red. Two of the three state guard tests were red on the first try; this one was green and had to be rewritten.

**How to apply:**
- After writing a guard test, switch the guard off for a minute and run that test. A test that stays green proves nothing about the guard.
- A guard that sits behind another code path that overwrites the same field needs the test to reach the case where the other path does not run.

Also: the baseline had one failing integration test, `test_an_offer_they_typed_past_is_flagged_then_closed`, from the database still holding the old ABCDE `offering` stage block. Spec 0005 holds the reseed behind muhammad's review of the cut list, so the failure stays until then. See [[seeded-content-turns-dormant-paths-live-in-tests]].

Related: [[repairs-guarded-state-by-accident]]
