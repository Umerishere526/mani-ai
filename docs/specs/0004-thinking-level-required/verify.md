# Verify: thinking level required on every call · spec 0004 · updated 2026-10-07
_Steps derived from spec 0004 acceptance criteria. `/check verify` runs these; `/test` locks the durable ones._

Run everything from `backend/` with `.venv` active, against local Supabase. Nothing here makes a real model
call, so nothing spends credit. Steps that break a file or a row put it back afterwards: rerun
`python scripts/seed.py` and `POST /v1/admin/prompts/cache/invalidate` (or restart the server).

## Commands
- [ ] `pytest` → 615 passed, 4 skipped (only the four JWKS auth tests); `tests/integration` ran, not skipped; no warning → AC-1 to AC-8
- [ ] `python scripts/seed.py` → prints 7 prompts, including `exercise_select` and `voice_translation` → AC-6
- [ ] `docker exec supabase_db_mani psql -U postgres -tAc "select name, model_parameters->>'reasoning_effort' from admin.prompts order by name"` → `exercise_select`, `mani_base`, `memory_fold`, `summarization` and `voice_translation` show `high`; `response_format` and `title_generation` show nothing → AC-1, AC-6
- [ ] Delete the `reasoning_effort: high` line from `content/prompts/memory_fold.md`, run `python scripts/seed.py` → exits with `seed refused, nothing written: memory_fold.md: memory_fold: model_parameters has no reasoning_effort`, and no row's `updated_at` changed; restore the line → AC-3
- [ ] Set it to `reasoning_effort: extreme` instead → refused, naming `memory_fold.md` and the allowed levels → AC-3
- [ ] Move `content/prompts/voice_translation.md` out of the folder, run the seed → refused, naming `voice_translation`; move it back → AC-3
- [ ] `content/prompts/response_format.md` and `title_generation.md` name no `reasoning_effort`, and the seed accepts both: a layer row needs no level → AC-3
- [ ] `grep -rn REASONING_EFFORT mani .env.example` → nothing; `python -c "from mani.config import Settings; print('reasoning_effort' in Settings.model_fields)"` → `False` → AC-2
- [ ] Add `REASONING_EFFORT=low` to `.env`, run `pytest tests/integration/test_turn.py -k "level_its_row_names"` → passes; the setting changes nothing; remove the line → AC-2
- [ ] `grep -n "_TRANSLATE_SYSTEM_PROMPT\|just completed the" mani -r` → nothing: both instructions live only in their rows → AC-6
- [ ] `pytest tests/unit/test_stt.py tests/integration/test_turn.py -k "translation_is_the_one or own_row_names"` → the translation and the pick each send effort `high`, Azure first, `data_collection: deny`, and a budget of their reply size (500, 200) plus 8,192 → AC-7

## UI / manual (API calls with an admin token, server running)
- [ ] `PATCH /v1/admin/prompts/{memory_fold id}` with `{"model_parameters": {"maxTokens": 800}}` → 422 `invalid_request`; the row still shows `reasoning_effort: high`; `admin.prompt_versions` has no new row for it → AC-4
- [ ] Same with `{"model_parameters": {"reasoning_effort": ["high"]}}` → 422, never 500 → AC-4
- [ ] Same with `{"name": "fold_paused"}`, and with `{"is_active": false}` → 422 each → AC-4
- [ ] `POST /v1/admin/prompts` with `{"name": "voice_translation", "content": "x"}` after deleting that row in SQL → 422 → AC-4 (reseed after)
- [ ] `PATCH` memory_fold with `{"content": "<same text>"}`, and `response_format` with `{"model_parameters": {}}` → 200 each → AC-4
- [ ] In SQL, set `exercise_select`'s `model_parameters` to `'{}'`, invalidate the cache, and complete a framework with a catalog exercise linked to it → the reply carries the framework's first exercise, the log says `exercise pick skipped, offering the first candidate`, and no `admin.llm_calls` row with purpose `exercise_select` is written. This step makes one real chat call: ask muhammad first, or rely on `test_an_exercise_row_with_no_level_offers_the_first_candidate_without_a_pick` → AC-5
- [ ] In SQL, set `mani_base`'s `model_parameters` to `'{}'`, invalidate, send a message → 500 `config_error` in the standard error shape, and no new `admin.llm_calls` row → AC-5
- [ ] In SQL, set `voice_translation` inactive, invalidate, upload a non-English recording → the reply is the untranslated transcript, and the log warns about `voice_translation` without the transcript text. Whisper is a real call: ask muhammad first, or rely on `test_a_row_with_no_level_costs_the_translation_not_the_voice_input` → AC-5
- [ ] With `voice_translation` inactive, restart the server and send any message → the log warns `prompts missing or inactive: voice_translation` → AC-8

## Value sourcing
- [ ] Chat turn: `pytest tests/integration/test_turn.py -k "level_its_row_names"` → a `mani_base` row on `low` sends `low` (every seeded row says `high`, so only a changed row proves it is read) → AC-1
- [ ] Summary and memory fold: in SQL set `summarization` to `'{"maxTokens": 500}'`, trigger a summary → the log shows `summarization failed` with `config_error` and the existing summary is kept; same for `memory_fold` → `memory fold failed` → AC-1, AC-5
- [ ] Exercise pick and voice translation: covered by the AC-7 command above, which reads model, budget, level and routing from each row → AC-1, AC-7
- [ ] Which rows are calls: `python -c "from mani.prompts.calls import CALL_PROMPTS; print(sorted(CALL_PROMPTS))"` → the five call names, and the seed refuses any of them missing → AC-3
- [ ] Admin check sees the row after the edit: `pytest tests/integration/test_admin_prompts.py -k "renamed_to_a_call_name"` → a layer renamed to `memory_fold` with no level is refused → AC-4
- [ ] Output budget: `pytest tests/unit/test_chain.py -k "eats_the_budget"` → every reply budget keeps room after the longest thinking seen → AC-7

## Acceptance-criteria coverage
- AC-1 covered by the database levels step, the chat turn value step, the summary and fold step, and the AC-7 command
- AC-2 by the `grep` and `Settings` step and the leftover `.env` step
- AC-3 by the four seed steps and the `CALL_PROMPTS` step
- AC-4 by the five admin API steps and the rename test
- AC-5 by the exercise pick, chat turn, voice and summary/fold steps
- AC-6 by the seed output, the database levels step and the `grep` for the old constants
- AC-7 by the request body command and the budget test
- AC-8 by the startup warning step
