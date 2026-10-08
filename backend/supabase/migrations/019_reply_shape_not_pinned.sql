-- ABOUTME: Drops the check that pinned a stored reply shape to the six written in migration 003.
-- ABOUTME: The shapes are listed in the mani_base prompt, and the guard keeps a reply to that list.

-- The six shapes were in three places: the prompt that teaches them, a constant in the code, and
-- this check. The list now lives only in the mani_base prompt's reply_shapes, read at cache load,
-- and guards.check drops any shape not on it before the write. Left in place, this check would
-- let a shape added in content pass the guard and then fail the turn's insert, losing the turn.
-- The voice check and every other constraint on the table stay.

alter table public.thread_response_styles
  drop constraint response_styles_shape_known;
