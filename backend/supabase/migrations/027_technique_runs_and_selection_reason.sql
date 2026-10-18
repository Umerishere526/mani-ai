-- ABOUTME: Records every finished framework run per thread, and why a framework was offered.
-- ABOUTME: Also drops threads.vague_streak, dead since the message-count offer gate it paced was removed.

-- `thread_technique_state` is one row per thread (its primary key is `thread_id` alone), so it only
-- ever remembers the single most recent run. With two active frameworks, offering "the other one"
-- after a completed run, while still holding that run's own cooldown, needs to know which
-- frameworks this thread has run and when - history the singleton row cannot hold (spec 0008).
--
-- Appended once, when a run's outcome is decided (accepted and finished, or declined), never
-- updated. The singleton row stays the live/most-recent state everything else already reads;
-- this table is additional, read only for the offer's exclusion set.
create table public.thread_technique_runs (
  id               uuid primary key default gen_random_uuid(),
  thread_id        uuid not null references public.threads (id) on delete cascade,
  user_id          uuid not null references auth.users (id) on delete cascade,
  framework_id     text not null references admin.frameworks (id) on delete restrict,
  outcome          public.technique_outcome not null,
  ended_at_message_count integer not null,
  created_at       timestamptz not null default now()
);

create index idx_technique_runs_thread on public.thread_technique_runs (thread_id, created_at desc);
create index idx_technique_runs_user on public.thread_technique_runs (user_id);
create index idx_technique_runs_framework on public.thread_technique_runs (framework_id);

alter table public.thread_technique_runs enable row level security;

create policy technique_runs_select on public.thread_technique_runs for select
  using ((select auth.uid()) = user_id);
-- Only the backend appends a run (mani_service), but the thread-ownership check still applies,
-- the same shape as thread_technique_state's (migration 003): a user token can never write
-- another user's thread_id into their own row.
create policy technique_runs_insert on public.thread_technique_runs for insert
  with check (
    (select auth.uid()) = user_id
    and exists (
      select 1 from public.threads t
       where t.id = thread_id and t.user_id = (select auth.uid())
    )
  );
create policy auth_admin_cascade_delete on public.thread_technique_runs
  for delete to supabase_auth_admin using (true);

grant select on public.thread_technique_runs to authenticated;
grant select, insert on public.thread_technique_runs to mani_service;
grant delete on public.thread_technique_runs to supabase_auth_admin;

-- Mani's own reading of why this framework fits what the person is dealing with, kept with the
-- run it was offered for the same reason `threads.understanding` is kept: readable by the admin
-- for reviewing selection quality, never logged, never read by the application logic that decides
-- anything (spec 0008). Nullable: a reply that confirms a check without filling it still offers.
alter table public.thread_technique_state
  add column offered_because text
    constraint thread_technique_state_offered_because_short
      check (char_length(offered_because) <= 200);

-- Dead since the message-count offer gate (spec 0006, 2026-10-13) replaced the pacing it counted
-- for; nothing in mani/ has read or written it since. Column only, caught in the spec 0008 cleanup.
alter table public.threads drop column vague_streak;
