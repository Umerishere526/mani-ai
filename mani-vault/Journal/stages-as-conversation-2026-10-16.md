---
type: journal
date: 2026-10-16
tags: [journal, walk, abcde, somatic, prompts, lessons]
---

# Stages as conversation, and the somatic cadence (2026-10-16)

Lolly's review of the two styles found ABCDE run as a questionnaire. Spec 0007 and its plan; the somatic
cadence (R18) built after it. See [[reply-moves-forward-not-recipe-2026-10-16]], [[body-kept-and-questions-held-2026-10-16]].

## The root cause was a counter in code

- `walk.advance` moved on any answer in `MOVES` and let a stage go after a second `not_yet`. The two-try rule was
  written on 2026-10-08 against the opposite failure (five asks in a row). An auto-move written against one
  failure became the next one. Keep both cases in view when a rule moves the conversation by itself.
- `context.may_check` let the check ride on the reply that received the control answer, which is her skipped answer.

## What a live run showed

- The skipped answer is fixed in all three styles. Inside ABCDE nothing moves on no, not sure or nothing comes to mind.
- The check now waits one more turn, and with control asked twice Directive and Reflective reached no check within
  her eight lines. The scenario harness's scripted lines run out before the check.
- The review's critical finding: "another issue" and "come back to it later" were read as `let_go`, so a stage was
  marked done that was never answered. A closed answer set needs a value for every way a person leaves a stage, or
  the model picks the nearest one that moves.

## Gotchas

- A colon in a prompt line that is a YAML mapping value breaks the whole file: "and say: Another issue" failed
  `test_every_rule_in_a_prompt_file_is_a_sentence_not_a_yaml_mapping`. Quote the line.
- A `pytest ... | tail` in a `&&` chain hides the failure exit code; use `set -o pipefail`.

## Superseded

The two-tries paragraph of [[abcde-walk-owned-by-code-2026-10-13]] and the letter line of
[[stages-are-skipped-not-confirmed-2026-10-09]] are superseded by this note.
