2026-11-06

# Supabase's default privileges made a fresh project unsafe

Moving the live database (`heqenombgkihfeggrxqc`) into the Mani org's project "mani-app" (`aipgficduzufstilndbw`): I emptied mani-app of the previous app (138 users, 3,882 messages, backed up first), pushed the 33 migrations, restored the data, re-seeded, then ran `tests/sql/test_grants.sql` against it. It failed: "a user cannot write a turn through the function" — any signed-in person could call `create_message_pair` and forge Mani's half of their own transcript.

Why: a new Supabase project has `alter default privileges for role postgres in schema public grant all on functions to anon, authenticated, service_role` (and the same for tables and sequences). `001`'s `revoke all ... from public` did nothing to those direct grants. Live was safe only because someone had removed the defaults by hand at some point; no migration recorded it. Every environment built from the migrations alone (a staging project, a Supabase branch, the throwaway test DB) came up insecure, and the test harness could not see it because it never had the defaults.

The same read-only audit of the privilege surface found that `authenticated` could `select pending_follow_up, understanding, rewind_snapshot from threads` through the Data API with the person's own token — `pending_follow_up` carries the reading's whole call, system prompt included — and could enter `admin` to read `frameworks` (the client's text) and `exercises`, which only the backend needs.

What was done: `test_harness.sql` grants the defaults (so the suite reproduces a hosted project); `000_supabase_defaults_off.sql` turns them off before 001 (`supabase db push --include-all` applies a migration numbered behind the applied ones); `034_backend_only_state.sql` hides the columns, moves the catalog to `mani_service`, revokes EXECUTE on the definer and trigger functions from the API roles, and adds the missing `turn_traces(llm_call_id)` index. Both hosted projects now pass 76/76 and dump identically.

Lessons:
- A suite that asserts privileges proves nothing unless its fixture starts from what the hosted platform gives you. Harness = platform defaults, migrations = the whole story.
- "Identical to live" is the wrong target when live's safety is undocumented; the target is "identical to what the migrations produce", and live must match that.
- Compare two projects with a normalised `supabase db dump` diff, not by eye; it caught 47 lines the first time.

Related: [[worktrees-share-one-local-database-2026-11-06]], `.claude/SUPABASE.md` ("Default privileges").
