-- ABOUTME: The library's topics: each one's id (an exercise's category), its title and the client's one-line blurb.
-- ABOUTME: Shared catalog like admin.exercises: seeded by scripts/seed_exercises.py and read by the backend alone.

-- The client wrote a blurb for each topic, shown under it on the main screen (R142), and there was nowhere to keep
-- one. The id is the category an exercise carries, so a topic's exercises are those with its id as their category.
create table admin.library_topics (
  id            text primary key,
  title         text not null,
  blurb         text not null default '',
  display_order integer not null default 0,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  constraint library_topics_id_shape check (id ~ '^[A-Z][A-Za-z]*$')
);

create trigger library_topics_touch before update on admin.library_topics
  for each row execute function public.touch_updated_at();

-- Served through the API, like the exercise catalog (034): the backend's role reads it, a person's token does not.
grant select on admin.library_topics to mani_service;
