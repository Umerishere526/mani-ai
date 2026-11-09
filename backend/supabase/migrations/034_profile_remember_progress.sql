-- ABOUTME: Lets a person choose whether Mani carries what they worked through into later conversations.
-- ABOUTME: Adds the setting to profiles; the person may change it themselves, as with their nickname.

-- muhammad, 2026-11-06: progress memory (what they realised, what they planned to try, what they are still working
-- on) is carried across conversations, and the person has control over whether it is. On by default; turning it off
-- clears what was kept at the next fold and keeps nothing new. A constant default on an added column is a metadata
-- change.
alter table public.profiles add column remember_progress boolean not null default true;

grant update (remember_progress) on public.profiles to authenticated;
