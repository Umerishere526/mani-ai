-- What Mani makes of the person, carried from one turn to the next: what it thinks is going on
-- underneath what they said, and the one thing that would tell it whether it has that right.
-- Written every turn by the backend, inside the turn's own transaction, unlike `summary` and
-- `current_issue`, which the background summarization writes once a conversation passes twenty
-- messages. Without it every turn forms its reading from nothing, so a person answering "idk" or
-- "everything" was asked the same two possibilities three times running (muhammad, 2026-10-13).
--
-- The two writers share the row and never share a column: each names only its own in its
-- `do update set`. If summarization is ever changed to upsert the whole row, this column is the
-- one it would silently blank.

alter table public.thread_summaries
  add column working_read text;
