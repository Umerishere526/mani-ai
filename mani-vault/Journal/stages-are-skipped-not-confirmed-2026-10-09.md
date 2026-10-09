---
type: journal
date: 2026-10-09
tags: [journal, frameworks, stages, dialog-management]
---

# A stage the conversation already answers is skipped, never confirmed

muhammad's rule: inside a framework, if what the person has said already answers a stage, skip it
with no "is that right?" and no mention, and do the same for the next stage and the next. A tap on
Not sure skips the stage outright.

Before this, `context._ALREADY_TOLD` told the model to check an answered stage with them once, and
`Registry.validate_transition` refused any forward jump over more than one stage (it clamped back to
the next one), so a person who had said everything in their first message still walked every stage.

What changed, and where each part lives:

- Which stages are answered is a semantic judgement, so it stays with the model. `[ctx]` now gives
  it the material: `later_stage` blocks (ready_when plus the style's ask) for every stage after the
  next, up to the closing. About 1.2 to 1.6 thousand characters per turn across the six frameworks.
- What may never be skipped is code: `Framework.may_skip` (the closing and the body route stay).
  `clamp` lands a jump over them on the closing.
- Not sure is a code-set button on a skippable stage question (`repairs.apply`). The tap becomes
  `stage_skipped` in `[ctx]` and `redraft.stayed_on` asks again if the draft stays on that stage.
  Typed "not sure" is unchanged: helped once, then moved on.

## Limits to remember

- The model lands on a later stage with only that stage's ready_when and ask, not its boundaries or
  if_unclear. The next turn it is the current stage and has everything.
- Nothing in code can check that a stage really was answered. A model that skips too eagerly is
  caught only by reading transcripts, so measure with `scripts/scenario_check.py` (see
  [[measure-before-tuning-prompts]]) before trusting it, and reseed first
  ([[router-removed-model-chooses-the-framework-2026-10-09]]): `thought_reframe` lost its
  "mirror it back and confirm" line from the thought stage's `ready_when`.

## Found on the re-check the same day

- The `in_a_framework` bullet I wrote for skipping stages had a colon in it, so YAML read it as a
  mapping and the model got a key and a value instead of the sentence. Two more were found the
  same way when the question rules were rewritten. `test_every_rule_in_a_prompt_file_is_a_sentence_not_a_yaml_mapping`
  now fails on any bullet that is not a string. The existing rule "no colons inside a YAML bullet"
  lived only in the plan document, which is why it was missed.
- Not sure was left on a safety-concern turn, where there is no stage question. It is dropped there now.

## Questions are about one part and how it is for them (muhammad, 2026-10-09)

Rewrote `before_an_offer`, `voice`, `reflecting`, the three style entries, `_MEANING` for
`conversation_phase`, `question_focus` and `their_last: vague`, and the two redraft notes. Removed
what contradicted it: "take in every side, never one branch" (Direct), "ask about all of them" (before
an offer), "ask what they want, a plan or to look at what it means" (a menu), "two ways it could go"
for a vague reply (a menu), and questions aimed at a set's Finding the fit line. One live pass of
`scenario_check.py` (15 conversations, one run, so noise): questions were about how it was for them
in nearly every turn. Still seen: a reply that restated them (10 of 15 flagged), a reply with no
question, and a reply that joined two things they said ("tied to feeling you are not good enough").
The no-question and joining cases did not repeat on a second run of one scenario.

## The stage ledger (same day, muhammad chose it)

What a stage needs is often half there already: the event for ABCDE's activate stage, some of the
facts. The reply now carries `stages_known` before `text`: from the stage in force, each stage with
what they already said for it and whether it is met, stopping at the first open one. The question
asks only for what that stage's known lacks. Code checks the draft against its own ledger
(`redraft.ledger_stage`): a step that skips a stage it marked open, or stays on one it marked met,
is redrafted once. The closing counts as passable only once it has been asked.

Left lenient on purpose: a draft with no ledger is not judged, so scripted tests and a model that
omits the field never cost a redraft. If the model omits it often live, that is the place to
tighten.

One live run (Direct, Thought Reframe): their first message held the thought, so `thought` was
marked met and the first stage asked was `significance`; a tap on Not sure went straight to
`facts`. Ledger logs: `thought=met, significance=open`, then `facts=open`.

## ABCDE only, from the client's document (2026-10-09, later)

Lolly's ABCDE document (`~/Downloads/ABCDE Framework.docx`) changes two things I had built. It wants
each letter and name said as it is reached ("A is for Activating Event. You've mentioned being left out
of meetings. We can use that as our starting point."), not skipped in silence, and it wants the event
confirmed once when it is only a possible one. Both contradict muhammad's "skip it, never confirm". Both
are now ABCDE's own: stage `label` in the file, a walk note that says labels
(`context._WALK_WITH_LABELS`), and one confirm line on the activate stage. Frameworks without labels still
skip in silence. The first live run skipped without labels until the generic prompt rule ("skip it without a
word") was changed to defer to a label; a prompt rule written for one design silently beat the content file.
The document also says no automatic body check-in; muhammad decided the check-in is asked, so ABCDE keeps
the shared body route.
The other five frameworks live in `content/frameworks/paused/`.

## Labels in the chat were removed (muhammad, 2026-10-09, after a manual test)

The manual chat showed "A is for Activating Event. You've mentioned... B is for Belief..." written into
the reply, then two Not sure taps skipped C and D and E arrived three replies after Try it. muhammad's
decision: the chat never names a stage; the sidebar ledger holds what is known (bypassed, partial, confirm,
missing); the chat only asks the missing thing in Mani's own tone; the closing (E) is always asked. This
reverses the labelled walk built from the client's document, so the document's "introduce each letter" is not
followed. Stage `title` stays in the framework file for the ledger only and is not sent to the model.

## The Not sure button was removed (muhammad, 2026-10-09)

Cause: no document or request ever asked for a Not sure button. I read "if the user taps not sure, skip that
stage" as a button that should exist, and added one in `repairs.apply` under every skippable stage question,
with the tap handled in the orchestrator (`stage_skipped`), `[ctx]` and `redraft.stayed_on`. In the manual
chat two taps skipped C and D and E arrived three replies after Try it. Removed the button and all of its
plumbing: the label constant, the repair, the tap handling, the `[ctx]` line and meaning, the redraft check,
the prompt sentence and nine tests. Typed "I don't know" still goes through the model's own reading (a
`response_format.md` reasoning step), and the closing is still never skipped. Lesson: do not build a control
from a sentence that only describes what should happen if it existed.
