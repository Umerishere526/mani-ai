# backend — FastAPI

FastAPI 0.141.1 on Python 3.14, in a local virtualenv at `backend/.venv`.

## Commands

Activate the venv before running anything Python:

```bash
cd backend
source .venv/bin/activate
supabase start             # local Supabase on 5434x (Docker must be running)
supabase db reset          # recreate and re-apply migrations
python scripts/seed.py     # loads content/ into admin.frameworks and admin.prompts
fastapi dev main.py        # dev server with reload on :8000
fastapi run main.py        # production mode
pytest                     # unit + integration (integration skips without a database)
./scripts/test_db.sh       # schema + RLS against a throwaway Postgres (needs Docker)
```

The previous project's Supabase occupies `5433x`. This one is on **`5434x`** — API `54341`,
Postgres `54342`, Studio `54343`, Mailpit `54344` — so both can run at once while porting.

To run the RLS assertions against the real local Supabase rather than a throwaway container:

```bash
docker exec -i supabase_db_mani psql -U postgres -v ON_ERROR_STOP=1 -q < tests/sql/test_rls.sql
```

Without activating, call the venv binaries directly — `./.venv/bin/python`, `./.venv/bin/pip`. Never use a system-wide `python` or `pip` for this project.

## Layout

- `main.py` — `create_app()` plus the module-level `app`. Sentry init and the `ServiceError` handler live here; routes do not.
- `mani/` — the application package, and the only thing that runs. `config.py`, `errors.py`, `routers/`, and the `chat/`, `prompts/`, `llm/` and `db/` layers. **It never reads the filesystem for content** — prompts and frameworks come from the database.
- `content/` — authored markdown, seeded into the `admin` schema by `scripts/seed.py` and never read at runtime. `content/prompts/*.md` become `admin.prompts`; `content/frameworks/*.md` become `admin.frameworks`, carrying each framework's per-stage content and its router activation data. Editing one of these changes nothing until it is re-seeded. Kept outside `mani/` because it is input to the database, not code — the same relationship a migration has to the schema.
- `supabase/migrations/` — the schema. `test_harness.sql` stubs what Supabase adds (`auth.users`, `auth.uid()`, the three roles) so the schema can be tested on plain Postgres.
- `tests/unit/` — deterministic logic. `tests/integration/` — whole turns against a live database with a scripted model. `tests/sql/` — schema, RLS and privilege assertions run by `scripts/test_db.sh`.
- `PORT-STATUS.md` — what the service does, what changed from the implementation it replaces, and what is still open. **Update it in the same change as the work.**
- `requirements.txt` — runtime dependencies only, pinned, hand-maintained. `requirements-dev.txt` adds pytest and `fastapi-cli` on top. **Add a new dependency to whichever file it belongs in** — do not `pip freeze` over them, which buries the fifteen packages that matter under their transitive closure and puts a test runner in the deployed image.
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
- OpenRouter is the only model provider. The `openai` package is the client because OpenRouter speaks that protocol — it is not a second provider. The key lives in the environment, never in the database.

## Identity and authorization

This backend is the only thing that touches the database, which makes it the only place authorization exists. Two rules, both non-negotiable:

- **Verify the JWT and derive the user id from it.** Never read a `user_id` from a request body, query parameter, or header — a client that names its own identity can name someone else's. Extract the subject from the verified token and ignore whatever the request claims.
- **Use a user-scoped Supabase client by default**, built per request from the caller's JWT, so Postgres enforces ownership through RLS. The service role key bypasses RLS entirely and is reserved for genuine cross-user work under a distinctly named client. Full reasoning in `.claude/SUPABASE.md`.

## Type safety across the API boundary

There is no shared contract between this backend and the frontends — no tRPC, no compile-time link. `web/` and `mobile/` can drift from the API silently, and mobile is especially unforgiving because it ships as a compiled binary through store review: a mismatch that reaches users waits out a review cycle to fix.

So generate it, and gate it:

- Generate TypeScript types for `web/` and `mobile/` from this app's OpenAPI schema, and commit the output.
- **Fail CI when the committed types don't match the schema.** Without that gate you have swapped a compiler guarantee for a convention, and conventions rot. Do this before the first mobile build ships, not after.
- Keep response models explicit on every route (`response_model=`), or the generated schema degrades to `Any` and the types become decorative.

## Gotchas

- Python 3.14 is new enough that some C-extension wheels may not publish builds yet. If an install fails to compile, check the package's Python support before working around it.
- `pytest.ini` sets `filterwarnings = error`. A warning fails the suite; that is deliberate, so fix the cause rather than filtering it.
- Integration tests skip rather than fail when no database is reachable. A green run that skipped everything is not a passing run — check the count.
