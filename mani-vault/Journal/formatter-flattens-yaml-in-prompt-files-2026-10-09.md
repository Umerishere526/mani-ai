---
type: journal
date: 2026-10-09
tags: [journal, content, prompts, yaml, tooling]
---

# A markdown formatter flattened the YAML in replies.md

Found while building spec 0010 task 2. `backend/content/prompts/replies.md` came in uncommitted with a real wording change to `offer.text` and, mixed into it, every nested key pulled to the left margin (`greeting:`, `offer:`, `labels:`, `by_framework:`), blank lines added around each `#` comment, and the list under `after_framework_questions` reflowed. The body of a prompt file is YAML, not markdown, so the file parsed to `greeting: null` plus a pile of extra top level keys. `load_replies()` refused it, so the seed and `test_offer.py` would both have failed.

The look is a markdown formatter run on save: blank lines around `#` "headings" and stripped indentation. Nothing in the repo configures one, so it is an editor setting.

## How to spot it

- `git diff -w` on a prompt file shows only the real wording change; the plain diff shows every nested line moved.
- `python -c "from scripts.seed import load_replies; load_replies()"` in `backend/` names every key that lost its parent.

## What was done

muhammad chose to restore the committed file and keep only the new offer text, with the line break inside it written as a space, so it stays one YAML string. A literal line break inside a double quoted YAML string folds to a space anyway.

## Not fixed

Formatting on save for `backend/content/**/*.md` is still on in whatever editor did it. A `.prettierignore` or an editor exclusion for `backend/content/` would stop a repeat; that is muhammad's call, since it touches his editor setup.

Related: [[stage-skip-and-short-questions-scope-2026-10-09]]
