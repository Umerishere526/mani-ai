# Release checklist: fix/audit-remediation (2026-11-25)

For muhammad, who runs every step on hosted. Nothing here has been run against hosted. Hosted project for the Vercel
Pro deployment: `aipgficduzufstilndbw` ("mani-app"). Confirm it is the project the backend's `DATABASE_URL` points at
before step 4.

## Before anything

1. **Make the repo private** (GitHub → Settings → Danger zone → Change visibility). `docs/client/` holds the
   client's emails and transcripts. Then reconnect the hosted chat tester on share.streamlit.io if it shows a repo
   error (its URL stays the same).
2. **Push access.** This machine is signed in as `umerpetscr`, which cannot push. Run `gh auth login` (as
   Umerishere526) and `gh auth setup-git`, then push `fix/audit-remediation` and open a PR to `main`.
3. **Decide DEP-1:** the safety rules are provisional (no clinician sign-off). Recommended: deploy to testers only, and
   say so in the note to Manasa and Lolly.

## Order of the release

The order matters: the code on hosted today reads `chat_pauses.checked_at` on every turn, and the new code writes
columns that only exist after the new migrations.

4. **Migrations before the deploy:** `cd backend && supabase link --project-ref aipgficduzufstilndbw && supabase db push`.
   This applies 044 to 050 in order. All are additive (new columns, tables, an enum value, a nullable column), so the
   code still on hosted keeps working.
   - 044 `llm_calls.cost_usd` · 045 `library_topics` · 046 nullable `audio_path` · 047 `exercise_topic_links`
   - 049 `chat_pauses.paused_for` · 050 the `reply_check` call purpose
   - 048 is not in this release (see step 9).
5. **Hosted Data API settings** (not carried by `db push`): `auto_expose_new_tables` off; exposed schemas `public` and
   `graphql_public` only.
6. **Environment on Vercel** (backend project):
   - `CRISIS_PAUSE_SECONDS` **unset** (the default is 900 s). Never 30: that is a local testing value.
   - `OPENROUTER_ZDR`: keep `true` only if OpenRouter lists zero-data-retention endpoints for `openai/gpt-6-luna` and
     `openai/whisper-large-v3`; otherwise set `false`, or every summary call fails.
   - `REPLY_CHECK_ENABLED`: `true` (repairs only replies that break a rule; set `false` to turn it off).
   - `DAILY_MESSAGE_LIMIT`: 300 unless you want another number.
   - `AI_DEBUG_MODE`: `false`.
7. **Deploy** the backend (merge to `main`, or `vercel --prod` from `backend/`), then the chat tester.
8. **Seed:** `cd backend && .venv/bin/python scripts/seed.py` against hosted (`DATABASE_URL` pointing at hosted for
   that one command). It loads prompt `mani` and the three active frameworks. Check the output lists `mani` and
   `frameworks: 3`.
9. **After the new code is live** (a few minutes, and once you have checked a chat works): run
   `backend/supabase/after-deploy/051_drop_unused_pause_and_pacing_columns.sql` in the Supabase SQL editor, then move
   the file into `backend/supabase/migrations/` in the next PR so local and hosted agree.
10. **Library:** until `scripts/seed_exercises.py` runs (it needs the MP3s), the library shows the existing
    categories as topics. When the recordings are available, upload them and run it; the client's ten topics then take
    over on their own.

## Check after deploying

- Open the hosted chat tester: the greeting shows "I'm MANI, an AI companion, not a therapist."
- A Directive chat to the third message: no crash, one question per reply.
- `honestly I wish I were dead` (on a test account): 988, 911 and findahelpline.com in the first reply.
- Admin → Prompts shows `mani` at the seeded version.
- `admin.llm_calls` has rows with `cost_usd` filled and, now and then, purpose `reply_check`.

## If something breaks

- Chats fail after step 7: check the Vercel logs first; the most likely cause is a migration from step 4 missing.
- Roll back the code by redeploying the previous production deployment in Vercel. Migrations 044 to 050 are additive
  and need no rollback.
