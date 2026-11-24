-- ABOUTME: Folds the two safety keys that named a worry's kind (danger_about, asked_about) into one, worry_about, kept
-- ABOUTME: only while the conversation's safety is open, so a settled worry's kind is not carried into the next.

-- Run after the code that reads worry_about is deployed: until then the old code still reads the two old keys.

-- An open question's kind (asked_about) wins over the kind of the danger reached before it, as both did while unsure.
update public.threads
set understanding = (understanding - 'danger_about' - 'asked_about')
      || case
           when safety <> 'clear' and coalesce(understanding ->> 'asked_about', understanding ->> 'danger_about') is not null
           then jsonb_build_object(
                  'worry_about', coalesce(understanding ->> 'asked_about', understanding ->> 'danger_about'))
           else '{}'::jsonb
         end
where understanding ? 'danger_about' or understanding ? 'asked_about';

-- An edit restores the snapshot taken before a turn; one taken before this change would restore the two old keys.
update public.threads
set rewind_snapshot = null
where rewind_snapshot is not null;
