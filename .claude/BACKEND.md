# backend — FastAPI

FastAPI 0.141.1 on Python 3.14, in a local virtualenv at `backend/.venv`.

## Commands

Activate the venv before running anything Python:

```bash
cd backend
source .venv/bin/activate
fastapi dev main.py        # dev server with reload on :8000
fastapi run main.py        # production mode
```

Without activating, call the venv binaries directly — `./.venv/bin/python`, `./.venv/bin/pip`. Never use a system-wide `python` or `pip` for this project.

## Layout

- `main.py` — the entire app today: a `FastAPI()` instance named `app` and a single `GET /` route.
- `requirements.txt` — generated with `pip freeze`. **Regenerate it whenever you add a dependency:**
  ```bash
  ./.venv/bin/pip freeze > requirements.txt
  ```

## Recreating the environment

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Conventions

- Use Pydantic models for request and response bodies rather than raw dicts — `pydantic` 2.13 is already installed, as are `pydantic-settings` and `email-validator`.
- Read configuration through `pydantic-settings` and a `.env` file (`python-dotenv` is installed). Never commit secrets or inline them in `main.py`.
- As routes grow past a handful, split them into `APIRouter` modules and include them from `main.py` — don't let `main.py` become a dumping ground.
- `sentry-sdk` is installed but not initialized. Either wire it up deliberately or drop the dependency; leaving it half-present is worse than either.

## Gotchas

- Python 3.14 is new enough that some C-extension wheels may not publish builds yet. If an install fails to compile, check the package's Python support before working around it.
- The backend has no tests and no test runner installed. Adding one means installing `pytest` and `httpx` (httpx is already present) and refreshing `requirements.txt`.
