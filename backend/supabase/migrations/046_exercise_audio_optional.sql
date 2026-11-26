-- ABOUTME: Lets an exercise exist before its recording does, so the library lists the client's unrecorded items.
-- ABOUTME: A null audio_path is an exercise the app shows as coming soon; the API never signs a link for it.

-- The client's library names 67 items, 36 of them "not yet recorded", and the whole Stress topic is unrecorded.
-- Dropping NOT NULL is a catalog-only change; no row is rewritten.
alter table admin.exercises alter column audio_path drop not null;
