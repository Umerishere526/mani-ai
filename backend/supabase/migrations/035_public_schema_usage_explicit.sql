-- ABOUTME: Grants the public schema only to the roles that use it, Supabase Auth included, and to nobody by default.
-- ABOUTME: Account deletion depends on it: GoTrue's delete from auth.users cascades into every table in public.

-- Postgres gives every role USAGE on `public` through PUBLIC. The hosted project had that taken away by hand, and
-- with it went supabase_auth_admin's reach into the tables an account deletion cascades into, so deleting an account
-- failed. Stated here, it holds the same on every project: no default, and each role that needs the schema named.
revoke usage on schema public from public;
grant usage on schema public to anon, authenticated, supabase_auth_admin;
