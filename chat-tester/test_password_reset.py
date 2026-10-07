# ABOUTME: Runs the on-page password reset against a real local Supabase Auth and the real login screen.
# ABOUTME: Skips when Supabase is not reachable; every account it creates is deleted afterwards.

from __future__ import annotations

import uuid

import pytest
import requests
from streamlit.testing.v1 import AppTest

import client as mani


def _supabase_is_up() -> bool:
    try:
        requests.get(f"{mani.SUPABASE_URL}/auth/v1/health", timeout=2)
        return bool(mani.SUPABASE_ANON_KEY and mani.SUPABASE_SERVICE_ROLE_KEY)
    except requests.RequestException:
        return False


pytestmark = pytest.mark.skipif(not _supabase_is_up(), reason="local Supabase Auth is not reachable")


@pytest.fixture
def account():
    email = f"reset-{uuid.uuid4().hex[:8]}@test.dev"
    mani.sign_up(email, "oldpass1")
    yield email
    requests.delete(
        f"{mani.SUPABASE_URL}/auth/v1/admin/users/{mani._user_id_for(email)}",
        headers=mani._admin_headers(), timeout=10,
    )


def test_reset_replaces_the_password_whatever_the_email_case(account):
    session = mani.reset_password(account.upper(), "newpass1")

    assert session.access_token
    with pytest.raises(RuntimeError):
        mani.sign_in_with_password(account, "oldpass1")
    assert mani.sign_in_with_password(account, "newpass1").user_id == session.user_id


def test_reset_for_an_unknown_email_is_refused():
    with pytest.raises(RuntimeError, match="No account with that email"):
        mani.reset_password(f"nobody-{uuid.uuid4().hex[:8]}@test.dev", "newpass1")


def _submit_reset(app: AppTest, email: str, password: str, again: str) -> None:
    app.text_input(key="reset_email").set_value(email)
    app.text_input(key="reset_password").set_value(password)
    app.text_input(key="reset_password_again").set_value(again)
    next(b for b in app.button if b.label == "Set new password").click().run()


def test_login_screen_checks_the_two_passwords_before_calling_supabase(account):
    app = AppTest.from_file("app.py", default_timeout=30).run()

    _submit_reset(app, account, "newpass1", "different")
    assert [e.value for e in app.error] == ["Those two passwords are not the same."]

    _submit_reset(app, account, "abcdef1", "abcdef1")
    assert [e.value for e in app.error] == ["A password needs at least eight characters."]

    mani.sign_in_with_password(account, "oldpass1")


def test_login_screen_signs_in_after_a_reset(account):
    app = AppTest.from_file("app.py", default_timeout=30).run()

    _submit_reset(app, account, "newpass1", "newpass1")

    assert not app.error and not app.exception
    assert app.session_state["email"] == account
    mani.sign_in_with_password(account, "newpass1")
