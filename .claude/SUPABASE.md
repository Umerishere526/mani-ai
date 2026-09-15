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
- The **service role key** bypasses RLS entirely. It lives on the FastAPI backend, loaded from environment via `pydantic-settings`, and must never appear in `web/`, `mobile/`, or any committed file.
- Never put a service role key in a `NEXT_PUBLIC_*` or `EXPO_PUBLIC_*` variable — those are compiled into the client bundle.

## Which client the backend uses — the rule that makes RLS real

In this architecture no frontend talks to Supabase directly; everything routes through FastAPI. So **if the backend uses the service role key for ordinary user requests, RLS never applies to any real traffic.** You would have policies on every table that are never exercised, and correctness would depend on every endpoint remembering its own `where user_id = …` filter.

That is not hypothetical. It is how the previous codebase leaked: one query omitted the user filter, and any signed-in user could read another person's full conversation, including a suicidal-ideation disclosure. RLS existed. The service-role client walked straight past it.

Two clients, and the distinction must be visible at every call site:

- **User-scoped — the default.** Build a per-request client carrying the caller's JWT, so Postgres enforces ownership whether or not the endpoint remembers to filter. Nearly all traffic uses this.
- **Service role — the exception.** Only for genuine cross-user work: admin dashboards, background jobs, migrations. Give it a distinct name (`admin_client`, never `client`) so its use stands out in review, and justify each one.

**Derive the user id from the verified JWT. Never from the request body, a query parameter, or a header.** A client-supplied `user_id` is an authorization bypass: the caller simply names someone else. Verify the token, extract the subject, ignore anything the request claims about identity.

Test both paths as an unprivileged user. A policy that passes under service role proves nothing.

## What the Data API exposes — set this deliberately, per environment

PostgREST runs against the database whether or not this project uses it, so anything it
exposes is reachable by anyone holding the anon key. Two settings decide that, and both
default to the permissive answer.

- **`[api] schemas` in `supabase/config.toml`.** Only `public` and `graphql_public` are
  listed, so `admin` — prompts, providers, `llm_calls`, `crisis_events` — is not merely
  denied, it is invisible: requests return `404`, even with the service key. Keep it that
  way. Anything added to that list becomes internet-reachable.
- **`auto_expose_new_tables`.** Ships commented out and **defaults to `true`**, which
  grants the Data API roles access to new `public` tables without explicit GRANTs. Left on,
  it silently overrides column-scoped grants — including the one stopping a user clearing
  their own `crisis_detected` flag. It is set to `false` here, so explicit GRANTs are the
  whole story.

**`config.toml` configures local development only.** A hosted project has its own
equivalents in the dashboard under Data API settings, and they are **not** migrated by
`supabase db push`. Set them by hand on every hosted project before it takes traffic, and
re-check after any dashboard change.

Assert the result rather than trusting it. `backend/tests/sql/test_grants.sql` checks the
privilege model directly — that `anon` holds nothing, that the column-scoped grants are
still column-scoped, that definer functions pin their `search_path`, that RLS is on
everywhere, and that every foreign key is indexed. Run it against local Supabase with
`scripts/test_db.sh --local`, and against a hosted project before it goes live.

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
