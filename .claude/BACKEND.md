# backend — FastAPI

FastAPI 0.141.1 on Python 3.14, in a local virtualenv at `backend/.venv`.

## Commands

Activate the venv before running anything Python:

```bash
cd backend
source .venv/bin/activate
supabase start             # local Supabase (Docker must be running); see the ports note below
supabase db reset          # recreate and re-apply migrations
python scripts/seed.py     # loads content/ into admin.frameworks and admin.prompts (re-run after ANY edit in content/)
python scripts/grant_admin.py you@example.com [--revoke]  # an existing account reads every conversation read-only, and chats in none
python scripts/seed_exercises.py  # uploads content/exercises/ audio to the private `exercises` bucket and upserts admin.exercises
fastapi dev main.py        # dev server with reload on :8000
fastapi run main.py        # production mode
pytest                     # the whole suite: unit and integration (integration skips without a database)
python evals/run_eval.py [--label <name>] [--prompt <file>] [--variant NAME=MODEL[,EFFORT[,HOST|HOST...]]]   # the gate for a prompt or model change: muhammad's test messages scored against reference replies, plus the rule cases; costs real calls
python evals/check_suite.py   # the merge gate's conversations through the real stack with a model-played person; exits 0 only when every check passes; costs real calls
python evals/drive.py <style> <turns> "<persona>" ["first message"]   # one model-played conversation, printed
python evals/regress.py --list                  # the regression scenarios (TC-01..20) and the gaps, no calls
python evals/regress.py                         # every scenario: deterministic checks, judged scores, latency, tokens; costs real calls (muhammad's yes first)
python evals/regress.py --scenario TC-11        # one scenario (repeatable)
python evals/regress.py --only safety|framework|pacing|isolation [--no-judge]
python evals/regress.py --bench 5 --scenario TC-01   # the selection 5 times, latency only
# regress.py refuses a non-local DATABASE_URL unless --allow-remote-db (a test project, never production). Exit 1 on any
# deterministic failure; gaps, pending requirements (the client's, not yet recorded in docs/client and approved) and
# judged scores never fail it; --strict-latency also fails a turn over its limit. The report
# is evals/results/regress-latest.md; evals/results/summaries/ is committed so each run is compared with the last.
# Free plumbing check: run scripts/fake_openrouter.py, set OPENROUTER_BASE_URL to it, and run script-only scenarios with
# --no-judge (the fake only streams, so the model-played person and the judge cannot use it).
./scripts/test_db.sh       # schema + RLS against a throwaway Postgres (needs Docker)
python scripts/fake_openrouter.py   # a local stand-in for OpenRouter at the production latency profile, for load tests
python scripts/load_users.py create 100 --out tokens.json   # synthetic local users and their tokens; `remove` deletes them
locust -f scripts/locustfile.py --host http://127.0.0.1:8011   # the offline load test; the backend must point OPENROUTER_BASE_URL at the fake
```

**Ports.** `backend/supabase/config.toml` sets `5434x` (API `54341`, Postgres `54342`, Studio `54343`, Mailpit `54344`) so it can run beside the previous project's `5433x`. What is running can differ: on this machine the containers answer on the Supabase defaults (API `54321`, Postgres `54322`, Studio `54323`), and `backend/.env` points there. If this paragraph and `docker ps` disagree, `docker ps` and `backend/.env` are right.

To run the RLS assertions against the real local Supabase rather than a throwaway container:

```bash
docker exec -i supabase_db_mani psql -U postgres -v ON_ERROR_STOP=1 -q < tests/sql/test_rls.sql
```

Without activating, call the venv binaries directly — `./.venv/bin/python`, `./.venv/bin/pip`. Never use a system-wide `python` or `pip` for this project.

## Layout

- `main.py` — `create_app()` plus the module-level `app`. Sentry init and the `ServiceError` handler live here; routes do not.
- `mani/` — the application package, and the only thing that runs. `config.py`, `errors.py`, `routers/`, `auth/`, `models/`, and the `chat/`, `prompts/`, `llm/` and `db/` layers, plus `summarize.py`, `background.py`, `storage.py` and `auth_admin.py`. `chat/` is the turn: `runner.py` runs it as read, think, write, with no database connection held while the model thinks; `turn.py` is its steps, one model call that writes every word; `facts.py` builds the system prompt (`mani.md` and the framework guide) and the facts block that says what code would refuse; `reply.py` is the reply's shape; `decide.py` holds the guarantees (offer gating and buttons, one stage step, finish only on the last stage); `judged.py`, `safety.py` and `pause.py` move the safety state and decide a pause; `record.py` is the thread record (Mani's notes, the frameworks declined or finished, the safety keys); `taps.py` reads a tapped button. **It never reads the filesystem for content** — prompts and frameworks come from the database.
- `content/` — authored markdown, seeded into the `admin` schema by `scripts/seed.py` and never read at runtime. `content/prompts/*.md` become `admin.prompts` (`mani.md` is the chat turn's, with its model, effort and hosts in its frontmatter); `content/frameworks/*.md` (ABCDE and Thought Reframe; the rest are in `paused/`) become `admin.frameworks`, carrying each framework's per-stage content and its activation data (the framework guide reads `central_indication`, `contraindications` and each stage's `intro`, `purpose` and `ready_when`; a lead-in button sends `offering.explain`, the five steps per style, and I need an example sends `offering.example`; the rest is read by nothing). Editing one of these changes nothing until it is re-seeded. A re-seed that changes a prompt's text, model, parameters or routing first copies the row it replaces into `admin.prompt_versions` and moves its `version` on, as an edit in the admin portal does (`seed.seed_prompt`). Kept outside `mani/` because it is input to the database, not code — the same relationship a migration has to the schema.
- `supabase/migrations/` — the schema. `test_harness.sql` stubs what Supabase adds (`auth.users`, `auth.uid()`, the three roles) so the schema can be tested on plain Postgres.
- `evals/` — the evaluation that gates prompt and model changes (`run_eval.py`, `cases.json`), the merge gate's conversations (`check_suite.py`, `suite.json`, `drive.py`) and the regression suite (`regress.py`, `regression/`: `scenarios.json`, `checks.py` the deterministic checks, `judge.py`, `metrics.py`, `report.py`, `play.py`); results go to `evals/results/`, which is gitignored except `summaries/`.
- `tests/unit/` — deterministic logic. `tests/integration/` — whole turns against a live database with a scripted model. `tests/sql/` — schema, RLS and privilege assertions run by `scripts/test_db.sh`.
- `scripts/` — `seed.py`, `seed_exercises.py` (the library: `content/exercises/exercises.json` plus its MP3s at 64 kbps mono; the MP3s are gitignored and stay off GitHub, so on a fresh machine copy them from production's `exercises` bucket first), `test_db.sh`.
- `docs/` — `specs/` holds the client's specifications, one per framework, as the source the content is checked against; `database-schema-reference.md`; `ai-layer-audit.md` (a dated snapshot, read its banner).
- `PORT-STATUS.md` — what the service does, what changed from the implementation it replaces, and what is still open. **Update it in the same change as the work.**
- `requirements.txt` — runtime dependencies only, pinned, hand-maintained. `requirements-dev.txt` adds pytest and `fastapi-cli` on top. **Add a new dependency to whichever file it belongs in** — do not `pip freeze` over them, which buries the packages that matter under their transitive closure and puts a test runner in the deployed image.
- `Dockerfile` — the API process. Platform-agnostic (Fly, Railway, Cloud Run); never Lambda-style, because the reading after a reply, summaries and the cost-row links run after the response, and a platform that suspends the function then loses them (PORT-STATUS, Open engineering).

## Recreating the environment

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

## Conventions

- Use Pydantic models for request and response bodies rather than raw dicts — `pydantic` 2.13 is already installed, as is `pydantic-settings`.
- Read configuration through `pydantic-settings` and a `.env` file (`python-dotenv` is installed). Never commit secrets or inline them in `main.py`.
- As routes grow past a handful, split them into `APIRouter` modules and include them from `main.py` — don't let `main.py` become a dumping ground.
- `sentry-sdk` is initialised in `create_app()` when `SENTRY_DSN` is set, with `send_default_pii=False` — conversation content is special-category health data and must not ride along on an error report.
- Postgres is reached directly with `asyncpg`, not through PostgREST. A chat turn makes many writes that must succeed or fail together, and PostgREST cannot hold a transaction across statements.
- `DATABASE_URL` points at Supabase's **transaction pooler** (port 6543), which hands each transaction whichever backend is free. Everything that touches the database runs inside a transaction, and state is only `set local`, `set_config(..., true)` or `pg_advisory_xact_lock`: no session-level SET, LISTEN, session advisory lock or named prepared statement, none of which survive the pooler. Never hold a connection across a model or network call, and never take a second while holding one: `pool` raises `RuntimeError` for a second connection, a model call or a prompt-cache read in a task that holds one. `chat/runner.py` is how a turn avoids it; `summarize.update` reads, calls the model, then writes the same way.
- OpenRouter is the only model provider. LangChain (`langchain-openai`) composes the call and parses the structured reply; the `openai` protocol is used because OpenRouter speaks it — it is not a second provider. The key lives in the environment, never in the database.
- A turn waits on one model call, and nothing reads the conversation after the reply; the summary, when due, is its own request (`turn.follow_up`).

## Identity and authorization

This backend is the only thing that touches the database, which makes it the only place authorization exists. Two rules, both non-negotiable:

- **Verify the JWT and derive the user id from it.** Never read a `user_id` from a request body, query parameter, or header — a client that names its own identity can name someone else's. Extract the subject from the verified token and ignore whatever the request claims.
- **Use a user-scoped Supabase client by default**, built per request from the caller's JWT, so Postgres enforces ownership through RLS. The service role key bypasses RLS entirely and is reserved for genuine cross-user work under a distinctly named client. Full reasoning in `.claude/SUPABASE.md`.

## Type safety across the API boundary

There is no shared contract between this backend and the frontends — no tRPC, no compile-time link. `web/` and `mobile/` can drift from the API silently, and mobile is especially unforgiving because it ships as a compiled binary through store review: a mismatch that reaches users waits out a review cycle to fix.

**Status: not in place.** There is no generated type output and no CI (`.github/` does not exist), and `web/` and `mobile/` still run on placeholder data and a chat simulation, not on this API. Until that changes, treat the OpenAPI schema (`/openapi.json`) as the contract and check it by hand.

So generate it, and gate it:

- Generate TypeScript types for `web/` and `mobile/` from this app's OpenAPI schema, and commit the output.
- **Fail CI when the committed types don't match the schema.** Without that gate you have swapped a compiler guarantee for a convention, and conventions rot. Do this before the first mobile build ships, not after.
- Keep response models explicit on every route (`response_model=`), or the generated schema degrades to `Any` and the types become decorative.

## API conventions

Things a reviewer will check for.

Things a reviewer will check for, and where they are.

- **One error shape, everywhere.** `{"error": {category, message, retryable}}`. The
  `ServiceError`, validation and unhandled-exception handlers in `main.py` all produce it, so a
  client has one branch rather than two. FastAPI's default `{"detail": [...]}` and Starlette's
  plain-text 500 are overridden.
- **401 and 403 are distinct.** No usable token is `unauthenticated` → 401, so a client
  refreshes. Authenticated but not permitted is `forbidden` → 403.
- **4xx does not log a stack trace.** Expired tokens are routine; a traceback each would
  bury real faults and spend the Sentry quota. 5xx logs with `exc_info`.
- **A validation error never echoes the input.** FastAPI's default includes the offending
  value, which here could be part of somebody's message.
- **`operationId` is the handler name** (`send`, `list_threads`), not FastAPI's
  `send_v1_threads__thread_id__messages_post`. These become the generated client's
  function names; uniqueness is asserted in `tests/unit/test_app.py`.
- **`response_model=` on every route.** Without it the generated schema degrades to
  `Any` and the types become decorative.
- **Every write is a POST/PATCH/DELETE.** `GET /v1/threads/opening` and `GET /v1/threads/current`
  write nothing: a conversation is created by `POST /v1/threads` with the person's first message.
  A GET must be safe, and prefetchers treat it so.
- **Cursors are `datetime`, not `str`.** Typed loosely, a malformed cursor reached
  Postgres as a cast and returned 500 rather than a refused request.
- **Expiring state is not stored.** `prompts` come back only on Mani's newest message,
  decided at serialization. `selected_prompt` persists everywhere — what somebody chose
  is part of the conversation, what they were offered is not.

## Gotchas

- Python 3.14 is new enough that some C-extension wheels may not publish builds yet. If an install fails to compile, check the package's Python support before working around it.
- `pytest.ini` sets `filterwarnings = error`. A warning fails the suite; that is deliberate, so fix the cause rather than filtering it.
- Integration tests skip rather than fail when no database is reachable. A green run that skipped everything is not a passing run — check the count.
- The running app and the integration tests read frameworks and prompts from the database, not from `content/`. After editing a file there, run `python scripts/seed.py`; the app picks it up when its prompt cache expires or the server restarts.
- Run the whole `pytest`, not only `tests/unit`: the integration tests run whole turns against the database.

## Before changing how Mani talks or when it checks and offers

Read `mani-vault/Journal/failure-classes-from-later-branches-2026-10-21.md`, then:

1. State the root cause in one sentence before the fix. A second fix to the same class goes to the `architecture-reviewer` agent.
2. No new gate, window, deadline or cooldown, in code or prompt. If one seems needed, stop and run `/architect`.
3. Cut or swap prompt text; do not add. Every turn speaks from `content/prompts/mani.md`, where the three styles live; there is no per-style prompt file. A prompt or model change passes `python evals/run_eval.py` (no drop of more than 0.15 overall against a side-by-side run, and every rule case passing) before it ships.
4. Mani's text goes out as the model wrote it; code only takes out dashes (`repairs.without_dashes`).
5. Free tests first (`pytest tests/unit tests/integration`); a live run costs the client's tokens, so ask muhammad.
6. Reseed (`python scripts/seed.py`) after content edits, and read the chat against the client's requirements.

## Where things live

- What the service does today and what is open: `backend/PORT-STATUS.md`.
- Lessons from bugs and gotchas: `mani-vault/Journal/`.
- The client's specifications: `backend/docs/specs/`.
