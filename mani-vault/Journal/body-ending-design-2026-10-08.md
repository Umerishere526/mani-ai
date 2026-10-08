---
type: journal
date: 2026-10-08
tags: [journal, prompts, ending, gotcha, preferences]
---

# Designing spec 0009: the body ending as rules

## muhammad's calls

- He rejected the client's ending mid interview and gave his own flow: ask how they feel at the end of the framework; if bad, apologise, invite them to unpack it, and move them to the body check; the check is guided one step per turn ("take deep breaths", then "tell me three things you see", wait for the answer); afterwards ask again, and if they still feel bad keep talking.
- The body check is offered even when they feel good. The model picks the steps and their count, from a list built out of the client's practices. Everything is typed, no buttons until Chat More / Go to Library.
- Chat More and Go to Library labels stay Python constants for now. Built before spec 0008, so the turn cap is a constant that 0008 moves into `tuning`.
- Tests only, no real run.

Lesson: on a flow the client specified, ask early whether muhammad wants the client's flow at all. Two rounds of questions about the client's version were thrown away.

## Gotchas the cross check caught

- Retirement must win over `_decided_framework`'s write: it sets `retire_technique = False` and would overwrite a retirement decided after the model call.
- A crisis turn makes no model call, so anything that retires on a model field never retires on a crisis turn. Locked threads then hold a framework mid flight forever.
- Clearing a cap counter on a step back lets the model reset the cap by stepping back and forth.
- `validators.missing_handoff` and `test_style_findings.py` compare against the literal phase `"somatic"`, which no real phase id matches, so the handoff check was silently a no-op.
- The turn context query reads `to_jsonb(s)`, the whole row, so a new `thread_technique_state` column needs only the row model and the upsert.
- `admin.frameworks.stages` is still selected by `config_tables.FRAMEWORK_COLUMNS` for the admin side, even once nothing in `mani/chat` reads it.

Related: [[reply-text-numbers-design-2026-10-08]], [[client-lines-the-code-matches-exactly]], [[repairs-guarded-state-by-accident]]
