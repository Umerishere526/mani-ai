-- ABOUTME: Drops admin.frameworks.stages and admin.frameworks.activation_conditions, which no code reads.
-- ABOUTME: A framework's model facing text is its seven line `body`, which already carries the Starts when line.

-- `stages` (migration 002) held per stage content for a composer that no longer exists; the
-- seed has written {} to it for every framework since the frameworks became seven lines.
-- `activation_conditions` (migration 001) held a copy of the body's first line and was
-- selected but never read. `activation` stays: it carries never_offer_when_said.

alter table admin.frameworks drop constraint frameworks_stages_is_an_object;
alter table admin.frameworks drop column stages;
alter table admin.frameworks drop column activation_conditions;
