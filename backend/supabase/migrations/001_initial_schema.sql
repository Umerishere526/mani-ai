-- ABOUTME: The complete Mani schema - user data in public, config and analytics in admin.
-- ABOUTME: Written fresh rather than squashed from the previous project's 24 migrations.

-- Two schemas. `public` holds user data and is exposed to PostgREST, so every table
-- in it carries RLS. `admin` holds configuration and analytics and is never added to
-- PostgREST's exposed schema list, so it is unreachable by the anon key regardless of
-- policy. FastAPI reaches both over a direct Postgres connection.
create schema if not exists admin;

-- ============================================================================
-- Enums
-- ============================================================================

create type public.message_role as enum ('user', 'mani');

create type public.technique_outcome as enum ('offered', 'accepted', 'declined');

create type admin.llm_call_outcome as enum (
  'ok',
  'schema_invalid',
  'provider_error',
  'timeout'
);

-- ============================================================================
-- admin.frameworks - the therapeutic techniques Mani can offer
-- ============================================================================
-- A registry rather than prose inside a prompt, so adding a framework is a content
-- change. `phases` is ordered; the state machine walks it and refuses transitions
-- that skip forward, which is why order is part of the data.

create table admin.frameworks (
  id                    text primary key,
  name                  text not null,
  summary               text not null,
  body                  text not null,
  activation_conditions text not null default '',
  phases                text[] not null,
  display_order         integer not null default 0,
  is_active             boolean not null default true,
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now(),
  constraint frameworks_phases_not_empty check (cardinality(phases) > 0),
  -- Every framework opens by offering itself; the orchestrator relies on it.
  constraint frameworks_first_phase_is_offering check (phases[1] = 'offering')
);

create index idx_frameworks_active on admin.frameworks (display_order)
  where is_active;

-- ============================================================================
-- admin.prompts - the layered system prompt, database-authoritative
-- ============================================================================
-- Markdown in prompts/ is seed input only. There is no `provider` column: OpenRouter
-- is the only provider and its key lives in the environment, never here.

create table admin.prompts (
  id               uuid primary key default gen_random_uuid(),
  name             text not null unique,
  description      text not null default '',
  content          text not null,
  -- The live version number. Without it the portal cannot say what is currently
  -- published, and computing the next one from max(prompt_versions.version) races.
  version          integer not null default 1,
  model_id         text,
  model_parameters jsonb not null default '{}'::jsonb,
  -- OpenRouter routing preferences, e.g. pinning an upstream provider.
  routing          jsonb not null default '{}'::jsonb,
  is_active        boolean not null default true,
  created_by       uuid references auth.users (id) on delete set null,
  -- Who last changed it. The previous schema recorded only the creator, which answers
  -- the wrong question once non-technical people are editing prompts.
  updated_by       uuid references auth.users (id) on delete set null,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  constraint prompts_version_positive check (version > 0)
);

create index idx_prompts_active on admin.prompts (name) where is_active;
create index idx_prompts_created_by on admin.prompts (created_by);
create index idx_prompts_updated_by on admin.prompts (updated_by);

-- A version is the complete record of what Mani was instructed to do at a point in time,
-- which is what makes llm_calls.prompt_version_id answerable after an incident. It
-- therefore captures the model as well as the text - the previous schema stored the text
-- and the model separately, so a snapshot could not say which model ran with it.
create table admin.prompt_versions (
  id               uuid primary key default gen_random_uuid(),
  prompt_id        uuid not null references admin.prompts (id) on delete restrict,
  version          integer not null,
  content          text not null,
  model_id         text,
  model_parameters jsonb not null default '{}'::jsonb,
  routing          jsonb not null default '{}'::jsonb,
  -- Why it changed, in the editor's words. Carried over from the previous schema, where
  -- it existed but was never written to. It matters more now the portal is authoritative.
  change_summary   text,
  created_by       uuid references auth.users (id) on delete set null,
  created_at       timestamptz not null default now(),
  unique (prompt_id, version)
);

-- `on delete restrict` above, deliberately: deleting a prompt previously cascaded its
-- version history away, destroying the only record of what Mani was instructed to do.
create index idx_prompt_versions_prompt on admin.prompt_versions (prompt_id, version desc);
create index idx_prompt_versions_created_by on admin.prompt_versions (created_by);

-- ============================================================================
-- admin.exercises - the audio library catalog
-- ============================================================================

create table admin.exercises (
  id                 uuid primary key default gen_random_uuid(),
  title              text not null,
  subtitle           text,
  description        text not null default '',
  type               text,
  category           text not null,
  audio_path         text not null,
  duration_minutes   numeric(5, 2),
  display_order      integer not null default 0,
  show_on_home_screen boolean not null default false,
  is_active          boolean not null default true,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now()
);

create index idx_exercises_category on admin.exercises (category, display_order)
  where is_active;
create index idx_exercises_home on admin.exercises (display_order)
  where is_active and show_on_home_screen;

-- ============================================================================
-- public.profiles - what onboarding collects
-- ============================================================================
-- The previous system kept this in Supabase auth user_metadata, which cost an Auth
-- Admin API call on every turn and, because the user can write that field themselves,
-- let an unbounded nickname reach the system prompt as an injection vector. Here it is
-- a table: joinable in the same round trip as the thread, and length-capped.
--
-- `topics` and `support_style` were collected at onboarding and reached nothing in the
-- old system. They have a home now; wiring them into the prompt is a later step.

create table public.profiles (
  user_id       uuid primary key references auth.users (id) on delete cascade,
  nickname      text,
  topics        text[] not null default '{}',
  support_style text,
  age_bracket   text,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  -- A nickname is interpolated into the system prompt. This is the length limit that
  -- stops it being a place to paste instructions.
  constraint profiles_nickname_sane
    check (nickname is null or char_length(nickname) between 1 and 40),
  constraint profiles_support_style_known
    check (support_style is null
           or support_style in ('supportive', 'reflective', 'direct'))
);

-- ============================================================================
-- public.threads
-- ============================================================================
-- `title` is unconstrained text. The previous schema capped it at varchar(100) while
-- the model schema enforced 50 and the consumer sliced to 100 - three disagreeing
-- limits, where exceeding the smallest destroyed the user's whole turn.

create table public.threads (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references auth.users (id) on delete cascade,
  title           text,
  message_count   integer not null default 0,
  crisis_detected boolean not null default false,
  created_at      timestamptz not null default now(),
  last_message_at timestamptz not null default now(),
  deleted_at      timestamptz
);

create index idx_threads_user_recent on public.threads (user_id, last_message_at desc)
  where deleted_at is null;

-- ============================================================================
-- public.messages
-- ============================================================================
-- `content` holds the clean user text. The hidden [ctx] metadata block is rebuilt per
-- turn and never stored, so history cannot replay stale contradictory context.

create table public.messages (
  id                uuid primary key default gen_random_uuid(),
  thread_id         uuid not null references public.threads (id) on delete cascade,
  user_id           uuid not null references auth.users (id) on delete cascade,
  role              public.message_role not null,
  content           text not null,
  prompt_options    jsonb,
  selected_prompt   text,
  client_message_id uuid,
  -- clock_timestamp(), not now(): now() is fixed for the whole transaction, so the two
  -- halves of a turn would share a timestamp and their order would be undefined.
  created_at        timestamptz not null default clock_timestamp(),
  constraint messages_content_not_empty check (length(trim(content)) > 0),
  -- Scoped to the user, so the idempotency lookup cannot be a global probe that
  -- returns a stranger's message.
  unique (user_id, client_message_id)
);

create index idx_messages_thread on public.messages (thread_id, created_at);
create index idx_messages_user on public.messages (user_id, created_at desc);

-- ============================================================================
-- Thread technique state - one row per thread, not six nullable columns
-- ============================================================================

create table public.thread_technique_state (
  thread_id              uuid primary key references public.threads (id) on delete cascade,
  user_id                uuid not null references auth.users (id) on delete cascade,
  framework_id           text not null references admin.frameworks (id) on delete restrict,
  outcome                public.technique_outcome not null,
  phase                  text,
  at_message_count       integer not null,
  library_offered_since  boolean not null default false,
  updated_at             timestamptz not null default now()
);

create index idx_technique_state_user on public.thread_technique_state (user_id);
create index idx_technique_state_framework on public.thread_technique_state (framework_id);

-- A table rather than a text[] column: the array was read-modify-written twice per
-- turn, losing updates under concurrency, and accumulated both display names and ids.
create table public.thread_techniques_offered (
  thread_id    uuid not null references public.threads (id) on delete cascade,
  framework_id text not null references admin.frameworks (id) on delete restrict,
  user_id      uuid not null references auth.users (id) on delete cascade,
  offered_at   timestamptz not null default clock_timestamp(),
  primary key (thread_id, framework_id)
);

create index idx_techniques_offered_user on public.thread_techniques_offered (user_id);
create index idx_techniques_offered_framework
  on public.thread_techniques_offered (framework_id);

-- Same reasoning: the rolling window of 7 was a jsonb array rewritten every turn.
create table public.thread_response_styles (
  id         uuid primary key default gen_random_uuid(),
  thread_id  uuid not null references public.threads (id) on delete cascade,
  user_id    uuid not null references auth.users (id) on delete cascade,
  shape      text not null,
  voice      text,
  -- Same reasoning as messages: the rolling window depends on real ordering.
  created_at timestamptz not null default clock_timestamp()
);

create index idx_response_styles_thread
  on public.thread_response_styles (thread_id, created_at desc);
create index idx_response_styles_user on public.thread_response_styles (user_id);

-- ============================================================================
-- public.thread_summaries
-- ============================================================================
-- `summarized_through_message_id` references messages. The previous implementation
-- wrote a summary row's own id into the equivalent column, so the next run silently
-- re-summarized the thread from the beginning.

create table public.thread_summaries (
  thread_id                     uuid primary key references public.threads (id) on delete cascade,
  user_id                       uuid not null references auth.users (id) on delete cascade,
  summary                       text,
  techniques_tried              jsonb not null default '[]'::jsonb,
  summarized_through_message_id uuid references public.messages (id) on delete set null,
  summarized_message_count      integer not null default 0,
  created_at                    timestamptz not null default now(),
  updated_at                    timestamptz not null default now(),
  constraint summaries_count_non_negative check (summarized_message_count >= 0)
);

create index idx_summaries_user on public.thread_summaries (user_id);
create index idx_summaries_through_message
  on public.thread_summaries (summarized_through_message_id);

-- ============================================================================
-- public.exercise_completions
-- ============================================================================

create table public.exercise_completions (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references auth.users (id) on delete cascade,
  exercise_id  uuid not null references admin.exercises (id) on delete cascade,
  helpful      boolean,
  completed_at timestamptz not null default now()
);

create index idx_completions_user on public.exercise_completions (user_id, completed_at desc);
create index idx_completions_exercise on public.exercise_completions (exercise_id);

-- ============================================================================
-- admin.crisis_events - measurable, unlike a boolean that overwrites itself
-- ============================================================================

create table admin.crisis_events (
  id          uuid primary key default gen_random_uuid(),
  thread_id   uuid not null references public.threads (id) on delete cascade,
  user_id     uuid not null references auth.users (id) on delete cascade,
  message_id  uuid references public.messages (id) on delete set null,
  reason      text not null,
  detected_at timestamptz not null default now(),
  resolution  text,
  resolved_at timestamptz
);

create index idx_crisis_events_detected on admin.crisis_events (detected_at desc);
create index idx_crisis_events_thread on admin.crisis_events (thread_id);
create index idx_crisis_events_user on admin.crisis_events (user_id);
create index idx_crisis_events_message on admin.crisis_events (message_id);
create index idx_crisis_events_unresolved on admin.crisis_events (detected_at desc)
  where resolved_at is null;

-- ============================================================================
-- admin.llm_calls - cost, latency, and the message to prompt-version link
-- ============================================================================
-- Without this there is no way, after an incident, to say what the system was
-- instructed to do or what a conversation cost.

create table admin.llm_calls (
  id                  uuid primary key default gen_random_uuid(),
  thread_id           uuid references public.threads (id) on delete set null,
  user_id             uuid references auth.users (id) on delete set null,
  message_id          uuid references public.messages (id) on delete set null,
  prompt_version_id   uuid references admin.prompt_versions (id) on delete set null,
  purpose             text not null,
  model               text not null,
  input_tokens        integer not null default 0,
  output_tokens       integer not null default 0,
  cached_input_tokens integer not null default 0,
  latency_ms          integer not null default 0,
  outcome             admin.llm_call_outcome not null,
  error_message       text,
  created_at          timestamptz not null default now()
);

create index idx_llm_calls_created on admin.llm_calls (created_at desc);
create index idx_llm_calls_user_created on admin.llm_calls (user_id, created_at desc);
create index idx_llm_calls_thread on admin.llm_calls (thread_id);
create index idx_llm_calls_message on admin.llm_calls (message_id);
create index idx_llm_calls_prompt_version on admin.llm_calls (prompt_version_id);

-- ============================================================================
-- Triggers
-- ============================================================================

create or replace function public.touch_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

create trigger frameworks_touch before update on admin.frameworks
  for each row execute function public.touch_updated_at();
create trigger prompts_touch before update on admin.prompts
  for each row execute function public.touch_updated_at();
create trigger exercises_touch before update on admin.exercises
  for each row execute function public.touch_updated_at();
create trigger technique_state_touch before update on public.thread_technique_state
  for each row execute function public.touch_updated_at();
create trigger summaries_touch before update on public.thread_summaries
  for each row execute function public.touch_updated_at();
create trigger profiles_touch before update on public.profiles
  for each row execute function public.touch_updated_at();

-- message_count is owned by this trigger, never by application code.
create or replace function public.sync_thread_message_count()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if tg_op = 'INSERT' then
    update public.threads
       set message_count = message_count + 1,
           last_message_at = new.created_at
     where id = new.thread_id;
  elsif tg_op = 'DELETE' then
    update public.threads
       set message_count = greatest(message_count - 1, 0)
     where id = old.thread_id;
  end if;
  return null;
end;
$$;

create trigger messages_sync_count
  after insert or delete on public.messages
  for each row execute function public.sync_thread_message_count();

-- ============================================================================
-- Row Level Security
-- ============================================================================
-- One policy per operation rather than a single `for all`, so a mistake is visible.
-- auth.uid() is wrapped in a subselect so Postgres caches it per statement.

alter table public.profiles                 enable row level security;
alter table public.threads                  enable row level security;
alter table public.messages                 enable row level security;
alter table public.thread_technique_state   enable row level security;
alter table public.thread_techniques_offered enable row level security;
alter table public.thread_response_styles   enable row level security;
alter table public.thread_summaries         enable row level security;
alter table public.exercise_completions     enable row level security;

create policy profiles_select on public.profiles for select
  using ((select auth.uid()) = user_id);
create policy profiles_insert on public.profiles for insert
  with check ((select auth.uid()) = user_id);
create policy profiles_update on public.profiles for update
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create policy threads_select on public.threads for select
  using ((select auth.uid()) = user_id);
create policy threads_insert on public.threads for insert
  with check ((select auth.uid()) = user_id);
create policy threads_update on public.threads for update
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);
create policy threads_delete on public.threads for delete
  using ((select auth.uid()) = user_id);

create policy messages_select on public.messages for select
  using ((select auth.uid()) = user_id);
create policy messages_insert on public.messages for insert
  with check (
    (select auth.uid()) = user_id
    and exists (
      select 1 from public.threads t
       where t.id = thread_id and t.user_id = (select auth.uid())
    )
  );
create policy messages_delete on public.messages for delete
  using ((select auth.uid()) = user_id);

create policy technique_state_select on public.thread_technique_state for select
  using ((select auth.uid()) = user_id);
create policy technique_state_insert on public.thread_technique_state for insert
  with check ((select auth.uid()) = user_id);
create policy technique_state_update on public.thread_technique_state for update
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);
-- Finishing a technique removes the row. The DELETE privilege is held by mani_service
-- alone, but the policy still has to exist or the delete matches nothing.
create policy technique_state_delete on public.thread_technique_state for delete
  using ((select auth.uid()) = user_id);

create policy techniques_offered_select on public.thread_techniques_offered for select
  using ((select auth.uid()) = user_id);
create policy techniques_offered_insert on public.thread_techniques_offered for insert
  with check ((select auth.uid()) = user_id);

create policy response_styles_select on public.thread_response_styles for select
  using ((select auth.uid()) = user_id);
create policy response_styles_insert on public.thread_response_styles for insert
  with check ((select auth.uid()) = user_id);

create policy summaries_select on public.thread_summaries for select
  using ((select auth.uid()) = user_id);
create policy summaries_insert on public.thread_summaries for insert
  with check ((select auth.uid()) = user_id);
create policy summaries_update on public.thread_summaries for update
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create policy completions_select on public.exercise_completions for select
  using ((select auth.uid()) = user_id);
create policy completions_insert on public.exercise_completions for insert
  with check ((select auth.uid()) = user_id);
create policy completions_update on public.exercise_completions for update
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

-- No UPDATE policy on messages, thread_techniques_offered or thread_response_styles:
-- a written turn is not editable by its author.
--
-- These policies are the active control, not decoration. The application runs ordinary
-- traffic - reads and writes both - as `mani_service` with the caller's claims set, so
-- Postgres enforces ownership even where an endpoint forgets its own filter. That is
-- the failure the previous system shipped: RLS existed, and a service-role client
-- walked past it.

-- ============================================================================
-- Privileged operations - the two writes a user must not be able to make directly
-- ============================================================================
-- Everything else is a plain DML grant below. These are security definer because they
-- write rows no plain grant should allow: Mani's side of a conversation, and a crisis
-- event in the admin schema.
--
-- Security definer is only half the control. EXECUTE on all three is granted to
-- mani_service and to nothing else, because a definer function that `authenticated`
-- may call is a privilege `authenticated` holds: the caller supplies p_mani_content
-- and the function writes it as Mani. Withholding the INSERT grant on public.messages
-- means nothing while the function that replaces it is reachable with a user's own JWT.

-- Writes both sides of a turn in one statement. Idempotent on client_message_id, so a
-- retried request returns the original pair instead of duplicating it.
create or replace function public.create_message_pair(
  p_thread_id         uuid,
  p_user_content      text,
  p_mani_content      text,
  p_selected_prompt   text default null,
  p_prompt_options    jsonb default null,
  p_client_message_id uuid default null
)
returns table (
  user_message_id uuid,
  mani_message_id uuid,
  created_at      timestamptz,
  was_duplicate   boolean
)
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_user_id  uuid := auth.uid();
  v_existing public.messages%rowtype;
  v_user_id_out uuid;
  v_mani_id_out uuid;
  v_created  timestamptz;
begin
  if v_user_id is null then
    raise exception 'no authenticated user' using errcode = '28000';
  end if;

  if not exists (
    select 1 from public.threads t
     where t.id = p_thread_id and t.user_id = v_user_id
  ) then
    raise exception 'thread does not belong to the caller' using errcode = '42501';
  end if;

  if p_client_message_id is not null then
    select * into v_existing
      from public.messages m
     where m.user_id = v_user_id
       and m.client_message_id = p_client_message_id
     limit 1;

    if found then
      return query
        select v_existing.id,
               -- The unique key is (user_id, client_message_id), so the original may
               -- sit in a different thread than the one this call names. Look for its
               -- reply where the original actually is, or the pair comes back half
               -- empty and the client renders a blank turn.
               (select m.id from public.messages m
                 where m.thread_id = v_existing.thread_id
                   and m.role = 'mani'
                   and m.created_at >= v_existing.created_at
                 order by m.created_at
                 limit 1),
               v_existing.created_at,
               true;
      return;
    end if;
  end if;

  insert into public.messages (thread_id, user_id, role, content, selected_prompt,
                               client_message_id)
  values (p_thread_id, v_user_id, 'user', p_user_content, p_selected_prompt,
          p_client_message_id)
  returning id, messages.created_at into v_user_id_out, v_created;

  insert into public.messages (thread_id, user_id, role, content, prompt_options)
  values (p_thread_id, v_user_id, 'mani', p_mani_content, p_prompt_options)
  returning id into v_mani_id_out;

  return query select v_user_id_out, v_mani_id_out, v_created, false;
end;
$$;

-- Writes Mani's opening line. Narrow on purpose: it refuses once the thread has any
-- message, so it cannot be used to insert arbitrary turns from Mani. That constraint is
-- what makes it safe to expose when a plain insert grant would not be.
create or replace function public.create_greeting(
  p_thread_id uuid,
  p_content   text
)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_user_id uuid := auth.uid();
  v_id      uuid;
begin
  if v_user_id is null then
    raise exception 'no authenticated user' using errcode = '28000';
  end if;

  if not exists (
    select 1 from public.threads t
     where t.id = p_thread_id and t.user_id = v_user_id
  ) then
    raise exception 'thread does not belong to the caller' using errcode = '42501';
  end if;

  if exists (select 1 from public.messages m where m.thread_id = p_thread_id) then
    raise exception 'thread has already started' using errcode = '42501';
  end if;

  insert into public.messages (thread_id, user_id, role, content)
  values (p_thread_id, v_user_id, 'mani', p_content)
  returning id into v_id;

  return v_id;
end;
$$;

-- Sets the flag and records the event. There is deliberately no way to clear the flag
-- from here: lifting a crisis lock is not a thing the person in crisis does.
create or replace function public.mark_thread_crisis(
  p_thread_id  uuid,
  p_reason     text,
  p_message_id uuid default null
)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_user_id uuid := auth.uid();
  v_event_id uuid;
begin
  if v_user_id is null then
    raise exception 'no authenticated user' using errcode = '28000';
  end if;

  if not exists (
    select 1 from public.threads t
     where t.id = p_thread_id and t.user_id = v_user_id
  ) then
    raise exception 'thread does not belong to the caller' using errcode = '42501';
  end if;

  update public.threads set crisis_detected = true where id = p_thread_id;

  insert into admin.crisis_events (thread_id, user_id, message_id, reason)
  values (p_thread_id, v_user_id, p_message_id, p_reason)
  returning id into v_event_id;

  return v_event_id;
end;
$$;

-- ============================================================================
-- Grants
-- ============================================================================

-- The role the backend acts as. It exists because the backend is the only thing that
-- talks to this database, and some of what it needs - writing Mani's half of a turn,
-- recording a crisis, clearing finished technique state - is exactly what a user must
-- not be able to do. While the backend acted as `authenticated`, every privilege it
-- needed was one the end user also held, reachable through PostgREST with their own
-- anon-key JWT.
--
-- RLS still applies to it: the policies above carry no TO clause, so they target
-- PUBLIC, and mani_service owns no tables and has no BYPASSRLS. It is a superset of
-- `authenticated`, not an escape from ownership checks.
do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'mani_service') then
    create role mani_service nologin;
  end if;
end
$$;

grant authenticated to mani_service;

-- The backend connects as `postgres` and switches with SET LOCAL ROLE, which needs
-- membership. Deliberately never granted to `authenticator`: PostgREST would then be
-- able to assume the role and the separation would be undone.
grant mani_service to postgres;

-- The admin schema is unreachable by users at all: configuration and analytics are not
-- theirs to read, and it is never added to PostgREST's exposed schema list.
revoke all on schema admin from anon, authenticated;
revoke all on all tables in schema admin from anon, authenticated;
grant usage on schema admin to service_role;
grant all on all tables in schema admin to service_role;

-- Exercises are a shared catalog, so signed-in users may read them.
grant usage on schema admin to authenticated;
grant select on admin.exercises, admin.frameworks to authenticated;

revoke all on all tables in schema public from anon, authenticated;
grant usage on schema public to anon, authenticated;

-- Ordinary traffic runs as `mani_service`, which inherits every grant below, and the
-- policies above apply to it - which is what makes them apply to real requests rather
-- than to nothing. These grants are also what `authenticated` may reach directly
-- through PostgREST, so they stay the floor, not the ceiling.
grant select, insert on public.profiles to authenticated;
-- user_id is excluded: a profile cannot be reassigned to another account.
grant update (nickname, topics, support_style, age_bracket) on public.profiles
  to authenticated;

grant select, insert, delete on public.threads to authenticated;
-- Column-restricted on purpose: message_count belongs to a trigger, and crisis_detected
-- must not be clearable by the person it protects.
grant update (title, last_message_at, deleted_at) on public.threads
  to authenticated;

-- No insert grant: messages are written only through create_message_pair, and EXECUTE
-- on that belongs to mani_service alone.
grant select on public.messages to authenticated;

grant select, insert, update on public.thread_technique_state to authenticated;
-- Removing the row is how a finished technique is cleared, which is the backend's
-- decision about the conversation, not the user's about their data.
grant delete on public.thread_technique_state to mani_service;
grant select, insert, delete on public.thread_techniques_offered to authenticated;
grant select, insert on public.thread_response_styles to authenticated;
grant select, insert, update on public.thread_summaries to authenticated;
grant select, insert, update on public.exercise_completions to authenticated;

-- Postgres grants EXECUTE to PUBLIC on every new function, so granting to a role is not
-- enough - the default has to be revoked first or anon can call it. That default is how
-- the previous project ended up with an unauthenticated caller able to reach its
-- message-writing RPC. Both functions do check auth.uid(), but a privilege should not
-- depend on the function body remembering to.
revoke all on function public.create_message_pair(uuid, text, text, text, jsonb, uuid)
  from public;
revoke all on function public.mark_thread_crisis(uuid, text, uuid) from public;
revoke all on function public.create_greeting(uuid, text) from public;

-- To mani_service and to nothing else. `authenticated` gets none of them: each one
-- takes content from its caller and writes it under privilege the caller does not have
-- - Mani's words, or a row in admin.crisis_events.
grant execute on function public.create_message_pair(uuid, text, text, text, jsonb, uuid)
  to mani_service;
grant execute on function public.mark_thread_crisis(uuid, text, uuid) to mani_service;
grant execute on function public.create_greeting(uuid, text) to mani_service;
