-- ABOUTME: Drops two columns nothing reads since the one-call turn: a framework's confirm phrases (the model writes its
-- ABOUTME: own words now) and when Mani last checked its understanding (no check is made any more).

alter table admin.frameworks drop column confirm_phrases;
alter table public.threads drop column check_at_message_count;
