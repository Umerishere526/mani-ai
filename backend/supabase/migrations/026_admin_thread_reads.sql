-- ABOUTME: Records each time an admin opens a person's conversation in full, so reading health data leaves a trail.
-- ABOUTME: Written by the admin transcript endpoint on its service-role connection; no user role can see it.

-- Admins read every beta user's conversations to review how a chat paces itself. A transcript is
-- special-category health data, so each full read is logged: who read which thread, and when. The row holds
-- no message content. It goes with the thread, and with either account, when one is deleted, as every other
-- user-owned row does; deleting the auth user is the whole account teardown (migration 005).
create table admin.thread_reads (
  id         uuid primary key default gen_random_uuid(),
  admin_id   uuid not null references auth.users (id) on delete cascade,
  thread_id  uuid not null references public.threads (id) on delete cascade,
  read_at    timestamptz not null default now()
);

create index idx_thread_reads_thread on admin.thread_reads (thread_id, read_at desc);
create index idx_thread_reads_admin on admin.thread_reads (admin_id, read_at desc);

-- The admin schema's default (migration 001): nothing for anon or authenticated, everything for service_role.
revoke all on admin.thread_reads from anon, authenticated;
grant all on admin.thread_reads to service_role;

-- Lets Supabase Auth complete the two cascades above when it deletes a user (migration 005 explains why).
grant delete on admin.thread_reads to supabase_auth_admin;
