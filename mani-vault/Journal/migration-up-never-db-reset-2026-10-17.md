---
type: journal
date: 2026-10-17
tags: [journal, supabase, migrations, local, lessons]
---

# Apply a migration with `migration up`, never `db reset` (2026-10-17)

To apply migration 027 locally, Claude ran `supabase db reset` twice. A reset recreates the database from the
migrations, so every local test account and chat thread was deleted, and nothing had been backed up.
muhammad then asked for exactly the opposite: restart, reseed and migrate without deleting users or threads.

- A pending migration goes on with `supabase migration up --local`; `supabase migration list --local` shows
  what is applied. `supabase stop` and `supabase start` keep the data (`stop --no-backup` does not).
- `db reset` only with muhammad's yes, and after a dump of the data.
- Before migrating a database that holds data, rehearse the migration over rows shaped like the old ones inside
  a transaction that rolls back, then load those threads through `load_turn_context`. That is how 027 was
  checked afterwards ([[thought-reframe-second-framework-2026-10-17]]).
