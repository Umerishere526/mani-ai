-- ABOUTME: Asserts migration 036 moved the rows before_036.sql planted to the states it names, snapshots too.
-- ABOUTME: Then removes them, so the suites after it start from the schema alone.

\set ON_ERROR_STOP on

do $$
declare
  got text;
begin
  select string_agg(right(id::text, 2) || '=' || safety || '/' || (rewind_snapshot ->> 'safety'), ' ' order by id)
    into got from public.threads where user_id = '00000000-0000-0000-0000-00000000036a';
  if got is distinct from 'a1=unsure/danger a2=danger/unsure a3=clear/clear' then
    raise exception 'FAIL: migration 036 moved open and unsafe rows and snapshots - got %', got;
  end if;
  raise notice 'PASS: migration 036 moved open and unsafe rows and their rewind snapshots';
end;
$$;

delete from auth.users where id = '00000000-0000-0000-0000-00000000036a';
