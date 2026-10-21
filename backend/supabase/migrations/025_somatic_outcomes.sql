-- ABOUTME: Records the two outcomes of the body check-in on the thread's technique row, each apart from the other.
-- ABOUTME: Also drops the library nudge flag, which the client's closing choices replace.

-- The physical response (what the exercise did for the body) and the conversation effect (whether the whole
-- conversation helped with what brought them) are separate outcomes and neither is derived from the other.
-- no_tension is a physical response too: they said there was nothing to ease. Both are null until the person
-- answers the step, hold no words, and are written only by mani_service through the table grant in 007; the
-- owner reads them through the existing select policy. A nullable add with no default is a metadata change.
alter table public.thread_technique_state
  add column physical_response text
    constraint thread_technique_state_physical_response_known
      check (physical_response in ('better', 'same', 'worse', 'no_tension')),
  add column conversation_effect text
    constraint thread_technique_state_conversation_effect_known
      check (conversation_effect in ('helped', 'somewhat', 'not_really'));

-- "Offer the Library before anything new" ended every framework with a nudge. The client's closing offers
-- Keep Chatting, Go to Library and Finish for Now in one message, so nothing is left to remember.
alter table public.thread_technique_state drop column library_offered_since;
