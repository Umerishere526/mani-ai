-- ABOUTME: Asserts migration 037 gave each flagged thread the time of its latest crisis, or of its last message.
-- ABOUTME: Then removes the rows before_037.sql planted, so the suites after it start from the schema alone.

\set ON_ERROR_STOP on

do $$
declare
  got text;
begin
  select string_agg(right(id::text, 2) || '=' || coalesce(to_char(crisis_at at time zone 'utc', 'MM-DD'), 'null'), ' ' order by id)
    into got from public.threads where user_id = '00000000-0000-0000-0000-00000000037a';
  if got is distinct from 'a1=03-02 a2=03-06 a3=null' then
    raise exception 'FAIL: migration 037 backfilled crisis_at - got %', got;
  end if;
  raise notice 'PASS: migration 037 backfilled crisis_at from the latest crisis event, else the last message';
end;
$$;

delete from auth.users where id = '00000000-0000-0000-0000-00000000037a';
