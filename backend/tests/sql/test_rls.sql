-- ABOUTME: Proves RLS isolates users and that privileged writes cannot be forged.
-- ABOUTME: Run against a database with test_harness.sql and 001_initial_schema.sql applied.

\set ON_ERROR_STOP on

\set alice '''a0000000-0000-4000-8000-00000000000a'''
\set bob   '''a0000000-0000-4000-8000-00000000000b'''
\set alice_thread '''11111111-0000-4000-8000-000000000001'''
\set bob_thread   '''22222222-0000-4000-8000-000000000002'''

-- ---------------------------------------------------------------------------
-- Fixtures, created with privileges so the test is about access, not setup.
-- Cleared first so a run that aborted partway does not block the next one.
-- ---------------------------------------------------------------------------

delete from admin.crisis_events where user_id in (:alice, :bob);
delete from public.messages where user_id in (:alice, :bob);
delete from public.threads where user_id in (:alice, :bob);
delete from auth.users where id in (:alice, :bob);

insert into auth.users (id, email) values
  (:alice, 'alice@example.test'),
  (:bob, 'bob@example.test');

-- `do nothing` because a seeded database already has this row, and the seeded copy
-- is the one the application uses. The test only needs it to exist.
insert into admin.frameworks (id, name, summary, body, phases) values
  ('thought_reframing', 'Thought Reframing', 'Reframe a painful thought.', '...',
   array['offering', 'surface', 'externalize', 'explore', 'land', 'ground'])
on conflict (id) do nothing;

insert into public.threads (id, user_id, title) values
  (:alice_thread, :alice, 'Alice thread'),
  (:bob_thread, :bob, 'Bob thread');

insert into public.messages (thread_id, user_id, role, content) values
  (:alice_thread, :alice, 'user', 'something Alice would only tell Mani'),
  (:bob_thread, :bob, 'user', 'something Bob would only tell Mani');

-- ---------------------------------------------------------------------------
-- Reads are isolated
-- ---------------------------------------------------------------------------

begin;
set local role authenticated;
set local request.jwt.claims = '{"sub":"a0000000-0000-4000-8000-00000000000a"}';

do $$
declare
  n integer;
begin
  select count(*) into n from public.threads;
  if n <> 1 then raise exception 'Alice sees % threads, expected 1', n; end if;

  select count(*) into n from public.messages;
  if n <> 1 then raise exception 'Alice sees % messages, expected 1', n; end if;

  -- The exact shape of the previous system's live defect: select by thread id with no
  -- ownership filter. RLS must return nothing regardless of the missing filter.
  select count(*) into n from public.messages
   where thread_id = '22222222-0000-4000-8000-000000000002';
  if n <> 0 then raise exception 'Alice read % of Bob''s messages', n; end if;

  raise notice 'PASS: reads are isolated to the calling user';
end
$$;
rollback;

-- ---------------------------------------------------------------------------
-- Ordinary writes work as the user, and RLS scopes them
-- ---------------------------------------------------------------------------

begin;
set local role authenticated;
set local request.jwt.claims = '{"sub":"a0000000-0000-4000-8000-00000000000a"}';

do $$
begin
  insert into public.threads (user_id, title)
  values ('a0000000-0000-4000-8000-00000000000a', 'a thread Alice starts');
  raise notice 'PASS: a user can create their own thread';

  insert into public.thread_technique_state
    (thread_id, user_id, framework_id, outcome, phase, at_message_count)
  values ('11111111-0000-4000-8000-000000000001',
          'a0000000-0000-4000-8000-00000000000a',
          'thought_reframing', 'offered', 'offering', 2);
  raise notice 'PASS: a user can write their own technique state';

  begin
    insert into public.threads (user_id, title)
    values ('a0000000-0000-4000-8000-00000000000b', 'a thread in Bob''s name');
    raise exception 'FAIL: Alice created a thread owned by Bob';
  exception
    when insufficient_privilege then
      raise notice 'PASS: a user cannot create rows owned by someone else';
  end;
end
$$;
rollback;

-- ---------------------------------------------------------------------------
-- The two writes a user must not be able to make directly
-- ---------------------------------------------------------------------------

begin;
set local role authenticated;
set local request.jwt.claims = '{"sub":"a0000000-0000-4000-8000-00000000000a"}';

do $$
begin
  begin
    insert into public.messages (thread_id, user_id, role, content)
    values ('11111111-0000-4000-8000-000000000001',
            'a0000000-0000-4000-8000-00000000000a', 'mani', 'forged reply from Mani');
    raise exception 'FAIL: a user forged a message from Mani';
  exception
    when insufficient_privilege then
      raise notice 'PASS: Mani''s side of a conversation cannot be forged';
  end;

  begin
    update public.threads set crisis_detected = false
     where id = '11111111-0000-4000-8000-000000000001';
    raise exception 'FAIL: a user cleared their own crisis flag';
  exception
    when insufficient_privilege then
      raise notice 'PASS: a user cannot clear their own crisis flag';
  end;

  begin
    perform 1 from admin.prompts;
    raise exception 'FAIL: a user read admin.prompts';
  exception
    when insufficient_privilege then
      raise notice 'PASS: the admin schema is unreachable by users';
  end;
end
$$;
rollback;

-- ---------------------------------------------------------------------------
-- create_message_pair: writes both sides, is idempotent, refuses other threads
-- ---------------------------------------------------------------------------

begin;
set local role authenticated;
set local request.jwt.claims = '{"sub":"a0000000-0000-4000-8000-00000000000a"}';

do $$
declare
  first_call  record;
  second_call record;
  roles       text;
begin
  select * into first_call from public.create_message_pair(
    '11111111-0000-4000-8000-000000000001',
    'I had a hard day',
    'That sounds heavy. What happened?',
    null, null,
    '33333333-0000-4000-8000-000000000003'
  );
  if first_call.was_duplicate then
    raise exception 'FAIL: a first write reported itself as a duplicate';
  end if;

  select string_agg(m.role::text, ',' order by m.created_at, m.role) into roles
    from public.messages m
   where m.id in (first_call.user_message_id, first_call.mani_message_id);
  if roles is distinct from 'mani,user' and roles is distinct from 'user,mani' then
    raise exception 'FAIL: expected a user and a mani row, got [%]', roles;
  end if;
  raise notice 'PASS: a turn writes both sides';

  -- A retried request must not double-write.
  select * into second_call from public.create_message_pair(
    '11111111-0000-4000-8000-000000000001',
    'I had a hard day',
    'a different reply entirely',
    null, null,
    '33333333-0000-4000-8000-000000000003'
  );
  if not second_call.was_duplicate then
    raise exception 'FAIL: a retry was written a second time';
  end if;
  if second_call.user_message_id <> first_call.user_message_id then
    raise exception 'FAIL: a retry returned a different message';
  end if;
  raise notice 'PASS: a retried turn is idempotent';

  begin
    perform public.create_message_pair(
      '22222222-0000-4000-8000-000000000002', 'writing into Bob''s thread', 'reply'
    );
    raise exception 'FAIL: Alice wrote into Bob''s thread';
  exception
    when insufficient_privilege then
      raise notice 'PASS: a turn cannot be written into another user''s thread';
  end;
end
$$;
rollback;

-- ---------------------------------------------------------------------------
-- mark_thread_crisis: records the event, refuses other threads
-- ---------------------------------------------------------------------------

begin;
set local role authenticated;
set local request.jwt.claims = '{"sub":"a0000000-0000-4000-8000-00000000000a"}';

do $$
declare
  event_id uuid;
  flagged  boolean;
begin
  event_id := public.mark_thread_crisis(
    '11111111-0000-4000-8000-000000000001', 'expressed suicidal ideation'
  );

  select t.crisis_detected into flagged
    from public.threads t where t.id = '11111111-0000-4000-8000-000000000001';
  if not flagged then raise exception 'FAIL: the thread was not flagged'; end if;
  raise notice 'PASS: a crisis flags the thread and returns event %', event_id;

  begin
    perform public.mark_thread_crisis(
      '22222222-0000-4000-8000-000000000002', 'flagging someone else''s thread'
    );
    raise exception 'FAIL: Alice flagged Bob''s thread';
  exception
    when insufficient_privilege then
      raise notice 'PASS: a crisis cannot be recorded against another user''s thread';
  end;
end
$$;
rollback;

-- ---------------------------------------------------------------------------
-- Symmetry, and no JWT means no rows
-- ---------------------------------------------------------------------------

begin;
set local role authenticated;
set local request.jwt.claims = '{"sub":"a0000000-0000-4000-8000-00000000000b"}';
do $$
declare
  titles text;
begin
  select string_agg(title, ',') into titles from public.threads;
  if titles is distinct from 'Bob thread' then
    raise exception 'Bob sees threads [%], expected only his own', titles;
  end if;
  raise notice 'PASS: isolation is symmetric';
end
$$;
rollback;

begin;
set local role authenticated;
do $$
declare
  n integer;
begin
  select count(*) into n from public.threads;
  if n <> 0 then raise exception 'A caller with no JWT saw % threads', n; end if;
  raise notice 'PASS: no JWT means no rows';
end
$$;
rollback;

-- ---------------------------------------------------------------------------
-- Cleanup
-- ---------------------------------------------------------------------------

-- Scoped to the fixtures by id. This file is also run against a real local Supabase,
-- where an unqualified `delete from auth.users` would take real accounts with it.
-- Scoped to the fixtures by id. This file also runs against a real local Supabase,
-- where an unqualified delete would take real accounts and seeded config with it.
-- admin.frameworks is deliberately left alone: the row may be seeded application data.
delete from admin.crisis_events where user_id in (:alice, :bob);
delete from public.messages where user_id in (:alice, :bob);
delete from public.threads where user_id in (:alice, :bob);
delete from auth.users where id in (:alice, :bob);
