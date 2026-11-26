# ABOUTME: Runs sign-up from the real login screen against a real local Supabase Auth, publishable key only.
# ABOUTME: Skips when Supabase is not reachable; every account it creates is deleted afterwards.

from __future__ import annotations

import asyncio
import uuid

import asyncpg
import pytest
import requests
from streamlit.testing.v1 import AppTest

import client as mani
import login


def _supabase_is_up() -> bool:
    try:
        requests.get(f"{mani.SUPABASE_URL}/auth/v1/health", timeout=2)
        return bool(mani.SUPABASE_ANON_KEY and mani.DATABASE_URL)
    except requests.RequestException:
        return False


pytestmark = pytest.mark.skipif(not _supabase_is_up(), reason="local Supabase Auth is not reachable")


def _sql(statement: str, email: str) -> None:
    async def run() -> None:
        conn = await asyncpg.connect(mani.DATABASE_URL)
        try:
            await conn.execute(statement, email)
        finally:
            await conn.close()

    asyncio.run(run())


@pytest.fixture
def email():
    address = f"signup-{uuid.uuid4().hex[:8]}@test.dev"
    yield address
    _sql("delete from auth.users where email = $1", address)


def test_a_sign_up_awaiting_its_confirmation_email_says_so_and_signs_in_once_confirmed(email):
    """Local Supabase confirms accounts by email (enable_confirmations in backend/supabase/config.toml), so signup
    hands back no session."""
    app = AppTest.from_file("app.py", default_timeout=30).run()
    app.text_input(key="sign_up_email").set_value(email)
    app.text_input(key="sign_up_password").set_value("signup-pass1")
    next(b for b in app.button if b.label == "Create account").click().run()

    assert not app.error and not app.exception
    assert [i.value for i in app.info] == [login.CONFIRM_FIRST.format(email=email)]
    assert "client" not in app.session_state
    with pytest.raises(RuntimeError, match="Email not confirmed"):
        mani.sign_in_with_password(email, "signup-pass1")

    # What following the confirmation link does.
    _sql("update auth.users set email_confirmed_at = now() where email = $1", email)
    assert mani.sign_in_with_password(email, "signup-pass1").access_token
