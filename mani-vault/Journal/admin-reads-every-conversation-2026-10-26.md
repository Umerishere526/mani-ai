---
type: journal
date: 2026-10-26
tags: [journal, admin, chat-tester, privacy, auth]
---

# Admins read every conversation, read-only, in the chat-tester

muhammad asked for an admin role that can read every beta user's chats in full (to review cadence with the
client) and can never chat. Decision in force in `backend/PORT-STATUS.md`; requirement R35.

- **Where:** the chat-tester, not `web/`. The web admin portal's Chats pages exist but run on placeholder data
  with no login at all; the chat-tester already has real Supabase sign-in and is what beta users use. muhammad
  chose the chat-tester knowing the web portal is where the admin surface was meant to live. When `web/` gets real
  auth, its Chats pages can call the same two endpoints.
- **The trap that made this unsafe:** the chat-tester's forgot-password resets any account with no email. With an
  admin role that would hand any beta user every conversation. `client.reset_password` now refuses an account whose
  `app_metadata.admin_role` is admin. Anything else added to the page that acts on another account needs the same check.
- **The overridden note:** "scope the admin conversation browser to unresolved crisis threads, log each read,
  metadata by default". Kept the logging (`admin.thread_reads`) and metadata-only list; dropped the crisis scope.
- **Read-only is enforced in the backend,** not only by hiding the composer: `Participant` in `mani/auth/deps.py`
  refuses `POST /v1/threads/{id}/messages` for an admin token. An admin can still open the ordinary thread
  endpoints for their own account; nothing calls them from the admin view.
- The admin claim reaches the token only at the next sign-in or refresh; a session open when it is granted
  still looks like a tester until then.
- Testing note: the full backend suite had 117 failures in this working tree before the change and the same 117
  after (uncommitted framework content work, and an unseeded database in the check environment).
