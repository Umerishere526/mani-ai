-- ABOUTME: Adds stage_ledger to thread_technique_state, what is known of each stage of the running framework.
-- ABOUTME: Statuses and turn counts only, never a word the person wrote; the stage Mani asks is read from it.

-- The model reports each stage of the running framework as missing, partial or known in the same
-- call as its reply, and the backend stores the result here: {"<stage id>": {"status": ..., "turns": n}}.
-- The stored stage is the first one not known, so a story told before the offer is not asked again.
--
-- Named stage_ledger, never `known`: a hosted project still carries a `known` column on this table
-- from a reverted migration, and a second column of that name would collide with it.
--
-- No grant changes: mani_service already holds table wide insert and update here (migration 007),
-- and authenticated still holds neither.

alter table public.thread_technique_state
  add column stage_ledger jsonb not null default '{}'::jsonb
    constraint technique_state_stage_ledger_is_object check (jsonb_typeof(stage_ledger) = 'object');
