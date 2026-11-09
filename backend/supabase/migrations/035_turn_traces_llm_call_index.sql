-- ABOUTME: Indexes admin.turn_traces(llm_call_id), the one foreign key migration 027 left without an index.
-- ABOUTME: Deleting an llm_calls row sets this column to null, which otherwise scans every trace.

create index idx_turn_traces_llm_call on admin.turn_traces (llm_call_id) where llm_call_id is not null;
