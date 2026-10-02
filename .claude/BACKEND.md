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
fastapi dev main.py        # dev server with reload on :8000
fastapi run main.py        # production mode
pytest                     # the whole suite: unit, evals and integration (integration skips without a database)
python scripts/eval_replies.py --scenario <name> --verbose   # real model conversations from scripts/eval_conversations.yaml; removes its own users
./scripts/test_db.sh       # schema + RLS against a throwaway Postgres (needs Docker)
```

**Ports.** `backend/supabase/config.toml` sets `5434x` (API `54341`, Postgres `54342`, Studio `54343`, Mailpit `54344`) so it can run beside the previous project's `5433x`. What is running can differ: on this machine the containers answer on the Supabase defaults (API `54321`, Postgres `54322`, Studio `54323`), and `backend/.env` points there. If this paragraph and `docker ps` disagree, `docker ps` and `backend/.env` are right.

To run the RLS assertions against the real local Supabase rather than a throwaway container:

```bash
docker exec -i supabase_db_mani psql -U postgres -v ON_ERROR_STOP=1 -q < tests/sql/test_rls.sql
```

Without activating, call the venv binaries directly — `./.venv/bin/python`, `./.venv/bin/pip`. Never use a system-wide `python` or `pip` for this project.

## Layout

- `main.py` — `create_app()` plus the module-level `app`. Sentry init and the `ServiceError` handler live here; routes do not.
- `mani/` — the application package, and the only thing that runs. `config.py`, `errors.py`, `routers/`, `auth/`, `models/`, and the `chat/`, `prompts/`, `llm/` and `db/` layers, plus `memory.py`, `summarize.py`, `background.py`, `storage.py` and `auth_admin.py`. `chat/` is the turn: `orchestrator.py` runs it, `router.py` shortlists frameworks, `safety.py` screens, `context.py` builds the `[ctx]` block and the offer timing, `redraft.py` decides when a draft is asked for again, `repairs.py` corrects what remains. **It never reads the filesystem for content** — prompts and frameworks come from the database.
- `content/` — authored markdown, seeded into the `admin` schema by `scripts/seed.py` and never read at runtime. `content/prompts/*.md` become `admin.prompts` (except `somatic.md`, which `seed.py` merges into every framework as the last two stages); `content/frameworks/*.md` become `admin.frameworks`, carrying each framework's per-stage content and its activation data (`central_indication`, `signals`, `to_find_out`, `earliest_offer_message`, `never_offer_when_said`, `contraindications`; `appropriate_when` and `not_when` are read by nothing). Editing one of these changes nothing until it is re-seeded. Kept outside `mani/` because it is input to the database, not code — the same relationship a migration has to the schema.
- `supabase/migrations/` — the schema. `test_harness.sql` stubs what Supabase adds (`auth.users`, `auth.uid()`, the three roles) so the schema can be tested on plain Postgres.
- `tests/unit/` — deterministic logic. `tests/evals/` — checks that frameworks' stage asks and replies keep the specifications' rules (no scenario text, no invented feelings). `tests/integration/` — whole turns against a live database with a scripted model. `tests/sql/` — schema, RLS and privilege assertions run by `scripts/test_db.sh`.
- `scripts/` — `seed.py`, `eval_replies.py` with `eval_conversations.yaml`, `fold_idle_threads.py` (memory folding, also reachable as `GET /internal/cron/fold-summaries` behind `CRON_SECRET`), `test_db.sh`.
- `docs/` — `specs/` holds the client's specifications, one per framework, as the source the content is checked against; `database-schema-reference.md`; `ai-layer-audit.md` (a dated snapshot, read its banner).
- `PORT-STATUS.md` — what the service does, what changed from the implementation it replaces, and what is still open. **Update it in the same change as the work.**
- `requirements.txt` — runtime dependencies only, pinned, hand-maintained. `requirements-dev.txt` adds pytest and `fastapi-cli` on top. **Add a new dependency to whichever file it belongs in** — do not `pip freeze` over them, which buries the packages that matter under their transitive closure and puts a test runner in the deployed image.
- `Dockerfile` — the API process. Platform-agnostic (Fly, Railway, Cloud Run); never Lambda-style, because a turn holds a connection across a multi-second model call.

## Recreating the environment

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

## Conventions

- Use Pydantic models for request and response bodies rather than raw dicts — `pydantic` 2.13 is already installed, as are `pydantic-settings` and `email-validator`.
- Read configuration through `pydantic-settings` and a `.env` file (`python-dotenv` is installed). Never commit secrets or inline them in `main.py`.
- As routes grow past a handful, split them into `APIRouter` modules and include them from `main.py` — don't let `main.py` become a dumping ground.
- `sentry-sdk` is initialised in `create_app()` when `SENTRY_DSN` is set, with `send_default_pii=False` — conversation content is special-category health data and must not ride along on an error report.
- Postgres is reached directly with `asyncpg`, not through PostgREST. A chat turn makes many writes that must succeed or fail together, and PostgREST cannot hold a transaction across statements.
- OpenRouter is the only model provider. LangChain (`langchain-openai`) composes the call and parses the structured reply; the `openai` protocol is used because OpenRouter speaks it — it is not a second provider. The key lives in the environment, never in the database.
- A turn is one model call, or more when a draft has to be asked for again (a feeling the person never named, an offer too early or ruled out, no question). Why, and the limits: `mani-vault/Decisions/`, ADR-002, 006, 007 and 008.

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

- **One error shape, everywhere.** `{"error": {category, message, retryable}}`. Both the
  `ServiceError` and the validation handlers in `main.py` produce it, so a client has one
  branch rather than two. FastAPI's default `{"detail": [...]}` is overridden.
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
- **Every write is a POST/PATCH/DELETE.** `/v1/threads/current` creates a thread and a
  greeting on first call, so it is POST — a GET must be safe, and prefetchers treat it so.
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
- Run the whole `pytest`, not only `tests/unit`: `tests/evals` fails on stage asks that carry scenario text or hand over a feeling word.

## Where things live

- What the service does today and what is open: `backend/PORT-STATUS.md`.
- Why it is built this way: `mani-vault/Decisions/` (start at `_Index.md`), and lessons in `mani-vault/Journal/`.
- The client's specifications: `backend/docs/specs/`.
