-- ABOUTME: Rows as migration 033 left them, planted before 036 runs, so 036 is tested on data it has to move.
-- ABOUTME: A thread at open and one at unsafe, each with a rewind snapshot holding the other name.

\set ON_ERROR_STOP on

insert into auth.users (id, email) values ('00000000-0000-0000-0000-00000000036a', 'migration-036@t.test');
insert into public.threads (id, user_id, safety, rewind_snapshot) values
  ('00000000-0000-0000-0000-0000000036a1', '00000000-0000-0000-0000-00000000036a', 'open', '{"safety": "unsafe"}'),
  ('00000000-0000-0000-0000-0000000036a2', '00000000-0000-0000-0000-00000000036a', 'unsafe', '{"safety": "open"}'),
  ('00000000-0000-0000-0000-0000000036a3', '00000000-0000-0000-0000-00000000036a', 'clear', '{"safety": "clear"}');
