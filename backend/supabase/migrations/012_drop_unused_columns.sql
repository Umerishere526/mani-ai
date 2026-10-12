-- ABOUTME: Drops threads.vague_streak and admin.llm_calls.prompt_version_id, which nothing can use.
-- ABOUTME: Each column's CHECK, grant, foreign key and index go with it.

-- vague_streak counted vague replies so that two in a row forced a pivot. Whether a reply is vague
-- is the model's reading, not something code decides, so nothing reads or writes the counter.
--
-- prompt_version_id was meant to name the prompt that wrote a reply. A chat call is built from
-- several prompts, so one id cannot name them; which text was live at a given time is read from
-- admin.prompt_versions, which holds the version a prompt had until it was replaced.

alter table public.threads
  drop column vague_streak;

alter table admin.llm_calls
  drop column prompt_version_id;
