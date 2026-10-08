# Verify: turn cost and latency baseline · spec 0002 · updated 2026-10-07
_Steps derived from spec 0002 acceptance criteria. `/check verify` runs these; `/test` locks the durable ones._

Run everything from `backend/` with `.venv` active, against local Supabase. Steps marked **(credit)** make real
model calls and need muhammad's yes first. Everything else is free. A cheap way to drive the full flow without
credit is a scratch driver that replaces `mani.llm.chain.build` with a fake runnable and makes `chain._model`
raise (see `mani-vault/Journal/testing-ctrl-c-from-a-background-job.md`).

## Commands
- [ ] `docker exec supabase_db_mani psql -U postgres -tAc "select data_type, column_default from information_schema.columns where table_schema='admin' and table_name='llm_calls' and column_name='reasoning_tokens'"` → `integer|0`, and an insert with `-1` is refused by the check → AC-3
- [ ] `pytest` → all pass; the only skips are the four JWKS auth tests; `tests/integration/test_queries.py::test_a_model_calls_thinking_is_stored_and_can_never_be_negative` ran, not skipped → AC-3, AC-13
- [ ] `python scripts/eval_replies.py --baseline --label x --scenario journey_abcde` → `parser.error`, exit 2. Same for `--user`, for `--baseline` with no `--label`, for `--label "a b"`, for `--runs 0`, and for `--runs 3` or `--label x` without `--baseline` → AC-1
- [ ] `DATABASE_URL=postgresql://u:p@db.example.supabase.co:5432/postgres python scripts/eval_replies.py --baseline --label x` → "local database only", exit 1, no user created → AC-8
- [ ] Create `scripts/baselines/<today UTC>-x.json`, then run `--baseline --label x` → "already exists", exit 1, no model call → AC-5
- [ ] Rename `admin.llm_calls.reasoning_tokens` locally, run `--baseline --label x`, rename it back → "apply migration 018 first", exit 1, no user created → AC-12
- [ ] **(credit, or fake model)** `python scripts/eval_replies.py --baseline --label <name> --runs 1` → the three tagged scenarios only, Supportive only, quality checks printed per scenario, exit 0 even with findings, file written → AC-1, AC-6
- [ ] In that file: one turn row per script line that sent a message (an `@accept` line after the offer was taken has none); each row has `line`, `token`, `kind`, `calls`, the four token counts, both latencies, `purposes`, `outcomes` → AC-2
- [ ] In that file: the sum of `calls` across all turn rows equals the number of `admin.llm_calls` rows the run wrote (count them before cleanup, or compare with the cost table the run prints); no row counted twice → AC-2
- [ ] After any run (completed, failed or interrupted): `select count(*) from auth.users where email like '%eval.mani.local'` → 0, and no `admin.llm_calls` row from the run remains → AC-4, AC-9
- [ ] Fake model that raises on one call → "stopped: <scenario>, run <n>, line <l> raised", exit 1, no file, users removed → AC-9
- [ ] Fake model run started with SIGINT handling restored, sent `kill -INT` partway → "interrupted during <scenario>, run <n>", exit 1, no traceback, no file, users removed → AC-9
- [ ] Fake model whose usage has no reasoning count, with effort `high` → warning printed, `reasoning_reported: false` in the file → AC-14
- [ ] **(credit)** A plain `python scripts/eval_replies.py --scenario anxiety_free_chat` → same output shape and exit code as before this change, and no file under `scripts/baselines/` → AC-10
- [ ] `python scripts/baseline.py compare <a.json> <b.json>` → header differences on top, a table per scenario and a total, median before and after, change and percent for each token kind, calls, both latencies and findings; a 0 before prints `n/a` → AC-7
- [ ] `python scripts/baseline.py compare <a.json> missing.json` and with a non baseline JSON file → message, exit 1 → AC-7
- [ ] `scripts/baselines/<date>-before-lean-prompts.json` is committed and its median totals are in `backend/PORT-STATUS.md` → AC-11

## Value sourcing
- [ ] `line` and `token`: in `journey_abcde`, the row for `@tap:Chat More` has `line` 13 and the token exactly as the YAML writes it → AC-2
- [ ] `kind`: an `@accept` taken on an offer reads `accept`; one sent with no offer reads `fallback`; `@tap:` reads `tap`; other lines read `typed` → AC-2
- [ ] `calls`, `purposes`, `outcomes`: a turn where a redraft happened shows two `chat` rows; the turn that completes a framework shows `exercise_select` last → AC-2
- [ ] Token counts: one turn's sums equal a manual `sum(...)` over that thread's rows for the turn, queried before cleanup → AC-2
- [ ] `model_latency_ms`: on a retried call, each row's `latency_ms` is one attempt (a fake model taking 2 s per attempt with a 1 s retry pause gives 2000 and 2000, not 2000 and 5000) → AC-13
- [ ] `turn_latency_ms`: at least the turn's `model_latency_ms` on every row; the gap between them is our own time → AC-2
- [ ] `findings`: equals the count of `FAIL` lines printed for that scenario and run → AC-6
- [ ] `model` and `reasoning_effort`: `chat` matches `model_parameters.reasoning_effort` on the seeded `mani_base` row; `exercise_select` matches `REASONING_EFFORT` in config. Change the `mani_base` row's effort, reseed, and the header follows → AC-5
- [ ] `content`: reseed after editing one framework file → only that framework's hash changes between two files → AC-5
- [ ] `scripts`: edit one tagged scenario's turns → the `scripts` hash changes and compare prints it as a difference → AC-5, AC-7
- [ ] `git`: a run with an uncommitted change under `backend/mani` has a different `git.diff` than one without; saving or staging a baseline file does not change it → AC-5
- [ ] `database_host`: the file holds `127.0.0.1` (or the local host used), never the user or password → AC-5
- [ ] `created_at` and the file date: both UTC; a run started just after local midnight but before UTC midnight is dated by UTC → AC-5
- [ ] `summary` and `totals`: three runs give medians with one decimal place; a line missing from one run shows `present_in` 2 → AC-5

## Acceptance-criteria coverage
- AC-1: flag refusals, the measured run · AC-2: turn rows and every value source row · AC-3: column, `pytest`
- AC-4: cleanup count · AC-5: file exists, header value sources, summary · AC-6: findings printed and stored
- AC-7: compare, both refusals · AC-8: hosted host refused · AC-9: raised turn, interrupt, cleanup
- AC-10: plain run unchanged · AC-11: committed file and PORT-STATUS line · AC-12: missing column, no row abort
- AC-13: per attempt latency · AC-14: `reasoning_reported`
