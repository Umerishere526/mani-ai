-- How many of Mani's replies have asked the stage now in `phase`: 1 when the phase is first
-- recorded, one more each reply that stays on it. A person who cannot answer a stage was asked
-- the same thing five times running, because nothing counted the asks; the backend now moves on
-- after two. Written by the backend, which already holds UPDATE on this table.

alter table public.thread_technique_state
  add column stage_asks smallint not null default 1
  constraint thread_technique_state_stage_asks_positive check (stage_asks >= 1);
