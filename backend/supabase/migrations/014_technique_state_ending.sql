-- ABOUTME: Records how a framework ended (resolved, pivoted or stopped), so the effectiveness outcome can carry it.
-- ABOUTME: One column on thread_technique_state; no new grant, the backend already writes the row.

-- Set on the turn a framework moves into the body check in, carried by every later write of the
-- row until the framework retires, and cleared when the row is written for a new offer. Spec 0010,
-- AC-6: a framework that got what it needs is resolved, one that stopped helping is pivoted, one
-- the person asked to stop is stopped.
--
-- No grant: mani_service already holds table-wide INSERT and UPDATE on this row, and
-- authenticated keeps SELECT only, so a person can read it and cannot change it.

alter table public.thread_technique_state
  add column ending text
  constraint technique_state_ending_known check (ending in ('resolved', 'pivoted', 'stopped'));
