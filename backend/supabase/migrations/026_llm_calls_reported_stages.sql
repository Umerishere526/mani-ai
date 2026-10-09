-- ABOUTME: Adds reported_stages and stage to admin.llm_calls, what a chat call reported of each stage and the stage stored.
-- ABOUTME: Stage ids and statuses only, never a word the person or the model wrote; read after a run to trace a stage.

-- reported_stages is {"<stage id>": "missing" | "partial" | "known"}, only the entries the guard kept
-- from the reply, whether or not the turn applied them. stage is the phase of the technique row the
-- turn wrote. Both are set by the backend in the same update that links the call to its message, and
-- both stay null on calls that are not a chat turn's and on chat turns with nothing to record.
--
-- No index: rows are read by thread_id, already indexed. No grant changes: the row is written on the
-- admin connection that already inserts it, and authenticated still holds nothing on admin.llm_calls.

alter table admin.llm_calls
  add column reported_stages jsonb
    constraint llm_calls_reported_stages_is_object check (jsonb_typeof(reported_stages) = 'object'),
  add column stage text;
