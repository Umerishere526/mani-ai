-- ABOUTME: Records when Mani last checked its understanding with the person, on the thread.
-- ABOUTME: The offer gate: a framework is offered only on the turn right after that check (spec 0006).

-- The thread's message_count after the turn whose reply was Mani's latest check. The next turn is
-- the check's answer when message_count still equals it; any later turn finds the check used.
-- Null until the first check. It holds no words. Only mani_service may write it, as with
-- understanding in 022: a grant to authenticated would let the person open their own check
-- through PostgREST. The owner reads it through the existing select policy. A nullable add with
-- no default is a metadata change; no row is rewritten.

alter table public.threads
  add column check_at_message_count integer
    constraint threads_check_at_message_count_not_negative
      check (check_at_message_count >= 0);

grant update (check_at_message_count) on public.threads to mani_service;
