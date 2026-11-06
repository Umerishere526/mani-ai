-- ABOUTME: Hides the thread state only the backend reads from the person's own role, and moves the catalog it alone
-- ABOUTME: reads off `authenticated`; the backend's role gets each. Also indexes the one foreign key that had none.

-- The reading a turn leaves for after its reply (pending_follow_up) carries the call's messages, system prompt
-- included; understanding and rewind_snapshot are Mani's working record of the person. The API hands none of them
-- out except in debug mode, and the Data API must not either: with their own token a person reads their thread's row.
revoke select on public.threads from authenticated;
grant select (id, user_id, title, message_count, crisis_detected, safety, conversation_style, created_at,
              last_message_at, deleted_at)
  on public.threads to authenticated;
grant select on public.threads to mani_service;

-- A privilege only the backend needs goes to mani_service, never to authenticated (.claude/SUPABASE.md). The
-- exercise catalog is served through the API, and the frameworks are the client's text.
revoke select on admin.exercises, admin.frameworks from authenticated;
revoke usage on schema admin from authenticated;
grant usage on schema admin to mani_service;
grant select on admin.exercises, admin.frameworks to mani_service;

-- EXECUTE on these stays with mani_service alone, whatever a project granted the API roles directly: each writes
-- under a privilege its caller must not hold (Mani's words, a crisis row, a greeting, the removal of a turn).
revoke all on function public.create_message_pair(uuid, text, text, text, jsonb, uuid) from anon, authenticated, service_role;
revoke all on function public.mark_thread_crisis(uuid, text, uuid) from anon, authenticated, service_role;
revoke all on function public.create_greeting(uuid, text, jsonb) from anon, authenticated, service_role;
revoke all on function public.delete_last_message_pair(uuid, uuid) from anon, authenticated, service_role;
-- Trigger functions: a trigger runs them whatever their grants, and nobody calls them.
revoke all on function public.create_profile_for_new_user() from anon, authenticated, service_role;
revoke all on function public.sync_thread_message_count() from anon, authenticated, service_role;
revoke all on function public.touch_updated_at() from anon, authenticated, service_role;

-- Every foreign key is indexed (.claude/SUPABASE.md): a cost record's deletion and a trace lookup by call scanned
-- the table without this.
create index if not exists idx_turn_traces_llm_call on admin.turn_traces (llm_call_id);
