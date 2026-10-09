---
type: journal
date: 2026-10-08
tags: [journal, audit, cleanup, build, database]
---

# Building spec 0014: removing what nothing reads or runs

Spec: `docs/specs/0014-audit-unused-code-files/`. Scope feature 16. Design notes: [[audit-unused-design-2026-10-08]].

muhammad chose to build on top of the staged 0012 and 0013 work rather than commit it first, against the spec's step 0. To keep the diffs apart, every 0014 edit is unstaged; `git diff --cached` is 0012 and 0013, `git diff` is 0014. The one exception is `git rm --cached .obsidian/workspace.json`, which has to stage.

## Counts

- Before: 675 passed, 4 skipped (all four are the JWKS symmetric token skips; integration ran).
- After every Python change, on the database before migrations 022 to 025: 670 passed, 4 skipped. Down 5, as the spec expects: the `spend_since` test and the four `check_capsules` tests.
- On the reset database with 001 to 025 applied and reseeded: 670 passed, 4 skipped (the same four), `test_db.sh --local` passed with 84 checks, both account deletion tests passed, and the OpenAPI schema is byte for byte the same as before the build.

## What did not finish in the session

- **The auto mode classifier refused to apply a column drop to the local database** (`supabase migration up --local`, judged irreversible) until muhammad asked for the reset outright. After that, `supabase db reset` applied 001 to 025 cleanly and the reseed gave 6 frameworks, 10 prompts and 17 exercises, with prompt rows identical to the baseline.
- A later batch (pytest, the OpenAPI compare, the keep item greps) was refused with no reason given. Not retried.
- What stood in: `scripts/test_db.sh` with no flag builds a throwaway Postgres, applies every migration and runs both SQL suites. All 25 migrations applied there and both suites passed. Each new SQL check was also proven to fail: restoring `threads_delete` or the backend's DELETE grant on technique state made `test_grants.sql` and `test_rls.sql` fail as they should.

## Lessons

- **`check_capsules` was the only executable form of "no self judging button label".** It went with nothing that checks labels today, because `eval_replies._score` never scored labels. The model still writes labels. If self judging labels come back, the check has to come back with a caller.
- **"No DELETE policy" has to exclude the account cascade.** The spec said to assert that no DELETE policy exists on technique state, but migration 005's `auth_admin_cascade_delete` sits on every user table and must stay. The assertion checks for DELETE policies whose roles are anything but `supabase_auth_admin`.
- **The test fallback named a database on the wrong port.** `tests/conftest.py`'s fallback `DATABASE_URL` used 54322 (the Supabase default, where another project may answer) while its own `SUPABASE_URL` used 54341, under a comment saying it named no database. That is the exact hazard the comment warned about. Fixed to 54342.
- **Code that stops reading a column can land before its drop**, as long as the column has a default. `stages` and `activation_conditions` both did, so the seed could stop writing them before 023 is applied, and the suite stayed green on the old schema.
- **Rebuilding the venv dropped more than the three removed packages**: `fastapi-cloud-cli`, `jinja2`, `rignore` and others came from an old `fastapi[standard]` install. Nothing imports them and `fastapi dev` works without them. The old venv sat in the scratchpad during the session.

## Noticed, not fixed

- `backend/docs/database-schema-reference.md` §2 calls `admin.exercises` empty; 17 are seeded.
- `drop policy if exists techniques_offered_delete` in migration 025 prints a "does not exist, skipping" notice on every reset and in `test_db.sh`. The spec asked for `if exists`.

Related: [[guard-test-passed-without-its-guard-2026-10-07]], [[reverting-code-does-not-revert-the-database]], [[duplicate-migration-versions-after-merge-2026-10-06]]
