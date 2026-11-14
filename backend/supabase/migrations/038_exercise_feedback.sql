-- ABOUTME: The person's 👍 or 👎 on a library exercise, with an optional reason, one per person per exercise.
-- ABOUTME: Read by its owner and by admins; written only by the backend, and only on an active exercise.

create table public.exercise_feedback (
  user_id      uuid not null references auth.users (id) on delete cascade,
  exercise_id  uuid not null references admin.exercises (id) on delete cascade,
  rating       text not null,
  reason       text,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  primary key (user_id, exercise_id),
  constraint exercise_feedback_rating check (rating in ('up', 'down')),
  -- The API cleans and bounds the reason first; this is the backstop. An empty reason is stored as null.
  constraint exercise_feedback_reason_length check (reason is null or char_length(reason) between 1 and 1000)
);

-- The primary key covers user_id; the exercise side of the foreign key needs its own.
create index idx_exercise_feedback_exercise on public.exercise_feedback (exercise_id);

alter table public.exercise_feedback enable row level security;

create policy exercise_feedback_select on public.exercise_feedback for select
  using ((select auth.uid()) = user_id);
create policy exercise_feedback_insert on public.exercise_feedback for insert
  with check ((select auth.uid()) = user_id);
create policy exercise_feedback_update on public.exercise_feedback for update
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);
create policy exercise_feedback_delete on public.exercise_feedback for delete
  using ((select auth.uid()) = user_id);

-- The person reads their own ratings; writes go through the backend, which cleans and bounds the reason and
-- refuses an inactive exercise, so they belong to mani_service alone.
grant select on public.exercise_feedback to authenticated;
grant insert, update, delete on public.exercise_feedback to mani_service;

-- Lets Supabase Auth complete the cascade when it deletes a user (migration 005 explains why).
grant delete on public.exercise_feedback to supabase_auth_admin;
create policy auth_admin_cascade_delete on public.exercise_feedback
  for delete to supabase_auth_admin using (true);
