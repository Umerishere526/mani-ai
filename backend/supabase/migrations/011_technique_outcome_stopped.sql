-- ABOUTME: Adds 'stopped' to public.technique_outcome, for a framework the person ended mid-way.
-- ABOUTME: Kept apart from 'declined' (never started) and 'accepted' (run to its end).

alter type public.technique_outcome add value if not exists 'stopped';
