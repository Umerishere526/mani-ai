-- ABOUTME: Drops admin.llm_calls.prompt_version_id and its index; no code path ever filled it.
-- ABOUTME: The call record keeps model, tokens, latency, outcome, error and the reply it produced.

-- Every call was recorded with prompt_version_id null, so the column recorded nothing. If tying
-- a call to the exact prompt version is wanted later, it comes back together with code that
-- fills it. Dropping the column also drops its foreign key to admin.prompt_versions.

drop index admin.idx_llm_calls_prompt_version;
alter table admin.llm_calls drop column prompt_version_id;
