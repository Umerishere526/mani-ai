-- ABOUTME: Stores what the person said for each stage of a framework, on the thread's technique row.
-- ABOUTME: Written by the backend after each turn, so it outlives the 20 message history window.

-- Keyed by framework id, then stage id: {"abcde": {"belief": {"said", "status", "tries"}}}. It
-- holds their own words about their state of mind, so it sits on a table only mani_service
-- writes (007), the owner reads it through the existing select policy, and it goes with the
-- thread through the cascade in 005. The insert and update grants in 007 are table wide and
-- cover the new column. A constant default makes the add a metadata change; no row is rewritten.

alter table public.thread_technique_state
  add column stages_known jsonb not null default '{}'::jsonb
    constraint thread_technique_state_stages_known_object
      check (jsonb_typeof(stages_known) = 'object');
