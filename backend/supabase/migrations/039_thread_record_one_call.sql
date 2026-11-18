-- ABOUTME: Reshapes each thread's record (threads.understanding) for the one-call turn: Mani's notes, the frameworks
-- ABOUTME: declined or finished, and the safety keys the pause rules read. Drops the old picture, readings and stores.

-- A conversation left at the body check-in, which is gone, is retired: its framework's questions were done, so it
-- counts as finished below.
update public.thread_technique_state
set phase = null
where phase like 'somatic\_%';

-- Declined and finished are rebuilt from the framework row, so a set a conversation declined or finished is never
-- offered to it again. Only the safety keys the kept pause rules read are carried over; every other key goes.
update public.threads t
set understanding = jsonb_strip_nulls(jsonb_build_object(
      'notes', '',
      'declined', coalesce((
        select jsonb_agg(s.framework_id) from public.thread_technique_state s
        where s.thread_id = t.id and s.outcome = 'declined'
      ), '[]'::jsonb),
      'finished', coalesce((
        select jsonb_agg(s.framework_id) from public.thread_technique_state s
        where s.thread_id = t.id and s.outcome = 'accepted' and s.phase is null
      ), '[]'::jsonb),
      'return_check', t.understanding -> 'return_check',
      'safety_settled', t.understanding -> 'safety_settled',
      'danger_reached', t.understanding -> 'danger_reached',
      'danger_about', t.understanding -> 'danger_about',
      'asked_about', t.understanding -> 'asked_about',
      'safety_end_check', t.understanding -> 'safety_end_check'
    )),
    -- An edit restores the snapshot taken before a turn; one taken before this change would restore the old shape.
    rewind_snapshot = null;
