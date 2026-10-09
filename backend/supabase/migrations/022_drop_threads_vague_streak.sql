-- ABOUTME: Drops threads.vague_streak, the counter behind a vague-reply pivot that no code reads or writes.
-- ABOUTME: Its check constraint and the mani_service column grant go with it.

-- Migration 002 added the column for a pacing counter the backend never came to use: it has
-- held 0 on every row since. Dropping the column also removes the column level UPDATE grant
-- to mani_service; the constraint is dropped by name first so the intent reads here.

alter table public.threads drop constraint threads_vague_streak_sane;
alter table public.threads drop column vague_streak;
