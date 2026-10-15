-- ABOUTME: Adds the framework level pool of short phrases that confirm a stage already answered.
-- ABOUTME: Seeded from the framework file's `confirm_phrases`; empty for a framework without them.

-- One pool for the whole framework, so it is neither stage content (admin.frameworks.stages) nor
-- activation data. A constant default makes the add a metadata change; no row is rewritten.

alter table admin.frameworks
  add column confirm_phrases text[] not null default '{}';
