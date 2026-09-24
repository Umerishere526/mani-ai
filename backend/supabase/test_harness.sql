-- ABOUTME: Recreates the pieces Supabase adds to a database, for testing on plain Postgres.
-- ABOUTME: Applied before 001_initial_schema.sql so RLS can be exercised without Supabase.

-- Supabase's three roles. `authenticated` is what a signed-in caller acts as; the
-- application sets request.jwt.claims alongside it so auth.uid() resolves.
do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'anon') then
    create role anon nologin;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'authenticated') then
    create role authenticated nologin;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'service_role') then
    create role service_role nologin bypassrls;
  end if;
  -- What GoTrue itself connects as (confirmed via GOTRUE_DB_DATABASE_URL on a real
  -- project) to manage auth.users, including cascading a deletion into every table that
  -- references it. Does NOT bypass RLS - matching that is the point of stubbing it here,
  -- since a migration granting it access only proves anything if RLS is still in the way
  -- until the grant exists.
  if not exists (select 1 from pg_roles where rolname = 'supabase_auth_admin') then
    create role supabase_auth_admin noinherit createrole login password 'postgres';
  end if;
end
$$;

create schema if not exists auth;

-- Only the columns this schema references. The real table has many more.
create table if not exists auth.users (
  id         uuid primary key default gen_random_uuid(),
  email      text unique,
  created_at timestamptz not null default now()
);

-- Matches Supabase's own definition: read the subject from the request's JWT claims,
-- which the application sets per transaction with `set local`.
create or replace function auth.uid()
returns uuid
language sql
stable
as $$
  select nullif(
    coalesce(
      nullif(current_setting('request.jwt.claim.sub', true), ''),
      nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub'
    ),
    ''
  )::uuid
$$;

grant usage on schema auth to anon, authenticated, service_role, supabase_auth_admin;
grant select on auth.users to authenticated, service_role;
-- Its actual job: GoTrue creates and deletes rows in auth.users directly.
grant select, insert, update, delete on auth.users to supabase_auth_admin;
