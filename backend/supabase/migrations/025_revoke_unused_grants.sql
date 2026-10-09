-- ABOUTME: Revokes grants and drops policies that no code path uses, so every privilege left has a user.
-- ABOUTME: Privileges only shrink. RLS stays on everywhere, and anon still holds nothing.

-- mani_service inherits from authenticated, so each revoke from authenticated leaves it without
-- the privilege too. The account deletion cascade runs as supabase_auth_admin on its own grants
-- and policies (migration 005), which nothing here touches.

-- No code path deletes technique state: a finished technique is retired with an UPDATE.
revoke delete on public.thread_technique_state from mani_service;
drop policy technique_state_delete on public.thread_technique_state;

-- No code path deletes a thread: it is soft deleted by an UPDATE of deleted_at, which a user's
-- own token could otherwise skip through PostgREST.
revoke delete on public.threads from authenticated;
drop policy threads_delete on public.threads;

-- No code path deletes an offered technique. No DELETE policy was ever created for it.
revoke delete on public.thread_techniques_offered from authenticated;
drop policy if exists techniques_offered_delete on public.thread_techniques_offered;

-- No code path updates an exercise completion: completions are only inserted.
revoke update on public.exercise_completions from authenticated;
drop policy completions_update on public.exercise_completions;

-- No code path writes last_message_at: the trigger sync_thread_message_count does, on inserts
-- into messages made inside the definer functions or by the account cascade. The column
-- grants on title and deleted_at stay.
revoke update (last_message_at) on public.threads from authenticated;

-- No code path reads the framework registry as a user: it loads on the admin connection.
-- SELECT on admin.exercises stays.
revoke select on admin.frameworks from authenticated;

-- No DELETE grant on messages stands behind this policy, so it permits nothing; a future grant
-- should come with a policy chosen on purpose.
drop policy messages_delete on public.messages;
