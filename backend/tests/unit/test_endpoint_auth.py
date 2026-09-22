# ABOUTME: Checks every versioned endpoint enforces auth over HTTP, not just in the deps.
# ABOUTME: Routes come from the OpenAPI spec, so a new endpoint is covered without an edit.

import datetime as dt
import uuid

import jwt
import pytest
from fastapi.testclient import TestClient

from mani.auth.jwt import AUDIENCE
from mani.config import get_settings
from main import create_app

# Every turn test in the suite calls orchestrator.send() directly, which is the right shape
# for testing a turn but means nothing had ever exercised the wire: whether the dependency
# that makes an endpoint admin-only is actually attached to it. That is invisible to a unit
# test of require_admin - the function can be perfect and simply not wired to a route - and
# the admin surface reads crisis events. Hence this file.

USER = str(uuid.uuid4())
PLACEHOLDER = "00000000-0000-4000-8000-000000000000"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def _token(secret: str, **claims) -> str:
    payload = {
        "sub": USER,
        "aud": AUDIENCE,
        "role": AUDIENCE,
        "exp": dt.datetime.now(dt.UTC) + dt.timedelta(hours=1),
    } | claims
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.fixture
def secret() -> str:
    """The secret the app is actually configured with, so a minted token really verifies.

    Skips rather than passing vacuously when the project is configured for JWKS instead -
    a token signed with a secret nobody checks would prove nothing.
    """
    configured = get_settings().supabase_jwt_secret
    if not configured:
        pytest.skip("project is configured for JWKS; cannot mint a symmetric token")
    return configured


def _routes(client: TestClient) -> list[tuple[str, str]]:
    """Every versioned path and method in the served spec, with ids filled in."""
    spec = client.app.openapi()
    found = []
    for path, operations in spec["paths"].items():
        if not path.startswith("/v1/"):
            continue
        concrete = path
        while "{" in concrete:
            head, _, rest = concrete.partition("{")
            _, _, tail = rest.partition("}")
            concrete = f"{head}{PLACEHOLDER}{tail}"
        for method in operations:
            found.append((method.upper(), concrete))
    return found


def test_the_spec_actually_lists_the_routes_we_think_it_does(client):
    """Guards the two tests below: if the spec came back empty they would pass having
    asserted nothing at all."""
    routes = _routes(client)
    paths = {path for _, path in routes}
    assert len(routes) >= 20, f"only found {len(routes)} versioned routes"
    assert any(p.startswith("/v1/admin/") for p in paths), "no admin routes in the spec"
    assert f"/v1/threads/{PLACEHOLDER}/messages" in paths, "the turn endpoint is missing"


def test_no_versioned_endpoint_answers_without_a_token(client):
    """401 and not 403: a client refreshes its session on the first and signs the person
    out on the second."""
    failures = []
    for method, path in _routes(client):
        response = client.request(method, path)
        if response.status_code != 401:
            failures.append(f"{method} {path} -> {response.status_code}")
    assert not failures, "answered without a token:\n" + "\n".join(failures)


def test_every_admin_endpoint_refuses_an_ordinary_signed_in_user(client, secret):
    """The dependency is only protection if it is attached to the route. A valid token for
    a real, non-admin user must get 403 from every admin path - never 200, and never a 500
    from having reached the database first."""
    ordinary = _token(secret)
    failures = []
    for method, path in _routes(client):
        if not path.startswith("/v1/admin/"):
            continue
        response = client.request(
            method, path, headers={"Authorization": f"Bearer {ordinary}"}, json={}
        )
        if response.status_code != 403:
            failures.append(f"{method} {path} -> {response.status_code}")
    assert not failures, "reachable by a non-admin:\n" + "\n".join(failures)


def test_admin_metadata_from_the_user_editable_half_of_the_token_is_ignored(client, secret):
    """app_metadata is set by the service; user_metadata is writable by the user. Granting
    admin from the wrong one would let anyone promote themselves over the wire."""
    self_promoted = _token(secret, user_metadata={"admin_role": "admin"})
    response = client.get(
        "/v1/admin/prompts", headers={"Authorization": f"Bearer {self_promoted}"}
    )
    assert response.status_code == 403


def test_an_expired_token_is_401_so_the_client_refreshes(client, secret):
    expired = _token(secret, exp=dt.datetime.now(dt.UTC) - dt.timedelta(minutes=1))
    response = client.get("/v1/threads", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401
    assert response.json()["error"]["category"] == "unauthenticated"


def test_a_token_signed_with_the_wrong_secret_is_refused_over_the_wire(client, secret):
    # Long enough to clear the HMAC minimum, so the refusal is about the wrong key rather
    # than a short one - a 401 for the wrong reason would pass while proving nothing.
    wrong = "a-different-secret-that-is-long-enough-to-be-a-real-one"
    response = client.get(
        "/v1/threads", headers={"Authorization": f"Bearer {_token(wrong)}"}
    )
    assert response.status_code == 401
