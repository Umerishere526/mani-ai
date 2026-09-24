-- ABOUTME: Asserts the privilege model itself, so a later migration cannot quietly widen it.
-- ABOUTME: Uses has_*_privilege, which accounts for inheritance and PUBLIC grants.

\set ON_ERROR_STOP on

-- ---------------------------------------------------------------------------
-- Helper: one assertion, one message
-- ---------------------------------------------------------------------------

create or replace function pg_temp.want(claim text, actual boolean, expected boolean)
returns void
language plpgsql
as $$
begin
  if actual is distinct from expected then
    raise exception 'FAIL: % - expected %, got %', claim, expected, actual;
  end if;
  raise notice 'PASS: %', claim;
end;
$$;

-- Assertions are raised as notices on stderr; the function's own empty result rows
-- are not interesting, so send query output to nowhere.
\o /dev/null

-- ---------------------------------------------------------------------------
-- anon holds nothing at all in public
-- ---------------------------------------------------------------------------

do $$
declare
  t text;
  p text;
begin
  foreach t in array array['threads', 'messages', 'thread_summaries',
                           'thread_technique_state', 'thread_techniques_offered',
                           'thread_response_styles', 'exercise_completions']
  loop
    foreach p in array array['SELECT', 'INSERT', 'UPDATE', 'DELETE']
    loop
      if has_table_privilege('anon', 'public.' || t, p) then
        raise exception 'FAIL: anon holds % on public.%', p, t;
      end if;
    end loop;
  end loop;
  raise notice 'PASS: anon holds no privilege on any user table';
end
$$;

-- ---------------------------------------------------------------------------
-- authenticated holds exactly what the application needs, and nothing more
-- ---------------------------------------------------------------------------

select pg_temp.want('a signed-in user can read their threads',
  has_table_privilege('authenticated', 'public.threads', 'SELECT'), true);

select pg_temp.want('a signed-in user can start a thread',
  has_table_privilege('authenticated', 'public.threads', 'INSERT'), true);

select pg_temp.want('a signed-in user can read their messages',
  has_table_privilege('authenticated', 'public.messages', 'SELECT'), true);

-- The whole reason create_message_pair exists: a direct insert grant would let a user
-- write a convincing reply from Mani into their own thread and feed it back to the model.
select pg_temp.want('a user cannot insert messages directly',
  has_table_privilege('authenticated', 'public.messages', 'INSERT'), false);

select pg_temp.want('a user cannot edit a message after the fact',
  has_table_privilege('authenticated', 'public.messages', 'UPDATE'), false);

-- ---------------------------------------------------------------------------
-- The threads UPDATE grant is column-scoped
-- ---------------------------------------------------------------------------

select pg_temp.want('a user can rename their own thread',
  has_column_privilege('authenticated', 'public.threads', 'title', 'UPDATE'), true);

select pg_temp.want('a user cannot clear their own crisis flag',
  has_column_privilege('authenticated', 'public.threads', 'crisis_detected', 'UPDATE'), false);

select pg_temp.want('a user cannot rewrite their own message count',
  has_column_privilege('authenticated', 'public.threads', 'message_count', 'UPDATE'), false);

select pg_temp.want('a user cannot reassign a thread to someone else',
  has_column_privilege('authenticated', 'public.threads', 'user_id', 'UPDATE'), false);

-- The two columns migration 002 added, and the line between them: how Mani speaks is the
-- person's to choose, the pacing counter behind the vague-reply pivot is not. A user who
-- could write it could reset their own counter and never be moved off a vague loop.
select pg_temp.want('a user can choose their conversation style',
  has_column_privilege('authenticated', 'public.threads', 'conversation_style', 'UPDATE'),
  true);

select pg_temp.want('a user cannot reset their own vague streak',
  has_column_privilege('authenticated', 'public.threads', 'vague_streak', 'UPDATE'), false);

select pg_temp.want('the backend can move the vague streak',
  has_column_privilege('mani_service', 'public.threads', 'vague_streak', 'UPDATE'), true);

select pg_temp.want('a user can change their own nickname',
  has_column_privilege('authenticated', 'public.profiles', 'nickname', 'UPDATE'), true);

select pg_temp.want('a user cannot reassign their profile to another account',
  has_column_privilege('authenticated', 'public.profiles', 'user_id', 'UPDATE'), false);

-- A nickname is interpolated into the system prompt, so its length is a security
-- property, not cosmetics: unbounded, it is somewhere to paste instructions.
do $$
declare
  ok boolean;
begin
  select count(*) > 0 into ok
    from pg_constraint con
    join pg_class t on t.oid = con.conrelid
    join pg_namespace n on n.oid = t.relnamespace
   where n.nspname = 'public' and t.relname = 'profiles'
     and con.contype = 'c' and con.conname = 'profiles_nickname_sane';
  if not ok then
    raise exception 'FAIL: nickname has no length constraint';
  end if;
  raise notice 'PASS: nickname is length-capped';
end
$$;

-- ---------------------------------------------------------------------------
-- The admin schema is out of reach, except the shared catalog
-- ---------------------------------------------------------------------------

select pg_temp.want('anon cannot enter the admin schema',
  has_schema_privilege('anon', 'admin', 'USAGE'), false);

select pg_temp.want('a user cannot read prompts',
  has_table_privilege('authenticated', 'admin.prompts', 'SELECT'), false);

select pg_temp.want('a user cannot read prompt version history',
  has_table_privilege('authenticated', 'admin.prompt_versions', 'SELECT'), false);

select pg_temp.want('a user cannot read the call log',
  has_table_privilege('authenticated', 'admin.llm_calls', 'SELECT'), false);

select pg_temp.want('a user cannot read crisis events',
  has_table_privilege('authenticated', 'admin.crisis_events', 'SELECT'), false);

select pg_temp.want('a user cannot write crisis events',
  has_table_privilege('authenticated', 'admin.crisis_events', 'INSERT'), false);

-- The exercise catalog and the framework registry are shared content, not private data.
select pg_temp.want('a user can read the exercise catalog',
  has_table_privilege('authenticated', 'admin.exercises', 'SELECT'), true);

select pg_temp.want('a user cannot edit the exercise catalog',
  has_table_privilege('authenticated', 'admin.exercises', 'UPDATE'), false);

-- ---------------------------------------------------------------------------
-- The privileged paths belong to the backend's role, not to the user's
-- ---------------------------------------------------------------------------
-- A definer function that `authenticated` may call is a privilege `authenticated`
-- holds. create_message_pair takes Mani's words from its caller, so a user able to
-- call it can forge Mani's half of their own transcript - which is exactly what
-- withholding the INSERT grant on public.messages was meant to stop.

select pg_temp.want('a user cannot write a turn through the function',
  has_function_privilege('authenticated',
    'public.create_message_pair(uuid, text, text, text, jsonb, uuid)', 'EXECUTE'), false);

select pg_temp.want('a user cannot record a crisis through the function',
  has_function_privilege('authenticated',
    'public.mark_thread_crisis(uuid, text, uuid)', 'EXECUTE'), false);

select pg_temp.want('a user cannot write a greeting through the function',
  has_function_privilege('authenticated',
    'public.create_greeting(uuid, text, jsonb)', 'EXECUTE'), false);

select pg_temp.want('the backend can write a turn through the function',
  has_function_privilege('mani_service',
    'public.create_message_pair(uuid, text, text, text, jsonb, uuid)', 'EXECUTE'), true);

select pg_temp.want('the backend can record a crisis through the function',
  has_function_privilege('mani_service',
    'public.mark_thread_crisis(uuid, text, uuid)', 'EXECUTE'), true);

select pg_temp.want('the backend can write a greeting through the function',
  has_function_privilege('mani_service',
    'public.create_greeting(uuid, text, jsonb)', 'EXECUTE'), true);

-- `create or replace` would leave the old signature in place, still granted. Dropping
-- it explicitly is what migration 002 does; this is what catches a regression to that.
select pg_temp.want('the old two-argument greeting function is gone, not just re-pointed',
  to_regprocedure('public.create_greeting(uuid, text)') is null, true);

-- Clearing a finished technique is a backend decision. Both halves matter: without the
-- grant the delete raises, without the policy it silently matches nothing.
select pg_temp.want('the backend can clear technique state',
  has_table_privilege('mani_service', 'public.thread_technique_state', 'DELETE'), true);

-- Both feed the model: the summary goes into the system prompt, technique state into [ctx].
select pg_temp.want('a user cannot write their own summary',
  has_table_privilege('authenticated', 'public.thread_summaries', 'INSERT')
  or has_table_privilege('authenticated', 'public.thread_summaries', 'UPDATE')
  or has_any_column_privilege('authenticated', 'public.thread_summaries', 'UPDATE'), false);

select pg_temp.want('a user cannot write their own technique state',
  has_table_privilege('authenticated', 'public.thread_technique_state', 'INSERT')
  or has_table_privilege('authenticated', 'public.thread_technique_state', 'UPDATE')
  or has_any_column_privilege('authenticated', 'public.thread_technique_state', 'UPDATE'), false);

select pg_temp.want('the backend can write summaries and technique state',
  has_table_privilege('mani_service', 'public.thread_summaries', 'INSERT')
  and has_table_privilege('mani_service', 'public.thread_summaries', 'UPDATE')
  and has_table_privilege('mani_service', 'public.thread_technique_state', 'INSERT')
  and has_table_privilege('mani_service', 'public.thread_technique_state', 'UPDATE'), true);

-- Topics are written by the person and pasted into every system prompt.
select pg_temp.want('profile topics are bounded in the database, not only in the API',
  exists (select 1 from pg_constraint where conname = 'profiles_topics_bounded'), true);

-- Health data about the person, backend-only. Not even its owner reads it through the API.
select pg_temp.want('a user holds nothing on the memory kept about them',
  has_table_privilege('authenticated', 'admin.user_memory', 'SELECT')
  or has_table_privilege('authenticated', 'admin.user_memory', 'INSERT')
  or has_table_privilege('authenticated', 'admin.user_memory', 'UPDATE')
  or has_table_privilege('anon', 'admin.user_memory', 'SELECT'), false);

select pg_temp.want('the backend can read and write the memory',
  has_table_privilege('mani_service', 'admin.user_memory', 'SELECT')
  and has_table_privilege('mani_service', 'admin.user_memory', 'UPDATE'), true);

select pg_temp.want('the memory is row-scoped even for the backend',
  (select relrowsecurity from pg_class where oid = 'admin.user_memory'::regclass), true);

select pg_temp.want('a user cannot delete technique state directly',
  has_table_privilege('authenticated', 'public.thread_technique_state', 'DELETE'), false);

do $$
begin
  if not exists (
    select 1 from pg_policies
     where schemaname = 'public' and tablename = 'thread_technique_state'
       and cmd = 'DELETE'
  ) then
    raise exception 'FAIL: thread_technique_state has no DELETE policy, so the grant deletes nothing';
  end if;
  raise notice 'PASS: technique state has a DELETE policy behind the grant';
end
$$;

-- The separation is only real while PostgREST cannot assume the role.
do $$
begin
  if pg_has_role('authenticator', 'mani_service', 'USAGE') then
    raise exception 'FAIL: authenticator can assume mani_service, so PostgREST can too';
  end if;
  raise notice 'PASS: PostgREST cannot assume the backend role';
exception
  when undefined_object then
    raise notice 'SKIP: no authenticator role on this database';
end
$$;

select pg_temp.want('the backend role does not bypass RLS',
  (select rolbypassrls from pg_roles where rolname = 'mani_service'), false);

-- Postgres grants EXECUTE to PUBLIC by default, so these are only closed if the default
-- was explicitly revoked. Forgetting is how the previous project left its message-writing
-- RPC reachable by an unauthenticated caller.
select pg_temp.want('an unauthenticated caller cannot write a turn',
  has_function_privilege('anon',
    'public.create_message_pair(uuid, text, text, text, jsonb, uuid)', 'EXECUTE'), false);

select pg_temp.want('an unauthenticated caller cannot record a crisis',
  has_function_privilege('anon',
    'public.mark_thread_crisis(uuid, text, uuid)', 'EXECUTE'), false);

select pg_temp.want('an unauthenticated caller cannot write a greeting',
  has_function_privilege('anon', 'public.create_greeting(uuid, text, jsonb)', 'EXECUTE'), false);

do $$
declare
  r record;
begin
  for r in
    select p.proname, p.prosecdef, p.proconfig
      from pg_proc p
      join pg_namespace n on n.oid = p.pronamespace
     where n.nspname = 'public'
       and p.proname in ('create_message_pair', 'mark_thread_crisis', 'create_greeting',
                         'touch_updated_at', 'sync_thread_message_count',
                         'create_profile_for_new_user')
  loop
    -- An unpinned search_path on a definer function lets a caller shadow a table name
    -- and run their own code with the owner's privileges.
    if r.proconfig is null
       or not exists (select 1 from unnest(r.proconfig) c where c like 'search_path=%')
    then
      raise exception 'FAIL: %() does not pin its search_path', r.proname;
    end if;
  end loop;
  raise notice 'PASS: every function pins its search_path';
end
$$;

-- ---------------------------------------------------------------------------
-- Structural guarantees a later migration could forget
-- ---------------------------------------------------------------------------

do $$
declare
  missing text;
begin
  select string_agg(c.relname, ', ') into missing
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
   where n.nspname = 'public' and c.relkind = 'r' and not c.relrowsecurity;
  if missing is not null then
    raise exception 'FAIL: RLS is off on: %', missing;
  end if;
  raise notice 'PASS: every user table has RLS enabled';
end
$$;

do $$
declare
  missing text;
begin
  -- Postgres does not index a foreign key for you, and the absence shows up as slow
  -- joins and slow cascading deletes rather than as an error.
  select string_agg(format('%s.%s(%s)', n.nspname, t.relname, a.attname), ', ')
    into missing
    from pg_constraint con
    join pg_class t on t.oid = con.conrelid
    join pg_namespace n on n.oid = t.relnamespace
    join lateral unnest(con.conkey) with ordinality as k(attnum, ord) on true
    join pg_attribute a on a.attrelid = t.oid and a.attnum = k.attnum
   where con.contype = 'f'
     and n.nspname in ('public', 'admin')
     and k.ord = 1
     and not exists (
       select 1 from pg_index i
        where i.indrelid = con.conrelid
          and i.indkey[0] = k.attnum
     );
  if missing is not null then
    raise exception 'FAIL: foreign keys with no index: %', missing;
  end if;
  raise notice 'PASS: every foreign key is indexed';
end
$$;

-- purpose used to be free text holding the same three values mani/db/llm_calls.py's
-- Purpose enum has always been limited to - migration 006 made the database's contract
-- match the code's. Enum violations raise invalid_text_representation, not
-- check_violation, since this is a real Postgres type now, not a CHECK constraint.
do $$
begin
  begin
    insert into admin.llm_calls (purpose, model, outcome) values ('nonsense', 'x', 'ok');
    raise exception 'FAIL: an off-list llm_calls.purpose was stored';
  exception
    when invalid_text_representation then
      raise notice 'PASS: llm_calls.purpose is pinned to the set the code validates';
  end;
end
$$;
