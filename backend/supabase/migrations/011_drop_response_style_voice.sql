-- ABOUTME: Drops thread_response_styles.voice, a column nothing can write a value into any more.
-- ABOUTME: Its CHECK constraint goes with it; the model reports a response shape only.

-- The model's Style carries only `shape` and the backend never supplies a voice, so every
-- row holds NULL and nothing reads the column. Dropping it also drops
-- response_styles_voice_known, which guards only this column.

alter table public.thread_response_styles
  drop column voice;
