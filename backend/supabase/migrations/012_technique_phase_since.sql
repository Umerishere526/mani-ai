-- ABOUTME: Records the thread's message count when the live framework stage began.
-- ABOUTME: Lets [ctx] tell Mani to move on from a stage that has been asked about three times.

alter table public.thread_technique_state
  add column phase_since integer check (phase_since >= 0);
