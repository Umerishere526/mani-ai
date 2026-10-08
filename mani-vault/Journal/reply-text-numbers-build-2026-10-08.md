---
type: journal
date: 2026-10-08
tags: [journal, config, tests, build, gotcha]
---

# Building spec 0008: reply text and numbers out of Python

Design notes are in [[reply-text-numbers-design-2026-10-08]]. These are what the build added.

## A mutation check on a refusal test writes to the real database

`tests/integration/test_admin_prompts.py` `refused()` expects the write to raise and has no rollback,
because a refused write stores nothing. With `_check_required` switched off to prove the tests notice,
the writes went through for real: `response_format` and `replies` were left inactive, four rows had
their version bumped and six `prompt_versions` rows appeared. A reseed does not undo it, because the
seed upsert never touches `is_active` or `version`. Repair was a reseed, then `is_active = true`,
`version = 1` on the four required rows and `delete from admin.prompt_versions` (the table held only
those six rows).

**How to apply:** mutation check a write guard against a throwaway database, or wrap the test in a
transaction it rolls back. Never against the local one the dev server uses. Same lesson as
[[guard-test-passed-without-its-guard-2026-10-07]], with a worse failure mode.

## The spec said "SupportStyle order", the enum order is not today's order

`SupportStyle` is supportive, reflective, direct. Today's buttons are Direct, Supportive, Reflective, and
the spec also says nothing may change in commit 1. The buttons follow the order of `style_labels` in
`replies.md` instead, which keeps today's output and puts the order in content. `test_greeting.py` holds
it. Worth correcting the spec's wording when it is next edited.

## Pydantic and a refusal that must not echo the value

`ValidationError.errors(include_input=False, include_context=False)` still carries the offending key in
`loc`, which is wanted. The YAML parser's own error text quotes the content, so `parse_yaml_row` says only
"does not parse as YAML". `parse_reply_shapes` used to put the YAML error in its message; it no longer does.

## Smaller things

- `EXPLAIN_LABELS` and `TELL_ME_ABOUT_THIS_LABEL` stayed through commit 1 so it was a pure move. Removing
  them changed what a decline drops: a bare "Tell me about this" now survives, and so does a duplicated
  "Tell me more" (there was never a guard for duplicates; the old test only passed because the offer's
  removal took both).
- `tests/seeded.py` is the one place a test gets the seeded `Replies` and `Tuning`, overridden one key at a
  time. `scripts/seed.py` `load_replies()` and `load_tuning()` are what it and the eval harness share.
- The build ran on a tree with spec 0009 uncommitted (muhammad's call, 2026-10-08). 0009's changes were
  staged, 0008's were not, so `git diff` showed only 0008. Reseeding for the full run also put 0009's
  unreviewed `mani_base.md` wording into the local database.

## Left for later

- `.claude/BACKEND.md` still names `ending.py` and `somatic.md`, and says `fold_idle_threads.py` is
  reachable as the cron route. `/sync`.
- Commit 2 is unmeasured by design: no real model run (muhammad, 2026-10-08). Feature 11 measures the
  vague, correction and heard scenarios.
