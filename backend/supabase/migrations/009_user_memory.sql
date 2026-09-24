-- ABOUTME: A per-person memory of patterns across conversations, folded in as each one ends.
-- ABOUTME: Backend-written, admin-readable, never reachable by the person or PostgREST.

-- What a person has said about themselves across conversations - recurring themes, when
-- they feel low and the reasons they gave, what helps - so Mani can choose how to respond
-- without being told again. Never the conversations themselves: a new chat starts with no
-- messages from the last one. This is special-category health data, so:
--
--   * It lives in `admin`, which PostgREST never exposes, and authenticated holds nothing
--     on it. profiles would have been simpler, but a profile row is readable by its owner.
--   * Only mani_service - the backend acting for one person - may read or write it, and RLS
--     scopes that to the caller's own row, so a query that forgets its filter still cannot
--     reach anyone else's. Unlike the rest of admin, this table is per-person, so it gets
--     RLS like a public table does.
--   * It goes with the account: the FK cascades from auth.users.

create table admin.user_memory (
  user_id    uuid primary key references auth.users (id) on delete cascade,
  memory     jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

alter table admin.user_memory enable row level security;

create policy user_memory_select on admin.user_memory for select to mani_service
  using ((select auth.uid()) = user_id);
create policy user_memory_insert on admin.user_memory for insert to mani_service
  with check ((select auth.uid()) = user_id);
create policy user_memory_update on admin.user_memory for update to mani_service
  using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);

grant select, insert, update on admin.user_memory to mani_service;

-- Account deletion runs as supabase_auth_admin; RLS applies to it, as migration 005 found.
grant delete on admin.user_memory to supabase_auth_admin;
create policy auth_admin_cascade_delete on admin.user_memory
  for delete to supabase_auth_admin using (true);

-- When a thread's messages were last folded into memory. Null means never. A thread that
-- has had messages since (last_message_at later than this) is folded again from here.
alter table public.threads add column memory_folded_at timestamptz;
grant update (memory_folded_at) on public.threads to mani_service;

-- The fold is its own model call, recorded like every other.
alter type admin.llm_call_purpose add value 'memory_fold';
