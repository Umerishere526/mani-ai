-- ABOUTME: Holds where a conversation stands on safety, so a concern outlives the reply that raised it.
-- ABOUTME: Adds the column; only mani_service writes it, as with understanding (022).

-- manasa's safety test, 2026-11-06: a concern was gone after one reply, so each time she pushed back Mani went back
-- to ordinary conversation without knowing she was safe. clear: nothing open. open: a concern raised and not yet
-- settled. unsafe: signs of danger now. The screen and the model's reading move it (chat/safety.py); it never locks
-- the conversation. A grant to authenticated would let the person close their own concern. A constant default on an
-- added column is a metadata change.
alter table public.threads
  add column safety text not null default 'clear'
    constraint threads_safety_state check (safety in ('clear', 'open', 'unsafe'));

grant update (safety) on public.threads to mani_service;
