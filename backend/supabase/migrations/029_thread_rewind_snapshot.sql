-- ABOUTME: Keeps the thread state from before the latest turn, so that turn can be undone when its message is edited.
-- ABOUTME: Adds the snapshot column and the one function that deletes a person's last message with Mani's reply.

-- The state the latest turn is about to overwrite: the title, understanding, check position, framework
-- row and offered list, as JSON. Written at the start of every turn and cleared when it is used, so it
-- always describes exactly one turn back. Only mani_service may write it, as with understanding in 022:
-- a grant to authenticated would let the person plant state that a rewind then restores. The owner
-- reads it through the existing select policy. A nullable add with no default is a metadata change.
alter table public.threads add column rewind_snapshot jsonb;

grant update (rewind_snapshot) on public.threads to mani_service;

-- Deletes the person's last message and Mani's reply to it, and says what happened instead of raising,
-- so the backend can answer each refusal in words. It is a definer function because the person holds
-- no DELETE grant on messages: messages leave only through here, only as the last pair, only a typed
-- one (a tapped option has selected_prompt set). The messages_sync_count trigger lowers message_count.
create or replace function public.delete_last_message_pair(
  p_thread_id  uuid,
  p_message_id uuid
)
returns text
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_user_id uuid := auth.uid();
  v_message public.messages%rowtype;
  v_after   integer;
  v_reply   uuid;
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

  select * into v_message
    from public.messages m
   where m.id = p_message_id
     and m.thread_id = p_thread_id
     and m.user_id = v_user_id
     and m.role = 'user';
  if not found then
    return 'not_found';
  end if;

  if v_message.selected_prompt is not null then
    return 'tapped';
  end if;

  select count(*) into v_after
    from public.messages m
   where m.thread_id = p_thread_id and m.created_at > v_message.created_at;
  if v_after <> 1 then
    return 'not_last';
  end if;

  select m.id into v_reply
    from public.messages m
   where m.thread_id = p_thread_id
     and m.created_at > v_message.created_at
     and m.role = 'mani';
  if v_reply is null then
    return 'not_last';
  end if;

  delete from public.messages where id in (v_message.id, v_reply);
  return 'deleted';
end;
$$;

revoke all on function public.delete_last_message_pair(uuid, uuid) from public;
grant execute on function public.delete_last_message_pair(uuid, uuid) to mani_service;

-- A rewind takes back an offer the undone turn recorded. The table has carried a DELETE grant since 001
-- but no DELETE policy, so row security refused every delete. The policy is for mani_service alone: the
-- offered list holds what may not be offered again, so a person deleting from it would reopen offers.
create policy techniques_offered_delete on public.thread_techniques_offered
  for delete to mani_service
  using ((select auth.uid()) = user_id);
