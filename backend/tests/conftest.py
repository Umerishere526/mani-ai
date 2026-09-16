# ABOUTME: Supplies configuration the app needs at import time, before collection.
# ABOUTME: Defers to backend/.env when it exists so tests hit the same database you do.

import os
import pathlib

ENV_FILE = pathlib.Path(__file__).resolve().parent.parent / ".env"

# Only a fallback, for a machine with no .env - enough for the unit suite to import the
# app. It deliberately does NOT name a database: hardcoding one here once pointed the
# whole integration suite at a different project's schema, where the tests passed
# against tables that were not the ones under test.
FALLBACK = {
    "ENVIRONMENT": "test",
    "SUPABASE_URL": "http://127.0.0.1:54341",
    "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key",
    "SENTRY_DSN": "",
    "OPENROUTER_API_KEY": "test-openrouter-key",
}

for key, value in FALLBACK.items():
    os.environ.setdefault(key, value)

if not ENV_FILE.exists():
    # No .env, so nothing else will supply a database. Integration tests skip when this
    # points at nothing listening, which is the intended outcome.
    os.environ.setdefault(
        "DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
    )
