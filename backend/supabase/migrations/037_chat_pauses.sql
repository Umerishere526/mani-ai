-- ABOUTME: Adds the chat pause the backend starts after a crisis, and threads.crisis_at, when the last one happened.
-- ABOUTME: Both are the backend's alone: the person's own role reads its pauses, all but the reason, and writes none.

-- When a crisis was last flagged on the thread. The backend reads it with the table-wide SELECT mani_service
-- holds; it is not in the column list authenticated may read (034), as the person's role has no use for it.
alter table public.threads add column crisis_at timestamptz;

-- A flagged thread takes its latest crisis event's time; one with no event row takes its last message's.
update public.threads t
   set crisis_at = coalesce(
     (select max(e.detected_at) from admin.crisis_events e where e.thread_id = t.id),
     t.last_message_at)
 where t.crisis_detected and t.crisis_at is null;

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

  update public.threads
     set crisis_detected = true, crisis_at = now()
   where id = p_thread_id;

  insert into admin.crisis_events (thread_id, user_id, message_id, reason)
  values (p_thread_id, v_user_id, p_message_id, p_reason)
  returning id into v_event_id;

  return v_event_id;
end;
$$;

-- A pause on the person's chat. The person may read their own, all but its reason; only the backend starts or ends one.
create table public.chat_pauses (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references auth.users (id) on delete cascade,
  thread_id  uuid not null references public.threads (id) on delete cascade,
  started_at timestamptz not null default now(),
  ends_at    timestamptz not null,
  reason     text,
  checked_at timestamptz
);

create index idx_chat_pauses_user on public.chat_pauses (user_id);
create index idx_chat_pauses_thread on public.chat_pauses (thread_id);

alter table public.chat_pauses enable row level security;

create policy chat_pauses_select on public.chat_pauses for select
  using ((select auth.uid()) = user_id);
create policy chat_pauses_insert on public.chat_pauses for insert
  with check ((select auth.uid()) = user_id);
create policy chat_pauses_update on public.chat_pauses for update
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

-- Every column but `reason`, the model's line of why the pause started, which can carry their words: the Data API
-- hands a person their own row, and the backend reads the reason with mani_service's table-wide SELECT.
grant select (id, user_id, thread_id, started_at, ends_at, checked_at) on public.chat_pauses to authenticated;
grant select, insert, update on public.chat_pauses to mani_service;

-- Account deletion runs as supabase_auth_admin, which RLS applies to (migration 005).
grant delete on public.chat_pauses to supabase_auth_admin;
create policy auth_admin_cascade_delete on public.chat_pauses
  for delete to supabase_auth_admin using (true);
