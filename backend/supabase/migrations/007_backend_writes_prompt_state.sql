-- ABOUTME: Moves writes to the two tables that feed the model from authenticated to mani_service.
-- ABOUTME: A user holding the anon key could otherwise write their own summary and framework state.

-- No client talks to these tables; only the backend does, as mani_service. Held by
-- authenticated, the grants were reachable through PostgREST with an ordinary user token:
--
--   thread_summaries        free text, placed in the *system* prompt on every later turn,
--                           so a user could write instructions to the model in its own voice.
--   thread_technique_state  outcome, phase and at_message_count drive [ctx]: a user could
--                           mark a framework accepted they never agreed to, or reset the
--                           cooldown that paces offers.
--
-- The same rule as .claude/SUPABASE.md: a privilege only the backend needs goes to
-- mani_service, never to authenticated. RLS still scopes mani_service to the caller's rows;
-- this narrows who may write, not which rows. SELECT stays with authenticated.

revoke insert, update on public.thread_summaries from authenticated;
revoke insert, update on public.thread_technique_state from authenticated;

grant insert, update on public.thread_summaries to mani_service;
grant insert, update on public.thread_technique_state to mani_service;
