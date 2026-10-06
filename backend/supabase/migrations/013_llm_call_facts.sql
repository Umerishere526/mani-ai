-- ABOUTME: Keeps what the router read from a chat draft's facts, so a missing or wrong offer can be traced afterwards.
-- ABOUTME: One jsonb column on admin.llm_calls; no new grant, the call log is written on the admin connection.

-- On a chat call whose facts were read: the fact ids the model reported, how many ids it made up,
-- the facts the fit was chosen from, the words check's note for each one dropped, and what they
-- pointed to:
-- {"reported": ["stuck"], "unknown": 0, "facts": [], "pick": null, "leading": null,
--  "missing": null, "stuck_route": false,
--  "dropped": ["dropped a fact not in their words: stuck"]}.
-- Null on every other call, including a redraft, whose facts are never read.
--
-- Ids and notes only, never the quoted words: this row outlives the person (their user and
-- thread are set null on delete), so their words must not be in it.

alter table admin.llm_calls
  add column facts jsonb;
