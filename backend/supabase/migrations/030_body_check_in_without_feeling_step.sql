-- ABOUTME: Moves any conversation waiting on the body check-in's feeling question to the client's Step 1, which
-- ABOUTME: replaced it (muhammad, 2026-11-04), so no thread is left on a step that no longer exists.

update public.thread_technique_state
set phase = 'somatic_body'
where phase = 'somatic_check';
