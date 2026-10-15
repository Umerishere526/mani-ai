-- ABOUTME: Records OpenRouter's generation id for every model call in admin.llm_calls.
-- ABOUTME: The id is what tells which provider endpoint served a call, and how long it took there.

-- Routing picks among several endpoints, so a slow turn could not be traced to the one that served
-- it: the row held no provider (2026-10-14). OpenRouter's /generation endpoint resolves this id to
-- the provider, its latency and its generation time. Null when no reply came back, as on a timeout.
-- It holds no words. A nullable add with no default is a metadata change; no row is rewritten.

alter table admin.llm_calls
  add column generation_id text;
