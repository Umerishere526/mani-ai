-- ABOUTME: Keeps what each chat pause is for (an overdose, or whose danger it is), so a client can lead with 911
-- ABOUTME: after an overdose (R90). Additive: earlier pauses keep null, which clients read as unknown.

-- PROVISIONAL: clinician sign-off required before deploy.
-- Numbered 049: 043 is held by a stashed branch, 045 to 047 by the library and 048 by the docs stream.
alter table public.chat_pauses
  add column paused_for text
    constraint chat_pauses_paused_for_known
    check (paused_for in ('overdose', 'themselves', 'someone_else', 'from_someone', 'body'));

-- The person reads their own pause (the chat-tester and the apps show it); reason stays unreadable to them.
grant select (paused_for) on public.chat_pauses to authenticated;
