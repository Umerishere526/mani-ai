# ABOUTME: Checks Settings rejects unusable configuration before the app starts.
# ABOUTME: Covers required values, the derived JWKS url, and the cache TTL default.

import pytest
from pydantic import ValidationError

from mani.config import DEV_PROMPT_CACHE_TTL, PROD_PROMPT_CACHE_TTL, Settings

REQUIRED = {
    "database_url": "postgresql://postgres:postgres@127.0.0.1:5432/postgres",
    "supabase_url": "http://192.168.1.10:54331",
    "supabase_service_role_key": "service-role-key",
}


def build(**overrides) -> Settings:
    return Settings(_env_file=None, **(REQUIRED | overrides))


def test_defaults_are_the_safe_choice():
    settings = build()
    assert settings.crisis_blocks_chat is True
    assert settings.ai_debug_mode is False
    assert settings.openrouter_data_collection == "deny"


@pytest.mark.parametrize("missing", sorted(REQUIRED))
def test_missing_required_value_is_rejected(missing, monkeypatch):
    # conftest exports these for the app, so the omitted one must also leave the
    # environment or Settings would simply read it from there.
    monkeypatch.delenv(missing.upper(), raising=False)
    values = {k: v for k, v in REQUIRED.items() if k != missing}
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)


def test_jwks_url_is_derived_from_supabase_url():
    assert build().jwks_url == (
        "http://192.168.1.10:54331/auth/v1/.well-known/jwks.json"
    )


def test_explicit_jwks_url_wins():
    settings = build(supabase_jwks_url="https://example.test/keys")
    assert settings.jwks_url == "https://example.test/keys"


def test_trailing_slash_does_not_double_up():
    settings = build(supabase_url="http://192.168.1.10:54331/")
    assert "//auth" not in settings.jwks_url


def test_prompt_cache_ttl_follows_environment():
    assert build(environment="development").prompt_cache_ttl == DEV_PROMPT_CACHE_TTL
    assert build(environment="production").prompt_cache_ttl == PROD_PROMPT_CACHE_TTL
    assert build(environment="production", prompt_cache_ttl_seconds=42).prompt_cache_ttl == 42


def test_unknown_environment_is_rejected():
    with pytest.raises(ValidationError):
        build(environment="staging")


def test_routing_pins_the_upstream_provider_by_default():
    # Unpinned, OpenRouter may send a conversation to any provider serving the model.
    routing = build().routing()
    assert routing["order"] == ["google-ai-studio"]
    assert routing["allow_fallbacks"] is False
    assert routing["data_collection"] == "deny"


def test_a_prompt_can_override_routing_without_losing_the_data_policy():
    routing = build().routing({"order": ["vertex"]})
    assert routing["order"] == ["vertex"]
    assert routing["data_collection"] == "deny"
