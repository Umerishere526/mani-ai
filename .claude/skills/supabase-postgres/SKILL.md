---
name: supabase-postgres
description: Supabase and Postgres best practices for this repo — RLS policies, key handling, migrations, schema design, indexing, and query performance. Use when adding or changing database tables, columns, migrations, RLS policies, indexes, or SQL queries; when integrating Supabase into web/, mobile/, or backend/; or when the user mentions Supabase, Postgres, RLS, row level security, migrations, database schema, or slow queries.
---

# Supabase & Postgres

**Nothing in this repo uses Supabase or Postgres yet.** The backend is FastAPI with no database. Adding one is an architectural decision — discuss it with muhammad before starting, per the root CLAUDE.md.

These rules apply the moment a database lands. See also [SUPABASE.md](../../SUPABASE.md).

## Row Level Security — the non-negotiable part

A Supabase table without RLS is readable and writable by anyone holding the anon key, which ships in your client bundle.

- Enable RLS in the **same migration** that creates the table:
  ```sql
  create table public.posts (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    body text not null,
    created_at timestamptz not null default now()
  );
  alter table public.posts enable row level security;
  ```
- Write one policy per operation, not a blanket `for all`:
  ```sql
  create policy "read own posts" on public.posts
    for select using ( (select auth.uid()) = user_id );

  create policy "insert own posts" on public.posts
    for insert with check ( (select auth.uid()) = user_id );
  ```
- `select` and `update`/`delete` use `using`. `insert` uses `with check`. `update` usually needs **both** — `using` decides which rows are visible to update, `with check` validates the result.
- Wrap `auth.uid()` in a subselect — `(select auth.uid())` — so Postgres evaluates it once per statement rather than once per row. On a large table this is the difference between fast and unusable.
- Index every column a policy filters on, especially `user_id`.
- Verify policies as a normal user, not the service role. The service role bypasses RLS, so a test run that way proves nothing.

## Keys

| Key | Where it may live | Bypasses RLS |
|-----|-------------------|--------------|
| anon / publishable | `web/`, `mobile/`, public bundles | No |
| service role | `backend/` env only | **Yes** |

- Never put a service role key in `NEXT_PUBLIC_*` or `EXPO_PUBLIC_*` — those are inlined into the client bundle at build time.
- Load the service role key in `backend/` through `pydantic-settings` and a gitignored `.env`.
- If a service role key is ever committed, rotate it. Removing the commit is not sufficient.

## Migrations

- Every schema change is a migration file in version control. No dashboard clicking, no ad-hoc SQL against a live database.
- One logical change per migration, descriptively named.
- Forward-only in shared environments: to undo something, write a new migration.
- Regenerate TypeScript types after each schema change and commit them, so `web/` and `mobile/` break at compile time rather than in production.

## Schema design

- `text` over `varchar(n)` unless the length is a genuine business rule — Postgres gains nothing from the cap.
- `timestamptz`, never bare `timestamp`. Store UTC.
- `uuid` or `identity` primary keys; avoid `serial` in new tables.
- **Index every foreign key.** Postgres does not create one automatically, and the omission makes joins and cascading deletes slow.
- Encode invariants as `check` constraints and `not null`, rather than relying on app-layer validation alone.
- Put application tables in `public` (or a dedicated schema) — never modify the `auth` schema.

## Query performance

- Select the columns you need; `select *` across a wide table and a network is waste that compounds.
- Paginate every list endpoint. An unbounded query is an incident waiting for the table to grow.
- Run `explain analyze` before adding an index — a guessed index adds write cost with no read benefit.
- Filter in SQL, not in Python or JavaScript after fetching.
- Watch for N+1: fetching a list then querying per row. Use a join or a single `in` query.

## Client usage

- One client instance per app, imported where needed — not constructed per component or per request.
- In `web/`, respect the App Router split: a server client with cookie handling for Server Components, a browser client for Client Components. Mixing them produces auth bugs that are hard to trace.
- The Supabase JS client does **not** throw. Check `error` on every response, or you will silently get `null` data.
