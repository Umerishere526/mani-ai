-- ABOUTME: Stores how a person said they felt after the body practice that ends a framework, the client's effectiveness signal.
-- ABOUTME: One row per framework ending that got an answer; written only by the backend, read only by its owner.

-- Spec 0010, AC-8. The client wants to know whether a conversation had an effect, not only
-- whether it was finished, so the person's answer after the practice is kept with the framework,
-- the style and how the framework ended. No words are stored: the outcome is one of five values.
--
-- Health data (how someone felt after a mental health exercise), so RLS from creation, a policy
-- per operation, and the insert only through mani_service: a person must not be able to write
-- their own outcome through PostgREST. Nothing updates a row. Rows go with the account, the
-- thread or the message.

create table public.framework_outcomes (
  id                 uuid primary key default gen_random_uuid(),
  user_id            uuid not null references auth.users (id) on delete cascade,
  thread_id          uuid not null references public.threads (id) on delete cascade,
  -- The person's reply that reported it. Unique, so a retried turn writes no second row.
  message_id         uuid not null unique references public.messages (id) on delete cascade,
  framework_id       text not null references admin.frameworks (id) on delete restrict,
  conversation_style text not null
    constraint framework_outcomes_style_known
    check (conversation_style in ('direct', 'supportive', 'reflective')),
  ending             text not null
    constraint framework_outcomes_ending_known check (ending in ('resolved', 'pivoted', 'stopped')),
  body_place         text
    constraint framework_outcomes_place_known
    check (body_place in ('chest', 'head', 'stomach', 'elsewhere')),
  outcome            text not null
    constraint framework_outcomes_outcome_known
    check (outcome in ('better', 'mixed', 'unchanged', 'worse', 'unsure')),
  created_at         timestamptz not null default now(),
  -- A finished framework is never offered again in its thread, so a second row for the same
  -- ending of the same framework is a concurrent retry, not a real second outcome.
  constraint framework_outcomes_one_per_ending unique (thread_id, framework_id, ending)
);

create index idx_framework_outcomes_user on public.framework_outcomes (user_id, created_at desc);
create index idx_framework_outcomes_framework on public.framework_outcomes (framework_id);

alter table public.framework_outcomes enable row level security;

create policy framework_outcomes_select on public.framework_outcomes for select
  using ((select auth.uid()) = user_id);

create policy framework_outcomes_insert on public.framework_outcomes for insert
  with check (
    (select auth.uid()) = user_id
    and exists (
      select 1 from public.threads t
       where t.id = thread_id and t.user_id = (select auth.uid())
    )
  );

-- Account deletion cascades through this table as supabase_auth_admin, which needs both the
-- policy and the grant (migration 005).
create policy auth_admin_cascade_delete on public.framework_outcomes
  for delete to supabase_auth_admin using (true);

-- Supabase's default privileges hand new public tables to anon and authenticated; migration 001
-- revokes them for the tables it creates, and this table needs the same.
revoke all on public.framework_outcomes from anon, authenticated;
grant select on public.framework_outcomes to authenticated;
grant insert on public.framework_outcomes to mani_service;
grant delete on public.framework_outcomes to supabase_auth_admin;
