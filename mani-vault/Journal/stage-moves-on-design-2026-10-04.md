---
type: journal
date: 2026-10-04
tags: [journal, frameworks, stages, design]
---

# Designing "a stage moves on after one answer" (row 18)

Spec: `docs/specs/0003-stage-moves-on-one-answer/`. muhammad picked code enforcement, holds only for the client's lines, kept branches and DBT STOP while acting, ADR-011's start turn kept, and writes the 26 `if_earlier_missing` questions himself.

## What the first draft got wrong (caught by a cross check on another model)

- **"The start turn" is not one path.** A tapped yes sets `accepted_this_turn` before the model call; a typed yes is accepted only after it (`deferred` in `orchestrator`), so `[ctx]` is built with the offer still waiting. A tapped start where the model gave no state stores phase `offering`. Any rule keyed on "after the start turn" must say what a stored `offering` does. The spec now defines a *move on turn* (stored stage after `offering`, before `somatic_checkin`, not accepted this turn) and leaves every other turn exactly as today.
- **An unknown stored stage does not drop the framework.** `phase_index` returns -1, `running` stays true, and `validate_transition` treats it as nothing started, so the framework falls back to `offering`. Check this before claiming a rename is harmless.
- **`ENDING_STAGES` is not "the somatic stages".** It also holds `grounding`. Use the two stage ids.
- **The body check reads its own branches as `next_stage_if_unclear`.** Dropping `next_stage_*` would have lost "closing already names an action, skip the check in". Somatic stages are now always sent in full.
- **First stage branches serve the start turn.** Sending them after it invites a hold; they carry `start_only: true`.
- **A specification's tone line carries scenario text.** Thought Reframe's "what does not support it" branch begins "She usually responds sooner"; reused as an `ask` it fails `test_negative_set.py`. Keep only the question half (as [[framework-files-what-the-model-actually-reads]] already says).

## Lessons

- The explorer's dependency map (haiku) marked stages HARD that are not. Judge each stage from its real question.
- "Invariant: never shown again" was false the moment holds existed. Write the invariant about what Mani *asked*, not what `[ctx]` showed.

Related: [[panic-and-already-answered-stages]], [[somatic-route-asked-once-and-held-in-code]].
