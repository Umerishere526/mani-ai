-- ABOUTME: Ends the framework runs that were waiting at the body route's old final stage.
-- ABOUTME: Touches only the technique row's phase; no user, thread or message changes.

-- Before the somatic cadence of 2026-10-16 the last stage of every framework was somatic_practice,
-- and the next message after it ended the run. The cadence ends on somatic_helped, so a run left at
-- somatic_practice would never end and its thread could not be offered anything again. Clearing the
-- phase is what the next message would have done: an accepted row with no phase is a finished run,
-- and its stored stages stay.

update public.thread_technique_state
   set phase = null
 where outcome = 'accepted'
   and phase = 'somatic_practice';
