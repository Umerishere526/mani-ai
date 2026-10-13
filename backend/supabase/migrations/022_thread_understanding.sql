-- ABOUTME: Stores what the person has told Mani so far (their feeling word and their issue) on the thread.
-- ABOUTME: Replaces thread_summaries.current_issue, which lagged the history window by a whole fold.

-- {"feeling": "...", "issue": "..."}, both keys optional, each at most 200 characters (enforced by
-- the backend's merge). It holds their own words about how they feel, so only mani_service may
-- write it, as vague_streak in 002: a grant to authenticated would let the person write their own
-- [ctx] through PostgREST. The owner reads it through the existing select policy, and it goes
-- with the thread row. A constant default makes the add a metadata change; no row is rewritten.

alter table public.threads
  add column understanding jsonb not null default '{}'::jsonb
    constraint threads_understanding_object
      check (jsonb_typeof(understanding) = 'object');

grant update (understanding) on public.threads to mani_service;

-- No backfill: there is no production data yet.
alter table public.thread_summaries
  drop column current_issue;
