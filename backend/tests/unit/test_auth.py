# ABOUTME: Checks that only a validly signed, unexpired Supabase token grants identity.
# ABOUTME: The user id must come from the signature, never from anything a caller can set.

import datetime as dt
import uuid

from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from mani.auth import jwt as auth_jwt
from mani.auth.jwt import AUDIENCE, Claims, verify_token
from mani.config import Settings
from mani.errors import ServiceError

SECRET = "super-secret-jwt-token-with-at-least-32-characters-long"
USER = str(uuid.uuid4())
# What local Supabase Auth puts in `iss`: the API URL with /auth/v1 (GOTRUE_JWT_ISSUER).
ISSUER = "http://127.0.0.1:54341/auth/v1"


def settings(**overrides) -> Settings:
    base = {
        "database_url": "postgresql://postgres:postgres@127.0.0.1:54342/postgres",
        "supabase_url": "http://127.0.0.1:54341",
        "supabase_service_role_key": "k",
        "supabase_jwt_secret": SECRET,
    }
    return Settings(_env_file=None, **(base | overrides))


def token(secret: str = SECRET, **claims) -> str:
    payload = {
        "sub": USER,
        "aud": AUDIENCE,
        "role": AUDIENCE,
        "iss": ISSUER,
        "exp": dt.datetime.now(dt.UTC) + dt.timedelta(hours=1),
    } | claims
    return jwt.encode(payload, secret, algorithm="HS256")


def test_a_valid_token_yields_its_subject():
    claims = verify_token(token(email="a@example.test"), settings())
    assert claims.user_id == USER
    assert claims.email == "a@example.test"
    assert claims.is_admin is False


def test_a_token_signed_with_another_secret_is_refused():
    with pytest.raises(ServiceError):
        verify_token(token(secret="a-different-secret-entirely-not-ours"), settings())


def test_an_expired_token_is_refused():
    expired = token(exp=dt.datetime.now(dt.UTC) - dt.timedelta(seconds=1))
    with pytest.raises(ServiceError):
        verify_token(expired, settings())


def test_a_token_for_another_audience_is_refused():
    with pytest.raises(ServiceError):
        verify_token(token(aud="some-other-service"), settings())


def test_a_token_without_a_subject_is_refused():
    # jwt.encode will happily omit `sub`; the verifier must not.
    payload = {
        "aud": AUDIENCE,
        "exp": dt.datetime.now(dt.UTC) + dt.timedelta(hours=1),
    }
    with pytest.raises(ServiceError):
        verify_token(jwt.encode(payload, SECRET, algorithm="HS256"), settings())


def test_a_token_from_another_issuer_is_refused():
    """Another Supabase project, or anything else holding a key this one trusts, signs tokens with its own issuer."""
    with pytest.raises(ServiceError, match="different issuer"):
        verify_token(token(iss="https://another-project.supabase.co/auth/v1"), settings())


def test_a_token_without_an_issuer_is_refused():
    payload = {"sub": USER, "aud": AUDIENCE, "exp": dt.datetime.now(dt.UTC) + dt.timedelta(hours=1)}
    with pytest.raises(ServiceError):
        verify_token(jwt.encode(payload, SECRET, algorithm="HS256"), settings())


def test_a_supabase_url_with_a_trailing_slash_still_matches_the_issuer():
    assert verify_token(token(), settings(supabase_url="http://127.0.0.1:54341/")).user_id == USER


def test_a_token_verified_against_the_key_set_is_held_to_the_issuer_too(monkeypatch):
    """The JWKS path, which local and hosted projects use, checks the issuer exactly as the secret path does."""
    private = ec.generate_private_key(ec.SECP256R1())
    monkeypatch.setattr(auth_jwt, "_jwks_client", lambda url, timeout: SimpleNamespace(
        get_signing_key_from_jwt=lambda _: SimpleNamespace(key=private.public_key())
    ))
    keyed = settings(supabase_jwt_secret="")

    def signed(**claims) -> str:
        payload = {"sub": USER, "aud": AUDIENCE, "iss": ISSUER,
                   "exp": dt.datetime.now(dt.UTC) + dt.timedelta(hours=1)} | claims
        return jwt.encode(payload, private, algorithm="ES256")

    assert verify_token(signed(), keyed).user_id == USER
    with pytest.raises(ServiceError, match="different issuer"):
        verify_token(signed(iss="https://another-project.supabase.co/auth/v1"), keyed)


@pytest.mark.parametrize("bad", ["", "not-a-token", "a.b.c"])
def test_rubbish_is_refused(bad):
    with pytest.raises(ServiceError):
        verify_token(bad, settings())


def test_an_unsigned_token_is_refused():
    # The `alg: none` attack: a well-formed token with no signature at all.
    forged = jwt.encode({"sub": USER, "aud": AUDIENCE}, key="", algorithm="none")
    with pytest.raises(ServiceError):
        verify_token(forged, settings())


def test_admin_comes_from_app_metadata_only():
    plain = verify_token(token(user_metadata={"admin_role": "admin"}), settings())
    assert plain.is_admin is False, "user_metadata is user-editable and must not grant admin"

    real = verify_token(token(app_metadata={"admin_role": "admin"}), settings())
    assert real.is_admin is True


def test_claims_round_trip_for_the_database_session():
    import json

    claims = verify_token(token(), settings())
    # auth.uid() reads `sub` out of exactly this value.
    assert json.loads(claims.as_pg_setting())["sub"] == USER


def test_identity_ignores_anything_the_caller_asserts():
    someone_else = str(uuid.uuid4())
    claims = verify_token(token(user_id=someone_else, id=someone_else), settings())
    assert claims.user_id == USER


def test_claims_do_not_leak_the_token_in_a_repr():
    claims = Claims(sub=USER, raw={"sub": USER, "secret": "value"})
    assert "secret" not in repr(claims)
