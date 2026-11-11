---
type: journal
date: 2026-11-11
tags: [journal, deploy, vercel, supabase, safety, lessons]
---

# Deploy check of the safety branch (2026-11-11)

Read-only check of `feat/safety-follows-what-they-said` against GitHub `main`, the hosted database
`aipgficduzufstilndbw` and Vercel `mymani/mani-api`. Nothing was committed, pushed, migrated, seeded or deployed.
History, not rules. "Inferred" marks what was not read directly.

- **A rename of stored values is a three-part release.** Old and new code both do `safety.State(thread.safety)` and
  both write through `threads_safety_state`, so each fails on the other's names: a turn on a thread holding the other
  name answers 500, and a turn that moves the state off clear fails on the constraint. Code, migration 036 and the
  reseeded prompts have to land within the same minute. Vercel's instant rollback alone, after 036, puts old code on
  the new constraint.
- **Merging to `main` is the production deploy.** `mani-api` is linked to the GitHub repo, production branch `main`,
  domains assigned automatically, builds in about 25 s. Nothing runs migrations or the seed
  ([[duplicate-migration-versions-after-merge-2026-10-06]] said the same of the earlier project).
- **A preview deployment cannot be used as a smoke test.** All 11 env vars on `mani-api` are scoped to production
  only, so a preview builds and has no `DATABASE_URL` (inferred from the project's env list; no preview was called).
  It proves the build and nothing else.
- **Where the hosted data stood**: migrations 000 to 035, constraint `clear/open/unsafe`, 74 threads clear, 3 unsafe,
  none open; rewind snapshots 8 clear, 2 unsafe, 24 with no safety key; no `pending_follow_up` waiting; the seven
  prompt rows equal to `main`'s files, four of them different from the branch.
- **`CRISIS_BLOCKS_CHAT` is set on production and its value cannot be read** (sensitive). Inferred off: three threads
  flagged on 2026-11-10 took 4, 12 and 8 messages after the flag. muhammad's local `.env` has it on, and with it on a
  flagged thread refuses the next message, yet [[audit-of-the-safety-branch-2026-11-11]] describes long live danger
  chats. Open question for muhammad: which value the manual tests ran with. A thread response carries
  `crisis_blocks_chat`, so one signed-in call reads production's value.
- **A plain `pytest` writes to the dev database.** `backend/.env` names 54342, muhammad's dev Supabase, and the
  integration tests ran there twice in this check (797 passed, 14 skipped for JWKS, `test_account_lifecycle` left
  out). No user or thread from the runs was left behind. Export `DATABASE_URL` for 55432 first next time.
- **Tooling**: `supabase migration list --linked` and `db push --linked --dry-run` work without a prompt from
  `backend/`; the Vercel CLI needs `--scope mymani` on every call; `gh` is not signed in on this machine;
  `scripts/test_db.sh` removes the container `mani-pg-test` before it starts, the same one kept for integration tests.
- The hobby project `mani-ai-obuv` is paused and has no git link, and the old `mani-backend` has none either, so a
  push to `main` deploys `mani-api` only. The second hosted database `heqenombgkihfeggrxqc` gets nothing.

Related: [[prod-and-harness-audit-2026-11-10]], [[audit-of-the-safety-branch-2026-11-11]].
