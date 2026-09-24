-- ABOUTME: Auto-creates an empty public.profiles row when a new auth.users row appears.
-- ABOUTME: security definer because the role that inserts into auth.users holds no grant
-- ABOUTME: on public.profiles and should not be given one.

-- Supabase Auth's own Postgres role (supabase_auth_admin) inserts into auth.users and has
-- no reason to hold a grant on an app-owned table. security definer runs this as its
-- owner instead - the migration-applying role, which already owns public.profiles - so no
-- new GRANT is needed anywhere. No EXECUTE grant/revoke either: Postgres refuses to invoke
-- a `returns trigger` function via direct call regardless of grants, the same reason
-- touch_updated_at and sync_thread_message_count in 001 carry no grant lines.
--
-- on conflict do nothing is cheap insurance against any other path that inserts into
-- auth.users directly - the test harness and chat-tester both do.

create function public.create_profile_for_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (user_id)
  values (new.id)
  on conflict (user_id) do nothing;
  return new;
end;
$$;

create trigger create_profile_on_signup
  after insert on auth.users
  for each row execute function public.create_profile_for_new_user();
