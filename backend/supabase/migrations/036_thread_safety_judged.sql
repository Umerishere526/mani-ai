-- ABOUTME: Makes the conversation's safety state clear, unsure or danger: the model's judgment of whether anyone is
-- ABOUTME: in danger now, which code applies (chat/safety.py). Replaces open and unsafe from migration 033.

-- muhammad, 2026-11-10: the model judges from the whole conversation each turn whether anyone is in danger now; unsure
-- is a concern it cannot settle yet, danger is danger now. The old check goes first: it refuses the new values.
alter table public.threads drop constraint threads_safety_state;

update public.threads set safety = 'unsure' where safety = 'open';
update public.threads set safety = 'danger' where safety = 'unsafe';

-- A rewind snapshot holds the state a turn found; one taken before this carries the old names.
update public.threads
   set rewind_snapshot = jsonb_set(
         rewind_snapshot, '{safety}',
         to_jsonb(case rewind_snapshot ->> 'safety' when 'open' then 'unsure' else 'danger' end))
 where rewind_snapshot ->> 'safety' in ('open', 'unsafe');

alter table public.threads
  add constraint threads_safety_state check (safety in ('clear', 'unsure', 'danger'));
