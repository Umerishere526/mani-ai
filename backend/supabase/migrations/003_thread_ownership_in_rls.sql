-- ABOUTME: Makes four thread-child tables check thread ownership, not just user_id, in RLS.
-- ABOUTME: Also pins response shape and voice to the closed sets the application validates.

-- `public.messages` has always checked both halves: that the row carries your user_id, and
-- that the thread it names is yours. The four tables below checked only the first, while
-- `authenticated` holds INSERT on all of them directly and `public` is exposed to PostgREST
-- (supabase/config.toml). So the backend was not the only door: anyone holding the anon key
-- and their own token could write a row carrying their own user_id onto someone else's
-- thread_id, and the FK made that succeed.
--
-- The damage is a write, not a read - every SELECT policy is still `auth.uid() = user_id`,
-- so nothing leaks. It is worse than it sounds anyway, because thread_id is the PRIMARY KEY
-- on thread_technique_state and thread_summaries: one inserted row permanently occupies the
-- victim's slot, their own upsert then fails the PK conflict, and the whole turn shares one
-- transaction - so the person loses their message and Mani's reply, on every turn, forever.
--
-- The fix is the clause messages_insert already uses. Forward-only: policies are dropped and
-- recreated rather than altered, so the new definition is what the file states rather than a
-- diff against something a reader has to go and look up.

drop policy if exists technique_state_insert on public.thread_technique_state;
create policy technique_state_insert on public.thread_technique_state for insert
  with check (
    (select auth.uid()) = user_id
    and exists (
      select 1 from public.threads t
       where t.id = thread_id and t.user_id = (select auth.uid())
    )
  );

drop policy if exists technique_state_update on public.thread_technique_state;
create policy technique_state_update on public.thread_technique_state for update
  using ((select auth.uid()) = user_id)
  with check (
    (select auth.uid()) = user_id
    and exists (
      select 1 from public.threads t
       where t.id = thread_id and t.user_id = (select auth.uid())
    )
  );

drop policy if exists techniques_offered_insert on public.thread_techniques_offered;
create policy techniques_offered_insert on public.thread_techniques_offered for insert
  with check (
    (select auth.uid()) = user_id
    and exists (
      select 1 from public.threads t
       where t.id = thread_id and t.user_id = (select auth.uid())
    )
  );

drop policy if exists response_styles_insert on public.thread_response_styles;
create policy response_styles_insert on public.thread_response_styles for insert
  with check (
    (select auth.uid()) = user_id
    and exists (
      select 1 from public.threads t
       where t.id = thread_id and t.user_id = (select auth.uid())
    )
  );

drop policy if exists summaries_insert on public.thread_summaries;
create policy summaries_insert on public.thread_summaries for insert
  with check (
    (select auth.uid()) = user_id
    and exists (
      select 1 from public.threads t
       where t.id = thread_id and t.user_id = (select auth.uid())
    )
  );

drop policy if exists summaries_update on public.thread_summaries;
create policy summaries_update on public.thread_summaries for update
  using ((select auth.uid()) = user_id)
  with check (
    (select auth.uid()) = user_id
    and exists (
      select 1 from public.threads t
       where t.id = thread_id and t.user_id = (select auth.uid())
    )
  );

-- `thread_techniques_offered` grants DELETE to `authenticated` but has no DELETE policy, so
-- the grant matches no rows and has never done anything. Left as it is: removing the grant is
-- a privilege change, and the safe state - deletes denied - is the one already in effect.

-- Shape and voice are closed sets in the application (mani/llm/schema.py SHAPES and VOICES,
-- enforced in repairs.apply before the write). The column accepted any text, so the database
-- held a looser contract than the code that writes to it - and this table is append-only, so
-- a bad value is never corrected.
--
-- Existing rows have to be reconciled before the constraint can hold, and the live data says
-- what that takes: of 435 rows, 35 carried an off-list voice. Two different faults, so two
-- different fixes.
--
-- Most were a capitalised form of a value that is on the list - the names are taught in the
-- prompt as "**Transitional**", so the model returned "Transitional". Those are lowercased:
-- the value was right and only its case was not, which is the same normalisation repairs.py
-- now applies before writing.
update public.thread_response_styles
   set voice = lower(voice)
 where voice is not null
   and lower(voice) in ('naming', 'receiving', 'quoting', 'transitional', 'observing')
   and voice <> lower(voice);

-- The rest named something that is not a mirroring voice at all - several were 'Supportive'
-- or 'Direct', which are conversation styles, from the turns where [ctx] never named the
-- style in force and the model reached for the nearest concept it had. There is no correct
-- value to recover, and voice is nullable by design ("Null if no mirroring"), so they become
-- null rather than a guess. The shape on those rows is untouched and still carries signal.
update public.thread_response_styles
   set voice = null
 where voice is not null
   and voice not in ('naming', 'receiving', 'quoting', 'transitional', 'observing');

alter table public.thread_response_styles
  add constraint response_styles_shape_known
  check (shape in ('warmth lead', 'honor and follow', 'mirror and ask',
                   'mirror and hold', 'gentle follow', 'presence only'));

alter table public.thread_response_styles
  add constraint response_styles_voice_known
  check (voice is null or voice in ('naming', 'receiving', 'quoting',
                                    'transitional', 'observing'));
