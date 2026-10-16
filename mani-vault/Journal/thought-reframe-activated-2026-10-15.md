---
type: journal
date: 2026-10-15
tags: [journal, frameworks, thought-reframe, offer, walk]
---

# Thought Reframe activated next to ABCDE

The client's Thought Reframe document (2026-10-15) brought Thought Reframe back from `paused/`. The file was
rewritten from the document, word for word, in `abcde.md`'s shape. Facts and decisions live in
`backend/PORT-STATUS.md` (Decisions in force) and `docs/client/requirements.md` (R16 and Conflicts).
This note is about what was learned.

## A second active set exposed five ABCDE-only assumptions

"Bringing a framework back is a content change" (the decision of 2026-10-13) was not true. All five
were in code that looked framework-agnostic:

- **The offer's slot description was global.** `repairs.slots_for` took it from the first set with
  a template, so Thought Reframe's thought would have been described to the model as ABCDE's feeling
  noun phrase. The fix was one offer object per set, keyed by id, instead of a combined description.
  Fable 5.1's review showed that a combined description lets one set's words render into the other's
  template, and logs it as a success.
- **The feeling fallback was global**, and it was already broken for ABCDE. The feeling is stored as
  an adjective ("frustrated"), so the fallback rendered "the thoughts behind frustrated". The test
  hid this by passing "your frustration", a value the schema never produces. Lesson: feed a fallback
  the value the real schema stores, never one that reads well.
- **With two sets and no `heading_toward`, there was no offer.** That still holds (spec 0006 AC-8),
  but now a filled slot also counts as the choice.
- **`_LETTER_LINE` knew only "A is for".** Model-written step lines are now dropped by data: the begin
  line, intros and titles, each sentence on its own. The first version compared whole lines and
  never matched the two-sentence begin line. A test caught it.
- **The body route's "acting skips the check-in" was shared**, and Thought Reframe's document forbids
  it. The skip rule moved from the check-in's `purpose` into the `acting` branch, so it can be left
  out of `[ctx]` for a set whose closing stage sets `check_in_required`.

## Not done, on purpose

- **"Acknowledge an answered step and move on."** Both documents ask for it. The walk confirms once,
  as decided for ABCDE on 2026-10-13. Moving on was tried on 2026-10-09
  ([[stages-are-skipped-not-confirmed-2026-10-09]]) and replaced
  ([[abcde-walk-owned-by-code-2026-10-13]]). It is a conflict for the client, not a silent choice.
- **No stop existed in either framework.** "I just want to talk" got a follow-up, then the next stage.
  Now `stage_answer` `stop` ends the run as declined.

## Unrelated, noticed

- `NextStage.gap`'s description still names only ABCDE's example ("challenge for dispute"). It is
  harmless, because the ids reach the model through `next_stage_if_unclear`.
- `docs/scope/scope.md` still describes ABCDE as the only active set. Leave it for `/sync`.
