-- ABOUTME: Counts the extra turns a framework stage has taken, so a stage can hold at most once.
-- ABOUTME: One column on thread_technique_state; no new grant, the backend already writes the row.

-- A framework stage normally moves on after one reply. It may take one extra turn: to say a
-- question again in simpler words, to offer one of the person's own options, or, in DBT STOP,
-- while they are acting on the urge. This is how many of those the stored stage has used.
-- The code sets it to 1 on a counted hold and back to 0 on every move, and refuses a second
-- hold by recording the next stage, so a conversation cannot loop on its own.
--
-- No grant: mani_service already holds table-wide INSERT and UPDATE on this row, and
-- authenticated keeps SELECT only, so a person can read the count and cannot change it.

alter table public.thread_technique_state
  add column holds smallint not null default 0
  constraint technique_state_holds_bounded check (holds between 0 and 1);
