# ABOUTME: Supplies configuration the app needs at import time, before collection.
# ABOUTME: Defers to backend/.env when it exists so tests hit the same database you do.

import os
import pathlib

ENV_FILE = pathlib.Path(__file__).resolve().parent.parent / ".env"

if not ENV_FILE.exists():
    # Only a fallback, for a machine with no .env - enough for the unit suite to import
    # the app. Guarded on ENV_FILE, not just os.environ.setdefault, because setdefault
    # alone shadows a real .env whenever pytest runs: these values enter os.environ at
    # conftest import time, and pydantic-settings prefers os.environ over the .env file -
    # so a real key on a machine that HAS a .env was being silently replaced by this
    # placeholder, which is only supposed to stand in when there is nothing else to read.
    # It deliberately does not name a database: hardcoding one here once pointed the whole
    # integration suite at a different project's schema, where the tests passed against
    # tables that were not the ones under test.
    FALLBACK = {
        "ENVIRONMENT": "test",
        "SUPABASE_URL": "http://127.0.0.1:54341",
        "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key",
        "SENTRY_DSN": "",
        "OPENROUTER_API_KEY": "test-openrouter-key",
        "DATABASE_URL": "postgresql://postgres:postgres@127.0.0.1:54322/postgres",
    }
    for key, value in FALLBACK.items():
        os.environ.setdefault(key, value)
