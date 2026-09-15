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
-- The two privileged paths are reachable, and are what they claim to be
-- ---------------------------------------------------------------------------

select pg_temp.want('a user can write a turn through the function',
  has_function_privilege('authenticated',
    'public.create_message_pair(uuid, text, text, text, jsonb, uuid)', 'EXECUTE'), true);

select pg_temp.want('a user can record a crisis through the function',
  has_function_privilege('authenticated',
    'public.mark_thread_crisis(uuid, text, uuid)', 'EXECUTE'), true);

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
  has_function_privilege('anon', 'public.create_greeting(uuid, text)', 'EXECUTE'), false);

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
                         'touch_updated_at', 'sync_thread_message_count')
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
