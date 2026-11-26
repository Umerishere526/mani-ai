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

The order matters: the new code writes columns that only exist after the new migrations.

4. **Migrations before the deploy:** `cd backend && supabase link --project-ref aipgficduzufstilndbw && supabase db push`.
   This applies 044 to 050 in order. All are additive (new columns, tables, an enum value, a nullable column), so the
   code still on hosted keeps working.
   - 044 `llm_calls.cost_usd` · 045 `library_topics` · 046 nullable `audio_path` · 047 `exercise_topic_links`
   - 049 `chat_pauses.paused_for` (already applied on hosted; no code reads or writes it) · 050 the `reply_check` call
     purpose
   - There is no 048: the code reads `chat_pauses.checked_at`, so that column stays.
5. **Hosted Data API settings** (not carried by `db push`): `auto_expose_new_tables` off; exposed schemas `public` and
   `graphql_public` only.
6. **Environment on Vercel** (backend project):
   - `CRISIS_PAUSE_SECONDS`: as on main (the code's default is 30 s).
   - `OPENROUTER_ZDR`: keep `true` only if OpenRouter lists zero-data-retention endpoints for `openai/gpt-6-luna` and
     `openai/whisper-large-v3`; otherwise set `false`, or every summary call fails.
   - `REPLY_CHECK_ENABLED`: `true` (repairs only replies that break a rule; set `false` to turn it off).
   - `DAILY_MESSAGE_LIMIT`: 300 unless you want another number.
   - `AI_DEBUG_MODE`: `false`.
7. **Deploy** the backend (merge to `main`, or `vercel --prod` from `backend/`), then the chat tester.
8. **Seed:** `cd backend && .venv/bin/python scripts/seed.py` against hosted (`DATABASE_URL` pointing at hosted for
   that one command). It loads prompt `mani` and the three active frameworks. Check the output lists `mani` and
   `frameworks: 3`.
9. **Library:** until `scripts/seed_exercises.py` runs (it needs the MP3s), the library shows the existing
    categories as topics. When the recordings are available, upload them and run it; the client's ten topics then take
    over on their own.

## Check after deploying

- A Directive chat to the third message: no crash, one question per reply.
- Admin → Prompts shows `mani` at the seeded version.
- `admin.llm_calls` has rows with `cost_usd` filled and, now and then, purpose `reply_check`.

## If something breaks

- Chats fail after step 7: check the Vercel logs first; the most likely cause is a migration from step 4 missing.
- Roll back the code by redeploying the previous production deployment in Vercel. Migrations 044 to 050 are additive
  and need no rollback.
