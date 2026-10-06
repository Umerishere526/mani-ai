---
type: journal
date: 2026-10-05
tags: [journal, frameworks, closing, somatic]
---

# A framework ends with a conclusion: what the build taught

Spec: `docs/specs/0007-framework-ends-with-conclusion/`. Decision: [[ADR-016-a-framework-ends-with-a-conclusion-and-the-body-check]]. Scope row 19.

**What muhammad wanted.** Two chats marked up on 2026-10-05 (ACT to a mother, ABCDE after a manager spoke in front of the CEO). The ending was a form question both times. He wanted the framework to conclude, say what they feel is okay, and go to the body check.

**What I pushed back on.** The first ending he suggested told the person to explain their situation to their manager and be with their mother. That chooses the action and value for them, which the ACT boundaries forbid. The second began "It sounds like" (banned in spec 0002), summarized the framework, wrote the balanced thought the person had said they could not find, and ended on another question. He accepted both objections. The conclusion confirms what the person decided or said and adds nothing of Mani's.

**Why it was small.** `repairs.with_the_check_in` already kept the model's reflection and replaced its question with the client's fixed body question, and the move `closing` to `somatic_checkin` was an ordinary move. Removing `closing` was the whole change, plus a conclusion note in `context._move_on_lines` and one rule change in `with_the_check_in` (drop every question sentence, not only the last).

**A trap.** Dropping the closing question would have made the shared "skip the body check when the answer names an action" rule fire on almost every ACT, Behavioral Activation, Problem Solving and DBT STOP ending. It had to go in the same change, or the body check would have stopped for four of six frameworks.

**A test lesson.** The integration tests read frameworks from the database, not from `content/`. Editing the files and running only the unit tests passed while the database still held the old stages. Re-seed before trusting an integration run.

**Not done, on purpose.**
- No real model run. The endings are unverified until the 27 conversation read (spec 0007 AC-8) runs, and muhammad has to say first (about 3.7 dollars of credit on 2026-10-05).
- The scenario `panic_somatic_once` now starts at DBT STOP `proceed`, but its turns were written for the old shape (an answer to the closing question first). Read it before trusting a real run.
- Two things in the chats are not in this change and sit in scope row 39: the "fairest to say" fallback question that fired at `balanced` after "yes" at `evidence_for`, and the ACT chat skipping `toward` then asking a second action question.
- The client has not been told the closing question is gone (their section 21). Add it to row 29's list.
