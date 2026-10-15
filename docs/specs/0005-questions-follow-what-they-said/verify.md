# Verify: questions follow what the person said · spec 0005 · updated 2026-10-13
_Steps derived from spec 0005 acceptance criteria. `/check verify` runs these; `/test` locks the durable ones._

## Commands
- [ ] `cd backend && .venv/bin/python -m pytest -q` → 437 passed, 4 skipped (the JWKS auth tests); the spec 0005 tests at the end of `tests/integration/test_turn.py` ran, not skipped → AC-1, AC-2, AC-4, AC-7, AC-8, AC-9, AC-10, AC-11
- [ ] `cd backend && ./scripts/test_db.sh --local` → "a user cannot write what Mani understands of them" and "the backend can store what Mani understands" both PASS → AC-1
- [ ] `docker exec supabase_db_mani psql -U postgres -c "\d public.threads"` → `understanding jsonb not null default '{}'` with `threads_understanding_object`; `\d public.thread_summaries` has no `current_issue` → AC-1, AC-8
- [ ] After a tester chat that opens "i am frustrated": `select understanding from public.threads where id = '<thread>'` → `{"feeling": "frustrated"}`, then the issue added after "my work" and the next line → AC-1, AC-3
- [ ] `grep -rn "frustrated" <backend log of that chat>` → no line carries the stored words → AC-11

## UI / manual (chat tester, `AI_DEBUG_MODE=true`)
- [ ] Directive, send "i am frustrated" → "What Mani knows" shows Feeling: frustrated above the stage ledger → AC-12
- [ ] Send "my work", then "my client keeps changing the requirements..." → Issue appears and later changes to the clearer one → AC-1, AC-4
- [ ] Keep chatting past 20 messages with no new feeling → Feeling is still shown, and the turn's `[ctx]` (reasoning or logs) still carries `understanding:` → AC-2
- [ ] Name a different feeling ("now I'm angry") → Feeling becomes angry → AC-3, AC-4
- [ ] Send a concern line (for example "I don't see the point of anything") → the record is unchanged on that turn → AC-11
- [ ] Say yes to the offer with a stored feeling and no event told → A reads "...left you feeling so frustrated?" (supportive) → AC-7
- [ ] Say yes in a chat that never named a feeling → A is the client's ask, and `slot empty` is logged → AC-7
- [ ] The offer's slot reads "the thoughts behind your frustration" (or the style's equivalent), never their judgment of someone else → AC-6
- [ ] A completed framework's exercise pick: the `exercise_select` call's user message starts "What this conversation is about: <stored issue>" → AC-8

## Live (only with muhammad's yes; spends the client's credit)
- [ ] `cd backend && PAUSE_FIRST_OFFER_WINDOW=false .venv/bin/python scripts/scenario_check.py --scenario names_a_feeling_first`, 3 runs × 3 styles → each question follows the previous answer, the feeling comes back in a question or the offer, nothing restated as a statement; "feeling stored" matches the offer's slot → AC-3, AC-5, AC-6
- [ ] Then every client scenario once per style → the same reading; one call per turn in the cost lines; output tokens and latency recorded against the R2 numbers → AC-5, AC-10

## Acceptance-criteria coverage
- AC-1 covered by pytest, test_db, the schema check and the stored record · AC-2 by pytest and the past-20 step · AC-3 by the stored record, the different-feeling step and live · AC-4 by pytest and the replace steps · AC-5 by live only · AC-6 by the offer slot step and live · AC-7 by pytest and the two yes steps · AC-8 by pytest, the schema check and the exercise pick step · AC-9 by pytest (`test_questions_follow_their_answers_from_one_rule_with_no_checklist_or_ban_beside_it`) · AC-10 by pytest and live cost lines · AC-11 by pytest, the log grep and the concern step · AC-12 by the chat tester steps · AC-13 by reading `backend/PORT-STATUS.md` "Decisions in force" and `scripts/scenarios.json` `names_a_feeling_first`
