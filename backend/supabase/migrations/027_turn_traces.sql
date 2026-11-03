-- ABOUTME: Records what code decided on each chat turn (moment, stage answers, walk notes, repairs, checks), so a
-- ABOUTME: review can say why a reply went the way it did. The model's raw reply is kept only in debug, for 14 days.

-- The career chat (2026-11-03): E stayed and the body check-in came twice, and nothing stored said why. The log lines
-- that did went to the console and were gone. `trace` holds decisions only: ids, statuses, closed values and code's
-- notes, never their words. `raw_reply` is the model's whole structured reply, which carries their words: written
-- only with AI_DEBUG_MODE on, and cleared once `raw_expires_at` passes (mani/db/turn_traces.py clears it on every
-- write). Both go with the thread or the message, as every other user-owned row does.
create table admin.turn_traces (
  id              uuid primary key default gen_random_uuid(),
  thread_id       uuid not null references public.threads (id) on delete cascade,
  message_id      uuid not null unique references public.messages (id) on delete cascade,
  llm_call_id     uuid references admin.llm_calls (id) on delete set null,
  trace           jsonb not null,
  raw_reply       jsonb,
  raw_expires_at  timestamptz,
  created_at      timestamptz not null default now(),
  constraint turn_traces_raw_expires check (raw_reply is null or raw_expires_at is not null)
);

create index idx_turn_traces_thread on admin.turn_traces (thread_id, created_at);
create index idx_turn_traces_raw_expires on admin.turn_traces (raw_expires_at) where raw_reply is not null;

-- The admin schema's default (migration 001): nothing for anon or authenticated, everything for service_role.
revoke all on admin.turn_traces from anon, authenticated;
grant all on admin.turn_traces to service_role;

-- Lets Supabase Auth complete the cascades above when it deletes a user (migration 005 explains why).
grant delete on admin.turn_traces to supabase_auth_admin;
