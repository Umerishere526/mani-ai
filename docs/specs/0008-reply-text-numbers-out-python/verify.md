# Verify: reply text and numbers out of Python · spec 0008 · updated 2026-10-08
_Steps derived from spec 0008 acceptance criteria and its Value sourcing table. `/check verify` runs these; `/test` locks the durable ones. Nothing here runs against a real model (muhammad, 2026-10-08). Run the manual steps after a reseed. Use a throwaway database for any step that makes a write guard fail: a guard that is off lets the write through for real._

## Commands
- [ ] `cd backend && source .venv/bin/activate && python scripts/seed.py`, then `select name, is_active, version from admin.prompts where name in ('replies','tuning')` → both rows exist, active, no `model_id`; the seed runs with `replies.md` or `tuning.md` removed from a copy of the directory → refused with `required row` and nothing written → AC-1, AC-2, AC-4
- [ ] `cd backend && pytest -rs` → whole suite passes with pristine output, the only skips are the four JWKS endpoint tests, and the integration tests ran, not skipped → AC-15
- [ ] `grep -rnE "OPENERS|STYLE_OPTIONS|STYLE_QUESTION|DEFAULT_NAME|AFTER_FRAMEWORK_QUESTIONS|CLARIFICATION_QUESTIONS|CLEAR_OFFER_AFTER|COOLDOWN_AFTER|DEFAULT_STYLE|RECENCY_WEIGHTS|ROUTER_MIN_EXCHANGES|CONTEXT_WINDOW|SUMMARY_THRESHOLD|STYLE_WINDOW|TITLE_AFTER_MESSAGES|ENDING_TURN_CAP|MAX_ENTRIES|MAX_ENTRY_CHARS|IDLE_AFTER|classify_reply|clarification_used|EXPLAIN_LABELS|their_last" backend/mani backend/scripts` → no hits → AC-5, AC-6, AC-7, AC-9, AC-10, AC-12
- [ ] `grep -nE "their_last|clarification_available|after_framework_question\b|Tell me about this" backend/content/prompts/*.md` → no hits → AC-9, AC-10, AC-11, AC-14
- [ ] `./scripts/test_db.sh --local` → still passes; this spec added no migration → AC-15
- [ ] `docker exec -i supabase_db_mani psql -U postgres -c "select name from admin.prompts where is_active order by name"` on a copy where `tuning` is renamed by direct SQL, then one turn → the turn fails with `config_error` (500), never a silent default → AC-3

## UI / manual (scripted model, no real run)
- [ ] `parse_replies` on the seeded file → greeting for a nickname, none and a returning person, the three buttons Direct, Supportive, Reflective in that order, and the three openers equal today's strings exactly → AC-1, AC-5
- [ ] `parse_replies` refuses each of: an unknown key, a missing key, a blank line, an empty list, `{nickname}`, `{}`, `{name!r}`, `{name:x}`, an unbalanced brace, a missing style, an unknown style, two labels equal ignoring case, and ` | `, `[`, `]` or a newline in a clarification line or an after framework question; no message contains the value written → AC-1
- [ ] `parse_tuning` refuses an unknown key, a missing group, `context_window` 3 and 101, `max_entry_chars` 501, `"2"` and `true` for a count, increasing or empty `recency_weights`, a weight of 0 and an unknown `default_style`; whole number weights are accepted → AC-2
- [ ] Cache load with `tuning` missing, then with `replies` that does not parse, each with an earlier good snapshot held → `CONFIG_ERROR` both times, and the snapshot is not served → AC-3
- [ ] `POST` or `PATCH /admin/prompts` with bad `tuning` content, `response_format` set inactive, and `replies` renamed → each 422 `invalid_request`, the row and `prompt_versions` unchanged, the problem text names the key and not the value → AC-4
- [ ] A bad portal edit to `mani_base` that leaves no `reply_shapes` → 422 → AC-4
- [ ] Open a new chat as a nickname user, a no nickname user and a returning user → greeting reads `Hi {name}. It's MANI.` or `Hi {name}, good to see you again.` plus the style question, `there` for no nickname, and three buttons → AC-5; Value sourcing: `start_thread` greeting and buttons
- [ ] Tap Direct, Supportive and Reflective in turn → each answers with its own opener, no model call; rename a label in `replies` after a thread is open and tap the old button on that thread → still resolves, because the stored options are read back → AC-5; Value sourcing: Style tap and Style turn reply
- [ ] Set `cooldown_after_complete` to 3 with an accepted, finished framework 3 messages back → `cooldown_passed: yes`; at 2 back → `no` → AC-6; Value sourcing: `cooldown_passed`
- [ ] Set `clear_offer_after` to 3 → no `cooldown_passed: yes` on a person's second message with nothing offered before; `urgent` still passes it → AC-6; Value sourcing: `cooldown_passed`
- [ ] Set `default_style` to `reflective` with no thread or profile style → `conversation_style: reflective` → AC-6; Value sourcing: `resolve_style`
- [ ] Router with `recency_weights: [1.0]` scores a sign from the first of six messages at full weight; with seeded weights at `0.15`; `strong_weight`, `signal_weight` and `promoted_floor` change the scores and the promoted floor the same way → AC-6; Value sourcing: Router scoring
- [ ] Set `router_min_exchanges` to 3 → the shortlist is empty on a person's second message and present on the third → AC-6; Value sourcing: Router start
- [ ] Set `context_window` to 4 → the model call carries 4 history messages, `needs_summary` turns true once 4 new messages have gathered, and `reconcile_due` asks for threads 4 behind (cron backstop, `GET /internal/cron/fold-summaries`) → AC-6; Value sourcing: History and Summary backstop
- [ ] `GET /v1/threads/{id}` after setting `context_window` to 4 → still 20 messages, from `THREAD_TAIL` → AC-6; Value sourcing: `GET` thread tail
- [ ] Set `style_window` to 2 → `recent_styles` lists at most 2 shapes; `eval_replies._framework_after` reads the same file value → AC-6, AC-7; Value sourcing: `recent_styles`
- [ ] Set `recent_openers_words` to 1 and `recent_openers_window` to 1 → `recent_openers` quotes one word from the last reply only → AC-6; Value sourcing: `recent_openers`
- [ ] Set `title_after_messages` to 5 → a thread is untitled at 3 messages and titled once it has 5 → AC-6; Value sourcing: Title
- [ ] Set `ending_turn_cap` to 3 with `ending_from` 6 messages behind → the framework retires before the call; at 4 behind it carries on → AC-6; Value sourcing: Ending
- [ ] Set `max_entries` to 2 and `max_entry_chars` to 10 → a fold that returns longer lists is bounded to 2 entries of 10 characters each → AC-6; Value sourcing: Memory bound
- [ ] `python scripts/fold_idle_threads.py` with `idle_after_hours` 1 and a thread idle 2 hours → it is folded; at 24 and idle 2 hours → left → AC-6; Value sourcing: Idle fold
- [ ] `eval_replies._open_chat` taps the label from `replies.style_labels` (rename one in a copy of the file); `baseline.content_hashes` changes when `tuning` or `replies` changes → AC-7; Value sourcing: Eval harness and Baseline content hashes
- [ ] A fixture module that binds `OPENERS` or defines `classify_reply` fails `test_prompts_name_what_exists` → AC-8, AC-14
- [ ] `[ctx]` for "idk" carries no `their_last`; with nothing running it carries `clarification_lines: Do I have this right? | What would you like us to focus on today?` even after one was asked; while a framework runs it carries none → AC-9, AC-10; Value sourcing: `[ctx]` `clarification_lines`
- [ ] After the reply that offered Chat More, `[ctx]` carries `after_framework_questions` with all three in order; none while a safety concern is on, and none once that reply has left the history window → AC-11; Value sourcing: `[ctx]` `after_framework_questions`
- [ ] A reply whose technique button is dropped keeps a `Tell me about this` button that has no `decline`, and drops its `Keep chatting` → AC-12
- [ ] The memory fold message starts with `max_entries: 6` for the seeded tuning and `memory_fold.md` names the key, not "six" → AC-13; Value sourcing: Memory fold message
- [ ] `after_framework_questions` does not trip the `after_framework_question` removed name check, and the `CTX_KEYS` contract test passes in both directions → AC-14
- [ ] `PORT-STATUS.md` has the decision line for the two rows, and the three commit 2 lines are edited in place; `docs/database-schema-reference.md` names `replies` and `tuning` → AC-15

## Acceptance-criteria coverage
- AC-1 … commands 1 and `parse_replies` steps · AC-2 … commands 1 and `parse_tuning` step · AC-3 … cache load steps and command 6 · AC-4 … admin write steps and command 1 · AC-5 … greeting, tap and opener steps · AC-6 … every number step · AC-7 … eval harness step and `style_window` step · AC-8 … removed names step · AC-9 … `[ctx]` for "idk" and the prompt grep · AC-10 … clarification step · AC-11 … after framework step · AC-12 … Tell me about this step · AC-13 … fold message step · AC-14 … removed names and contract steps · AC-15 … full suite, PORT-STATUS and schema reference steps
