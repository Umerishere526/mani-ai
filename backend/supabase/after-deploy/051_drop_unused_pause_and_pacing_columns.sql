-- ABOUTME: Drops two columns nothing reads or writes: when a person said they were all right after a pause
-- ABOUTME: (chat_pauses.checked_at), and the vague-reply counter (threads.vague_streak), with what exists only for them.

-- Only the paused conversation asks after a pause now, so nothing records the answer on the pause row. The update
-- policy and mani_service's UPDATE grant served only that write: the backend inserts a pause and reads it, and
-- never changes one. Dropping the column takes its column grants (the person's SELECT among them) with it.
-- Run after the code of 2026-11-25 is live: the code before it reads checked_at on every turn. Moved into
-- supabase/migrations as 051 for the release after that one; `if exists` keeps it safe on a database that already
-- dropped them (muhammad's local one).
drop policy if exists chat_pauses_update on public.chat_pauses;
revoke update on public.chat_pauses from mani_service;
alter table public.chat_pauses drop column if exists checked_at;

-- The vague-reply pivot this counted for was never built (R138 is pending). Dropping the column drops its check
-- constraint and mani_service's column UPDATE grant.
alter table public.threads drop column if exists vague_streak;
