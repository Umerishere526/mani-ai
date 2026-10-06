-- ABOUTME: Keeps what the person said when a framework was offered, so accepting it does not ask it again.
-- ABOUTME: One jsonb column on thread_technique_state; no new grant, the backend already writes the row.

-- The facts the router kept on the turn a framework was offered, each with the person's own
-- words: {"event": "the very next day i had an exam", ...}. The turn that accepts the offer
-- reads them to skip the stages those words already answer. Written with the offer and
-- replaced by the next write of the row, so it never outlives that turn's use.
--
-- No grant: mani_service already holds table-wide INSERT and UPDATE on this row, and
-- authenticated keeps SELECT only, so a person can read it and cannot change it.

alter table public.thread_technique_state
  add column known jsonb not null default '{}'::jsonb;
