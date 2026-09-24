-- ABOUTME: Caps profiles.topics, which is interpolated into the system prompt on every turn.
-- ABOUTME: The same reason nickname already carries a length check.

-- A person can write their own topics, through the API and through PostgREST alike, and
-- every one of them is pasted into the system prompt of every turn. Unbounded, it was a
-- place to paste instructions and a cost multiplier. A CHECK cannot hold a subquery, so the
-- database bounds the count and the total; ProfileIn also caps each item.

alter table public.profiles
  add constraint profiles_topics_bounded
  check (cardinality(topics) <= 10 and char_length(array_to_string(topics, '')) <= 600);
