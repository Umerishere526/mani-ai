-- One line, replaced each run: what the person is actually working on right now, distinct
-- from the fuller prose summary beside it. Added because a long conversation could lose track
-- of the person's actual issue - the summary paragraph buries it among everything else that
-- happened, so nothing forced it to stay in view. This column is the forcing function: the
-- composer puts it first, ahead of the prose, on every turn a summary exists.

alter table public.thread_summaries
  add column current_issue text;
