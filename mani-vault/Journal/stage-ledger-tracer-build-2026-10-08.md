---
type: journal
date: 2026-10-08
tags: [journal, frameworks, stages, ledger, gotcha, tests]
---

# Stage ledger tracer (spec 0010, task 1)

Built the tracer: migration 021, the ledger in the guard and the orchestrator, `[ctx]` `stage_ledger`, the ` | ` in all six Stages lines. Counting and the backstops are task 2.

## Gotchas worth keeping

- **A plain YAML scalar cannot hold `: `.** The drafted `fields.state` sentence ("their latest message: known when ...") broke `response_format.md` at parse time. Every prompt draft in a spec needs a read through `parse_yaml_row` before it is called ready, not only a read by eye.
- **The stored stage is now derived, so a test that sets only `phase` makes an inconsistent row.** `_land_on` in `test_turn.py` writes the ledger too (every stage before the landing stage known). Any new helper that lands a thread on a stage has to do the same, or the next turn recomputes the stage from an empty ledger and lands on `activate`.
- **`StageStatus` and `LedgerEntry` live in `rows.py`, not `techniques.py`.** `techniques.py` imports `rows`, and `rows.TechniqueState` holds the ledger, so the other way round is a circular import. `techniques.py` still exposes `StageStatus` by importing it.
- **The guard no longer decides the stage before `closing`.** `Checked.phase` is None there and the orchestrator sets it from the ledger (`_running_state`). The unanswered offer and the decline paths therefore write `checked.phase or OFFERING`; without that an offer row would be written with a null phase and read back as not running.
- **A declined offer asked for again must set `accepted_framework`.** `technique` is reassigned to the stored declined row in that branch, and a framework id read before the reassignment is None.

## Waiting on muhammad

The prompt wording in `mani_base.md` and `response_format.md` is the spec's draft, with one change forced by YAML (a comma where the draft had a colon). It is not seeded yet: the database still holds the old prompts and the old Stages lines until muhammad reviews it and the reseed runs.

Related: [[stage-ledger-design-2026-10-08]], [[stage-skip-blocked-by-its-own-gate-2026-10-08]], [[seeded-content-turns-dormant-paths-live-in-tests]]
