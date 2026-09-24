-- ABOUTME: Grants supabase_auth_admin what it needs to actually complete the cascades
-- ABOUTME: every user-owned table already promised via `on delete cascade`/`set null`.

-- Deleting a user through the real Auth Admin API - the only way to delete an account,
-- since GoTrue owns auth.users - executes as `supabase_auth_admin`, Supabase's own
-- Postgres role for Auth. Verified live, not assumed, with two distinct failures in turn:
--
-- 1. With zero grants on `public`, the cascade into a user's profiles row succeeded
--    anyway - profiles has no DELETE policy at all, which Postgres's RLS treats as zero
--    visible rows rather than a hard denial, so the cascade silently matched nothing to
--    deny. It failed with `permission denied for table threads (SQLSTATE 42501)` the
--    moment the account had a real thread. The grants below fix that half.
-- 2. Once granted, the identical error persisted on the identical table - because
--    `threads` has an explicit DELETE policy scoped to `auth.uid() = user_id`, which
--    `supabase_auth_admin`'s claims-free session can never satisfy. A table-level grant
--    only clears the table-privilege gate; RLS still runs on top of it.
--
-- `service_role` bypasses RLS entirely (confirmed: `select rolbypassrls from pg_roles`);
-- `supabase_auth_admin` does not, and - confirmed live - cannot be altered to: it is a
-- reserved role Supabase locks even from the `postgres` role this project connects as.
-- So the fix is one additional permissive policy per table, scoped to this one role,
-- rather than a broader bypass. Permissive RLS policies are OR'd together, so this adds
-- an allowance for `supabase_auth_admin` without touching what any existing policy
-- already permits for `authenticated` or anyone else.
--
-- 3. A third failure, found only once a test account had a real message: deleting from
--    `messages` fires `sync_thread_message_count()` (not security definer, so it runs as
--    whichever role triggered it), which UPDATEs `threads.message_count` and
--    `.last_message_at`. DELETE on threads was not enough - the cascade needs UPDATE on
--    those two columns too, granted and policied the same narrow way.

grant delete on
  public.profiles,
  public.threads,
  public.messages,
  public.thread_technique_state,
  public.thread_techniques_offered,
  public.thread_response_styles,
  public.thread_summaries,
  public.exercise_completions
to supabase_auth_admin;

create policy auth_admin_cascade_delete on public.profiles
  for delete to supabase_auth_admin using (true);
create policy auth_admin_cascade_delete on public.threads
  for delete to supabase_auth_admin using (true);
create policy auth_admin_cascade_delete on public.messages
  for delete to supabase_auth_admin using (true);
create policy auth_admin_cascade_delete on public.thread_technique_state
  for delete to supabase_auth_admin using (true);
create policy auth_admin_cascade_delete on public.thread_techniques_offered
  for delete to supabase_auth_admin using (true);
create policy auth_admin_cascade_delete on public.thread_response_styles
  for delete to supabase_auth_admin using (true);
create policy auth_admin_cascade_delete on public.thread_summaries
  for delete to supabase_auth_admin using (true);
create policy auth_admin_cascade_delete on public.exercise_completions
  for delete to supabase_auth_admin using (true);

-- The one side-effect trigger among the eight: sync_thread_message_count needs to update
-- threads, not delete it, when a message cascades away. An UPDATE grant on the written
-- columns was not sufficient on its own - `set message_count = message_count - 1` reads
-- the column it writes, and `where id = ...` reads id, so both need SELECT too. Verified
-- by reproducing the exact statement directly as supabase_auth_admin until it stopped
-- erroring, rather than granting broadly and hoping.
grant select (id, message_count) on public.threads to supabase_auth_admin;
grant update (message_count, last_message_at) on public.threads to supabase_auth_admin;
create policy auth_admin_cascade_message_count on public.threads
  for update to supabase_auth_admin using (true) with check (true);

-- admin has no RLS at all (by design - it is unreachable via PostgREST regardless), so
-- these three only need the grant, not a policy. admin is also invisible to PostgREST,
-- but that has no bearing on a direct Postgres role completing an internal cascade - it
-- still needs USAGE to reach the schema.
grant usage on schema admin to supabase_auth_admin;
grant delete on admin.crisis_events to supabase_auth_admin;
grant update (user_id) on admin.llm_calls to supabase_auth_admin;
grant update (created_by, updated_by) on admin.prompts to supabase_auth_admin;
grant update (created_by) on admin.prompt_versions to supabase_auth_admin;
