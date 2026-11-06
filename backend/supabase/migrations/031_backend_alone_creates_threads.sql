-- ABOUTME: Only the backend creates a thread or records an offered framework; a signed-in user's own token cannot.
-- ABOUTME: Revokes the table INSERT and DELETE grants authenticated held directly, and grants mani_service what it writes.

-- authenticated is what a user's own JWT reaches through PostgREST. With INSERT on threads it could create a row
-- with any understanding, rewind_snapshot, check_at_message_count, memory_folded_at or message_count, all of which
-- the backend reads back as its own state; with DELETE it could remove a thread outright rather than through the
-- backend's soft delete. Nothing in web/, mobile/ or chat-tester writes these tables directly (checked 2026-11-05):
-- every write goes through the backend.
revoke insert, delete on public.threads from authenticated;
revoke insert on public.thread_techniques_offered from authenticated;
revoke insert on public.thread_response_styles from authenticated;

-- mani_service inherited these through authenticated. The backend starts threads (db/threads.create_or_reuse) and
-- records which frameworks were offered (db/threads.apply); it writes no response styles.
grant insert on public.threads to mani_service;
grant insert on public.thread_techniques_offered to mani_service;
