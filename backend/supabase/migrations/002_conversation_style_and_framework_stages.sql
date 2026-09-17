-- ABOUTME: The conversational layer's state - style per conversation, pacing, stage content.
-- ABOUTME: Additive. Every new column carries its own grant, because the existing one is
-- ABOUTME: column-scoped and a new column inherits nothing from it.

-- ============================================================================
-- public.threads - what this conversation sounds like, and how it is pacing
-- ============================================================================
-- The style is chosen per conversation rather than once at onboarding, so
-- profiles.support_style stays as the default rather than the answer. Same closed set,
-- deliberately: two spellings of one vocabulary is how the specifications drifted apart.

alter table public.threads
  add column conversation_style text,
  add column vague_streak       smallint not null default 0;

alter table public.threads
  add constraint threads_conversation_style_known
    check (conversation_style is null
           or conversation_style in ('supportive', 'reflective', 'direct'));

-- A counter, not a score: two vague replies in a row force a pivot.
alter table public.threads
  add constraint threads_vague_streak_sane
    check (vague_streak >= 0 and vague_streak <= 10);

-- `grant update (title, last_message_at, deleted_at) on public.threads` in 001 is
-- column-scoped. A new column is not covered by it, and the failure is a runtime 42501
-- that rolls back the whole turn - the message pair with it, not just the write that
-- was refused.
grant update (conversation_style) on public.threads to authenticated;

-- vague_streak is the backend's, not the user's. Writable by the person, they could
-- reset their own pivot counter and never be moved off a vague loop.
grant update (vague_streak) on public.threads to mani_service;

-- ============================================================================
-- admin.frameworks - the per-stage content
-- ============================================================================
-- Keyed by phase id, one entry per phase. Style varies at the `ask` leaf only:
-- listening cues, readiness and boundaries are clinical rather than tonal, so the
-- composer emits one `ask` resolved to the conversation's style, never three.
--
--   { "belief": { "purpose": …, "listen_for": …, "ready_when": …,
--                 "boundaries": …, "if_unclear": …,
--                 "ask": { "direct": …, "supportive": …, "reflective": … } } }
--
-- jsonb rather than its own table: the runtime reads one framework's content at a time
-- and never queries across frameworks. No new grant - admin.frameworks is already the
-- shared read-only catalog.

alter table admin.frameworks
  add column stages jsonb not null default '{}'::jsonb;

alter table admin.frameworks
  add constraint frameworks_stages_is_an_object
    check (jsonb_typeof(stages) = 'object');

-- The router's input: central indication, phrase lists weighted by confidence, and the
-- pairwise distinctions the specifications call out. `activation_conditions text` from
-- 001 cannot hold this - it is a single string, and the router needs structure to score
-- against. That column is left as-is and simply stops being read for routing.
--
--   { "central_indication": …, "strong_signals": […], "signals": […],
--     "not_when": …, "distinctions": { "other_framework_id": … } }

alter table admin.frameworks
  add column activation jsonb not null default '{}'::jsonb;

alter table admin.frameworks
  add constraint frameworks_activation_is_an_object
    check (jsonb_typeof(activation) = 'object');

-- ============================================================================
-- admin.exercises - which framework an exercise follows
-- ============================================================================
-- Null is the ordinary library exercise, which is most of them. Set, it is the exercise
-- offered when that framework finishes, so the person lands on the exercise itself
-- rather than on a category screen to go and find it.

alter table admin.exercises
  add column framework_id text references admin.frameworks (id) on delete set null;

-- Every foreign key gets an index; Postgres does not create one.
create index idx_exercises_framework on admin.exercises (framework_id, display_order)
  where is_active and framework_id is not null;

-- ============================================================================
-- public.create_greeting - the opening line now carries its style capsules
-- ============================================================================
-- The style is chosen by tapping one of three capsules on the greeting itself. A second
-- Mani message is not an option: this function refuses to write when the thread already
-- holds one, which is what makes it safe to expose at all.
--
-- A changed signature is a NEW function. `create or replace` would leave the two-argument
-- version in place, still granted and still callable, so it is dropped first.

drop function if exists public.create_greeting(uuid, text);

create function public.create_greeting(
  p_thread_id      uuid,
  p_content        text,
  p_prompt_options jsonb default null
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

  insert into public.messages (thread_id, user_id, role, content, prompt_options)
  values (p_thread_id, v_user_id, 'mani', p_content, p_prompt_options)
  returning id into v_id;

  return v_id;
end;
$$;

-- Postgres grants EXECUTE on a new function to PUBLIC by default. Closing that is the
-- whole point of the privilege model in 001, and a new signature reopens it every time.
revoke all on function public.create_greeting(uuid, text, jsonb) from public;
grant execute on function public.create_greeting(uuid, text, jsonb) to mani_service;
