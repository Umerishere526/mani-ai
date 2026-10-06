-- ABOUTME: Keeps what a chat turn decided about offers and framework steps, so either can be traced afterwards.
-- ABOUTME: One jsonb column on admin.llm_calls; no new grant, the call log is written on the admin connection.

-- On a chat call: the framework the reply offered, why its offer was removed if it was, the step
-- it moved from and to, how a framework ended and how the person felt after the practice:
-- {"offered": "abcde", "refused": null, "step_from": null, "step_to": "offering",
--  "ending": null, "felt_after": null}.
-- Refusal codes: first_message, safety_concern, vetoed, cooling_down, finished, running,
-- unknown, another_question. Null on every other call.
--
-- Ids and codes only, never the person's words: this row outlives the person (their user and
-- thread are set null on delete), so their words must not be in it.

alter table admin.llm_calls
  add column decision jsonb;
