-- ABOUTME: Adds ending_from to thread_technique_state, the message count when a framework's ending began.
-- ABOUTME: The turn cap counts from it, so a framework the model never ends still retires.

-- The model ends a framework by setting `ending` on its reply. One that never does would hold
-- the framework, and block every new offer, for as long as the thread lasts. The backend
-- retires it once the person has sent ENDING_TURN_CAP messages since the ending began, counted
-- from this column. It is set on the first reply recorded in an ending phase, carried from the
-- stored row after that, and cleared only when the framework retires.
--
-- No grant changes: mani_service already holds table wide insert and update here (migration
-- 007), and authenticated still holds neither.

alter table public.thread_technique_state
  add column ending_from integer
    constraint technique_state_ending_from_not_negative check (ending_from >= 0);

-- Threads already in the ending when this runs start counting now, so they are capped too.
update public.thread_technique_state s
   set ending_from = t.message_count
  from public.threads t
 where t.id = s.thread_id
   and s.phase in ('somatic_checkin', 'somatic_practice');
