---
type: journal
date: 2026-11-13
apps: [backend]
tags: [journal, supabase, rls, account-deletion, lessons]
---

# Account deletion cascades run as the table owner (2026-11-13)

2026-11-13. History, not rules. Found while adding a `chat_pauses` row to
`backend/tests/integration/test_account_lifecycle.py`.

- On the local stack (Postgres 17.6, public tables owned by `postgres`, which has BYPASSRLS), deleting a user as
  `supabase_auth_admin` removes their `chat_pauses` rows even with the `auth_admin_cascade_delete` policy dropped and
  the DELETE grant revoked. Checked in a rolled-back transaction as `supabase_admin`: `DELETE 1`, no pause left.
  Postgres runs a foreign key's cascade as the owner of the referencing table, so the deleting role's grants and
  policies are never consulted for it.
- So the lifecycle test cannot go red by removing that policy or grant. It still proves the deletion end to end
  through GoTrue; it would catch a missing `on delete cascade` or a trigger that fails under the cascade.
- Only `chat_pauses` (037) was tested, with a thread holding no messages. Migrations 005 and 009 add the same grant
  and policy for other tables, and 005 also records a failure from the message-count trigger firing under the
  cascade; none of that was tried here, so whether those are still needed is open. Dropping policies on `threads` or
  `messages` to find out would lock tables the live backend uses, so it was not done. Not changed.
- Related: [[supabase-defaults-made-a-fresh-project-unsafe-2026-11-06]].
