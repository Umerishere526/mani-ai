-- ABOUTME: Makes admin.llm_calls.purpose a real enum, matching outcome on the same table.
-- ABOUTME: The application already treats it as a closed 3-value set (mani/db/llm_calls.py).

-- outcome was already admin.llm_call_outcome; purpose was free text holding the same three
-- values the code's own Purpose StrEnum has always been limited to. No CHECK constraint
-- meant the table's own contract was looser than the code that writes to it. Verified live
-- against the current data first: only 'chat' and 'summarize' appear, both valid.

create type admin.llm_call_purpose as enum ('chat', 'summarize', 'exercise_select');

alter table admin.llm_calls
  alter column purpose type admin.llm_call_purpose
  using purpose::admin.llm_call_purpose;
