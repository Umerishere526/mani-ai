-- ABOUTME: Drops the per-person memory across chats, and the prompt that folded it: every chat stands alone.
-- ABOUTME: The safety check after a pause still crosses chats; it reads chat_pauses, which stays.

-- muhammad, 2026-11-18: a new chat must carry nothing from an earlier one, even when the person comes back with the
-- same issue. Dropping the table deletes what was kept about every person; muhammad approved that the same day.

-- The table's policies and grants go with it.
drop table if exists admin.user_memory;

-- The column's grant to mani_service goes with it.
alter table public.threads drop column if exists memory_folded_at;

-- Its versions first: they hold the prompt row on delete restrict. Call logs that cite one keep their row, with
-- prompt_version_id set null.
delete from admin.prompt_versions
 where prompt_id in (select id from admin.prompts where name = 'memory_fold');
delete from admin.prompts where name = 'memory_fold';

-- admin.llm_call_purpose keeps 'memory_fold': old log rows carry it, and Postgres cannot drop an enum value.
