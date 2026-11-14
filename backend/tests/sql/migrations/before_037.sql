-- ABOUTME: Rows as migration 036 left them, planted before 037 runs, so 037 is tested on data it has to backfill.
-- ABOUTME: A flagged thread with two crisis events, a flagged one with none, and a thread never flagged.

\set ON_ERROR_STOP on

insert into auth.users (id, email) values ('00000000-0000-0000-0000-00000000037a', 'migration-037@t.test');
insert into public.threads (id, user_id, crisis_detected, last_message_at) values
  ('00000000-0000-0000-0000-0000000037a1', '00000000-0000-0000-0000-00000000037a', true, '2026-03-05 10:00+00'),
  ('00000000-0000-0000-0000-0000000037a2', '00000000-0000-0000-0000-00000000037a', true, '2026-03-06 10:00+00'),
  ('00000000-0000-0000-0000-0000000037a3', '00000000-0000-0000-0000-00000000037a', false, '2026-03-07 10:00+00');
insert into admin.crisis_events (thread_id, user_id, reason, detected_at) values
  ('00000000-0000-0000-0000-0000000037a1', '00000000-0000-0000-0000-00000000037a', 'later', '2026-03-02 10:00+00'),
  ('00000000-0000-0000-0000-0000000037a1', '00000000-0000-0000-0000-00000000037a', 'first', '2026-03-01 10:00+00');
