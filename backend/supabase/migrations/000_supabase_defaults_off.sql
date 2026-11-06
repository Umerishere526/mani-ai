-- ABOUTME: Turns off what a new Supabase project grants by default on everything `postgres` creates in `public`.
-- ABOUTME: Runs before 001, so the grants the migrations make are the whole story on any project.

-- A new project gives anon, authenticated and service_role every privilege on each table, sequence and function
-- created in `public`. The privilege model here is explicit and column-scoped, and a function that writes under
-- privilege its caller lacks must be callable by the backend's role alone; neither survives these defaults.
alter default privileges for role postgres in schema public revoke all on tables from anon, authenticated, service_role;
alter default privileges for role postgres in schema public revoke all on sequences from anon, authenticated, service_role;
alter default privileges for role postgres in schema public revoke all on functions from anon, authenticated, service_role;
