# Migration versions after the dummy-merge

The merge of `fix/improvement-mani` into `dummy-merge-branch` left two files on `011` and two on `012`. `supabase_migrations.schema_migrations` keys on `version`, so a reset cannot record both.

Renumbered on 2026-10-06. The `fix/improvement-mani` files kept the numbers the code already cites. The other branch's two files moved to the end, in their own order:

- `011` `technique_state_holds`
- `012` `technique_state_known`
- `013` `llm_call_decision`
- `014` `technique_state_ending`
- `015` `framework_outcomes`
- `016` `technique_outcome_stopped` (was `011`)
- `017` `technique_phase_since` (was `012`)

Then `supabase db reset --local --yes --no-seed` on project `mani` (port 54342) applied `001`–`017`, and `python scripts/seed.py` loaded 6 frameworks and 5 prompts. `--no-seed` because `backend/supabase/seed.sql` does not exist; markdown is seeded by `scripts/seed.py`. Reset clears `admin.exercises`; the library is `scripts/seed_exercises.py`, not this reseed.

## Hosted, same day

The hosted project (`heqenombgkihfeggrxqc`) had stopped at `010` and its content was last seeded on Oct 2. Live turns failed with `UndefinedColumnError` on `llm_calls.decision`, and live ran `gemini-3.1-flash-lite` while local ran `gemini-3.8-flash`. Fixed with `supabase db push` (011–017) and `scripts/seed.py` using `.env.hosted`'s `DATABASE_URL`. **A merge that touches `migrations/` or `content/` is not live until both are run against hosted.** Vercel only ships code.

`SEMANTIC_ROUTER` was `true` in local `.env` and unset on Vercel (so `false`). That is a third source of local/live drift.
