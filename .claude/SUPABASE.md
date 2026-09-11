# Supabase & Postgres practices

**Status: not installed.** Nothing in this repo depends on Supabase today — the backend is FastAPI talking to no database yet. These rules apply from the moment a Supabase or Postgres dependency lands, and exist so the first integration is done correctly rather than retrofitted.

Discuss with muhammad before introducing Supabase — adding a database is an architectural decision, not a routine one.

## Row Level Security

- **RLS on every table with user data. No exceptions.** A table without RLS in a Supabase project is world-readable through the anon key.
- Enable it at creation time in the same migration as the `CREATE TABLE`, never as a follow-up.
- Write a policy per operation (`select`, `insert`, `update`, `delete`) rather than one broad `for all` policy — broad policies hide mistakes.
- Wrap `auth.uid()` in a subselect so Postgres caches it per statement instead of per row:
  ```sql
  using ( (select auth.uid()) = user_id )
  ```
- Test policies as an unprivileged user. A policy that passes as the service role proves nothing.

## Keys

- The **anon / publishable** key is the only one that may reach the web or mobile client. It is public by design and safe *only* because RLS is enforcing access.
- The **service role key** bypasses RLS entirely. It belongs on the FastAPI backend, loaded from environment via `pydantic-settings`, and must never appear in `web/`, `mobile/`, or any committed file.
- Never put a service role key in a `NEXT_PUBLIC_*` or `EXPO_PUBLIC_*` variable — those are compiled into the client bundle.

## Schema changes

- All schema changes go through migration files in version control. No ad-hoc SQL against a live database, and no clicking through the dashboard for anything structural.
- One logical change per migration, with a descriptive name.
- Migrations are forward-only in shared environments — to undo, write a new migration.
- Regenerate TypeScript types after every schema change and commit the result, so `web/` and `mobile/` fail at compile time rather than runtime.

## Schema design

- Prefer `text` over `varchar(n)` unless a limit is a real business rule; Postgres gains nothing from the length cap.
- Use `timestamptz`, never bare `timestamp`. Store UTC.
- Every foreign key gets an index — Postgres does not create one automatically, and its absence makes joins and cascading deletes slow.
- Use `identity` columns or `uuid` primary keys; avoid `serial` in new tables.
- Add `check` constraints for invariants rather than relying on application validation alone.

## Queries

- Select only the columns you need. `select *` over a wide table across a network is waste that compounds.
- Always paginate list endpoints — an unbounded query is a latency incident waiting for the table to grow.
- Reach for `explain analyze` before adding an index; guessing at indexes adds write cost without read benefit.
- Push filtering into SQL rather than fetching rows and filtering in Python or JavaScript.

## Client usage

- Instantiate one client per app and import it — do not construct a client per component or per request.
- In Next.js, respect the server/client split: server components use a server client with cookie-based session handling, client components use the browser client. Mixing them breaks auth in confusing ways.
- Handle the `error` field on every Supabase response. The client does not throw; ignoring `error` silently yields `null` data.
