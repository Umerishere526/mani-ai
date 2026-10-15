# Prod runbook: stage asks and the working read (migrations 011, 012)

For muhammad to run. Nothing here has been run against hosted; the numbers below come from read-only
`select`s on 2026-10-14 (project `heqenombgkihfeggrxqc`, `.env.hosted`).

## What hosted holds today

| Check | Hosted |
|---|---|
| Migration history | `001`-`010`, nothing after. The `011`-`017` pushed on 2026-10-06 (`mani-vault/Journal/duplicate-migration-versions-after-merge-2026-10-06.md`) are no longer there, and neither table carries their columns |
| `thread_technique_state` | 17 rows: 11 open offers (`offered` / `offering`), 3 mid-framework (`consequence`, `dispute`, `somatic_practice`), 3 declined. No `stage_asks` column |
| `thread_summaries` | 3 rows. No `working_read` column |
| Other rows | 10 users (7 `@example.com`, 2 `@mymani.ai`, 1 `@gmail.com`), 38 threads, 360 messages, 184 model calls, 0 crisis events, 17 exercises |
| Content | All 5 prompts older than the files (`mani_base` 20,496 chars against 23,722 now); seeded 2026-10-09. `abcde` active, the 5 paused frameworks inactive |
| Safety | RLS on every public table; `authenticator` cannot assume `mani_service`; `mani_service` can UPDATE both tables, `authenticated` cannot |
| Vercel production env | No `AI_DEBUG_MODE` (off), no `SENTRY_DSN` (no error reports at all), no `DAILY_MESSAGE_LIMIT` (off) |

Not checked (the second read-only pass was skipped): the full `test_grants.sql` privilege list, PostgREST's exposed
schemas, and how long the 11 open offers have stood. Step 2 covers them.

## Order, and why

Migrations first, then code, then content. **Code before migrations breaks nearly every turn**: loading a turn
still works (it reads whole rows as JSON and the missing keys fall back to their defaults), but the turn's write
fails: the `working_read` upsert on every turn that forms a read, the `stage_asks` upsert on every offer and
framework turn, and the summary run's `select` of `working_read`. Each failed write rolls the whole turn back.
**Migrations before code is harmless**: both columns are additive (`stage_asks` not null with default 1,
`working_read` nullable), and the code on main reads rows into models that ignore keys they do not know.

Content after code: the new prompts teach `[ctx]` keys (`read_*`, `stage_check`, `stage_asked`) that only the new
code sends, and the new code reads stage keys (`label`, `confirm`, `read_slots`, `check`) that only the new
`abcde.md` has.

## Steps

1. **Window.** Low traffic. 10 users, so a few minutes of mismatch between code and content is the real risk, not load.

2. **Confirm the starting point (read only).**
   ```bash
   cd backend
   psql "$HOSTED_DB_URL" -c "select version from supabase_migrations.schema_migrations order by version"   # ends at 010
   psql "$HOSTED_DB_URL" -c "select rolconfig from pg_roles where rolname = 'authenticator'"            # exposed schemas
   ```
   Dashboard, API settings: exposed schemas `public, graphql_public` and new tables not exposed automatically, as
   `supabase/config.toml` has locally.

3. **Push the migrations.**
   ```bash
   supabase db push --db-url "$HOSTED_DB_URL" --dry-run   # must list exactly 011 and 012
   supabase db push --db-url "$HOSTED_DB_URL"
   ```
   011 sets `stage_asks = 1` on all 17 rows from the default (no table rewrite) and validates `stage_asks >= 1`;
   the 3 mid-framework threads start their current stage at one ask. 012 adds `working_read` as null on all 3
   rows, so every existing thread's next turn starts with no read (`read_so_far` empty) and may get the client's
   focus line once more.

4. **Check the database.**
   ```bash
   psql "$HOSTED_DB_URL" -f tests/sql/test_grants.sql
   ```
   `test_grants.sql` only creates `pg_temp` helpers and tries one insert it expects to fail, so it leaves no rows.
   Every line should read PASS, including the two for the read and the stage ask count. Locally the same suite
   passes on a fresh database with all 12 migrations and on the running local Supabase.

5. **Deploy the code** (merge to main, Vercel production). The new code refuses to start when `ENVIRONMENT=production`
   and `AI_DEBUG_MODE=true`. Production sets neither debug flag today; check any Preview environment that sets
   `ENVIRONMENT=production` does not set `AI_DEBUG_MODE` either.

6. **Seed the content, straight after the deploy is live.**
   ```bash
   set -a; source .env.hosted; set +a
   python scripts/seed.py      # 1 framework (abcde), 5 prompts; paused frameworks stay inactive
   ```
   Then `POST /v1/admin/prompts/cache/invalidate` with an admin token. Each Vercel instance keeps its own cache, so
   instances the call does not reach pick the new content up within `PROD_PROMPT_CACHE_TTL` (300 s).

7. **Smoke test** with a test account in the chat tester against production: one conversation to an offer, Try it,
   two stages, and check that `admin.llm_calls` has no `error` outcomes since the deploy and that
   `thread_technique_state.stage_asks` and `thread_summaries.working_read` are being written.

## Rollback

Migrations are forward-only and need no undoing: the old code ignores both columns. Roll back with Vercel's
instant rollback, then re-seed the old content from main's files:
```bash
git worktree add /tmp/mani-main <the commit production rolled back to>
cd /tmp/mani-main/backend && cp ../../<repo>/backend/.env.hosted .
set -a; source .env.hosted; set +a
<repo>/backend/.venv/bin/python scripts/seed.py
```
then invalidate the cache. Reverting the code alone leaves the new prompts talking about `[ctx]` keys the old code
does not send.

## Before real traffic (not part of this push)

- 7 `@example.com` accounts are in prod; decide whether they stay.
- `SENTRY_DSN` is unset in production, so errors are only in Vercel logs. When it is set, the privacy settings in
  `main.py` already keep message content out of reports.
- `DAILY_MESSAGE_LIMIT` is off (`0`); muhammad's number is 300.
