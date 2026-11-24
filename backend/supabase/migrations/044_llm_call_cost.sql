-- ABOUTME: Records what OpenRouter billed for every model call in admin.llm_calls, in US dollars.
-- ABOUTME: Null when the provider reported no cost, as on a call cut off before any reply came back.

-- OpenRouter returns the billed cost in each call's usage block, and the call already asks for it
-- (`usage.include`), but the row kept only the token counts, so a turn's cost had to be fetched from
-- OpenRouter's /generation endpoint one call at a time. Numbered 044 rather than 043: a stashed branch
-- holds a 043 of its own, and two migrations under one number collide.
-- A nullable add with no default is a metadata change; no row is rewritten.

alter table admin.llm_calls
  add column cost_usd numeric
    check (cost_usd >= 0);
