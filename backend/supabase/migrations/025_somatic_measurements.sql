-- ABOUTME: Records the client's two measurements at the end of a framework, apart from each other.
-- ABOUTME: How their body felt after the exercise, and whether the whole conversation helped.

-- The client's somatic cadence (2026-10-16): "These are two separate outcomes and must be recorded
-- independently." One row per thread, so a later framework run replaces them. Written only by
-- mani_service, whose table wide update grant in 007 covers new columns. Nullable, no default:
-- the add is a metadata change.

alter table public.thread_technique_state
  add column body_response text
    constraint thread_technique_state_body_response_known
      check (body_response in ('better', 'same', 'worse', 'no_tension')),
  add column conversation_helped text
    constraint thread_technique_state_conversation_helped_known
      check (conversation_helped in ('helped', 'somewhat', 'not_helped'));
