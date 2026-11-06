-- ABOUTME: Keeps the work a turn leaves for after its reply until the app asks for it with a request of its own.
-- ABOUTME: Adds the column; only mani_service writes it, as with understanding (022) and rewind_snapshot (029).

-- On Vercel the instance stops soon after a response is sent, and work started in the background then was cut off:
-- 15 of 49 readings after a reply, and memory folds that never wrote a row (latency report, 2026-11-05). The turn
-- now stores what is left to do here, keyed by Mani's reply: the reading's call, and whether the summary is due.
-- The app asks for it once the reply is shown, a request of its own, which runs to the end. Written on every turn
-- (set, or cleared) and cleared when taken, so at most one waits. A grant to authenticated would let the person plant
-- a prompt the backend then sends to the model. The owner reads it through the existing select policy. A nullable
-- add with no default is a metadata change.
alter table public.threads add column pending_follow_up jsonb;

grant update (pending_follow_up) on public.threads to mani_service;
