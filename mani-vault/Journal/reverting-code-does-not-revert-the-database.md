# Reverting code does not revert the database

2026-10-07. `main` was reverted to `1473a0c` to undo a merge that should not have happened.
The revert was clean and the working tree matched the target exactly. Both databases were
still seven migrations ahead of it.

The reverted branches had added 011-017: four columns on `thread_technique_state`
(`holds`, `known`, `ending`, `phase_since`), `decision` on `admin.llm_calls`, the
`public.framework_outcomes` table, and `'stopped'` on the `technique_outcome` enum. `git
revert` touches none of that. A migration is a forward-only write to a system the
repository does not own.

## Why it did not crash

Two accidents, not design:

- `Row` in `mani/models/rows.py` sets `extra="ignore"`, so the extra columns came back in
  `to_jsonb(s)` and were dropped silently. With `extra="forbid"` every turn would have
  failed at validation.
- No row anywhere held `outcome = 'stopped'`. `TechniqueOutcome` in the reverted code has
  three members and the database enum had four. One such row and that thread's every turn
  raises on validation.

The second one is worth remembering: an enum value added by a migration outlives the code
that introduced it, and `StrEnum` validation is where it surfaces, far from the migration.

## What cannot be undone

`alter type ... add value` has no inverse. Postgres cannot drop an enum value. Rolling
`016` back means recreating the type and rewriting every column that uses it, or accepting
the value and writing forward. On a database with live rows the second is the only sane
option.

## The check that matters

Before trusting a revert, compare `supabase_migrations.schema_migrations` against the
migration files on disk. The codebase cannot tell you this - only the database can.

Numbers were also reused across the branches: `011` was both `technique_state_holds` and
`technique_outcome_stopped`, `013` both `llm_call_decision` and `llm_call_facts`. Parallel
branches each picking "the next number" collide, and the merge that resolves it records one
name against the other's contents.
