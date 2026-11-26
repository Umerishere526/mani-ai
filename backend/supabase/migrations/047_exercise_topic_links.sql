-- ABOUTME: Lists an exercise in a topic besides its own, under a subcategory: Workplace Challenges reuses other topics'.
-- ABOUTME: Seeded from the manifest by scripts/seed_exercises.py and read by the backend alone, like the catalog.

-- An exercise's own topic stays its `category`; a link adds it to another topic's listing. The client's Workplace
-- Challenges "reuses exercises from other collections, organized into seven subcategories", so the link carries the
-- subcategory it is shown under and its place in that topic's list.
create table admin.exercise_topic_links (
  topic_id      text not null references admin.library_topics (id) on delete cascade,
  exercise_id   uuid not null references admin.exercises (id) on delete cascade,
  subcategory   text not null,
  display_order integer not null default 0,
  primary key (topic_id, exercise_id)
);

-- The primary key covers topic_id; the exercise side of the foreign key needs its own.
create index idx_exercise_topic_links_exercise on admin.exercise_topic_links (exercise_id);

grant select on admin.exercise_topic_links to mani_service;
