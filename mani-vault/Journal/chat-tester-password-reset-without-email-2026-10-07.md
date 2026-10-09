---
apps: [chat-tester, backend]
tags: [journal, chat-tester, auth, supabase]
---

# chat-tester resets a password on the page, no email

muhammad wanted the tester's forgot-password to need no mail setup, so it takes email plus a new
password and sets it through the Auth Admin API (`client.reset_password`). The emailed six-digit
code flow it replaced was safe because only the mailbox owner could finish it; this one is not,
so the page must stay non-public. muhammad accepted that: it is a test tool, and it goes to prod
alongside the open sign-up.

- Local and hosted Supabase behave the same for this. Verified on prod with a throwaway account
  (created, reset, signed in, deleted): the `sb_secret_` key works as `apikey` and as `Bearer`
  on the admin endpoints.
- Admin-created users send no mail. Mailpit only shows mail from the public `/auth/v1/signup`
  (confirmation) and, in the old flow, `/recover`. Prod has no Mailpit.
- GoTrue's admin API cannot filter users by email, so the lookup scans pages of 1000.
- `PORT-STATUS.md` claimed hosted was seven migrations ahead of local. It was not: schema and
  seeded content matched on 2026-10-07. Check before trusting that kind of note; see
  [[reverting-code-does-not-revert-the-database]].
- Removed with the emailed flow: `backend/supabase/templates/recovery.html` and the
  `[auth.email.template.recovery]` block in `config.toml`. The apps will need an email reset later and
  will have to bring a template back (a code, not a link: a link needs a per-environment redirect).
  The local auth container only reads `config.toml` at `supabase start`, so a running one keeps the old template until restarted.
