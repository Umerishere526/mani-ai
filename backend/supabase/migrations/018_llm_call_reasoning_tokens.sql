-- ABOUTME: Records the reasoning tokens of every model call in admin.llm_calls.
-- ABOUTME: They are part of output_tokens, never added on top of it.

-- A reasoning model thinks before it answers, and that thinking is billed as output. Without
-- this column the share of output spent thinking was dropped, so the cost of a reasoning
-- effort could not be measured. Numbered 018 rather than 011: hosted already carries 011 to
-- 017 from reverted branches, and a second migration under one of those numbers collides.
-- A constant default makes the add a metadata change; the table is not rewritten.

alter table admin.llm_calls
  add column reasoning_tokens integer not null default 0
    check (reasoning_tokens >= 0);
