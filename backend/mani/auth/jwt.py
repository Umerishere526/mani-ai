# ABOUTME: Verifies Supabase-issued JWTs and extracts the caller's identity.
# ABOUTME: The subject from a verified token is the only source of a user id.

import json
from functools import lru_cache
from typing import Any

import jwt
from jwt import PyJWKClient
from pydantic import BaseModel, Field

from mani.config import Settings, get_settings
from mani.errors import ErrorCategory, ServiceError

# Supabase issues user tokens with this audience.
AUDIENCE = "authenticated"

# Projects sign with the shared secret or with a published key set, never both.
SYMMETRIC_ALGORITHMS = ["HS256"]
ASYMMETRIC_ALGORITHMS = ["RS256", "ES256"]

ADMIN_ROLE = "admin"


class Claims(BaseModel):
    """The parts of a verified token the application acts on."""

    sub: str
    role: str = AUDIENCE
    email: str | None = None
    app_metadata: dict[str, Any] = Field(default_factory=dict)
    # Kept verbatim so the database session can be given exactly what was verified.
    raw: dict[str, Any] = Field(default_factory=dict, repr=False)

    @classmethod
    def acting_as(cls, user_id) -> "Claims":
        """A person's identity for work a scheduler runs on their behalf, so RLS scopes every write exactly as it
        does their own requests. Only for jobs the server starts; a request's identity comes from its verified token."""
        return cls(sub=str(user_id), raw={"sub": str(user_id), "role": AUDIENCE})

    @property
    def user_id(self) -> str:
        return self.sub

    @property
    def is_admin(self) -> bool:
        # Matches the previous system: admin is a claim on the token, granted out of
        # band, not a flag any user-facing code can set.
        return self.app_metadata.get("admin_role") == ADMIN_ROLE

    def as_pg_setting(self) -> str:
        """The value for `set local request.jwt.claims`, which makes auth.uid() resolve."""
        return json.dumps(self.raw)


def _unauthorized(message: str) -> ServiceError:
    return ServiceError(
        message,
        ErrorCategory.UNAUTHENTICATED,
        user_message="Your session has expired. Please sign in again.",
    )


@lru_cache
def _jwks_client(url: str, timeout: float) -> PyJWKClient:
    # Caches fetched keys, so verification costs no network call per request. A cache miss fetches
    # with a blocking HTTP call, which stays off the event loop because verify_token is only called
    # from auth/deps.current_user, a plain `def` dependency that FastAPI runs in its threadpool.
    return PyJWKClient(url, cache_keys=True, timeout=timeout)


def verify_token(token: str, settings: Settings | None = None) -> Claims:
    """Verify a Supabase JWT and return its claims, or raise."""
    settings = settings or get_settings()

    if not token:
        raise _unauthorized("no token supplied")

    try:
        if settings.supabase_jwt_secret:
            payload = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=SYMMETRIC_ALGORITHMS,
                audience=AUDIENCE,
                options={"require": ["exp", "sub"]},
            )
        else:
            signing_key = _jwks_client(settings.jwks_url, settings.jwks_timeout_seconds).get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=ASYMMETRIC_ALGORITHMS,
                audience=AUDIENCE,
                options={"require": ["exp", "sub"]},
            )
    except jwt.ExpiredSignatureError as exc:
        raise _unauthorized("token expired") from exc
    except jwt.InvalidAudienceError as exc:
        raise _unauthorized("token is for a different audience") from exc
    except jwt.PyJWTError as exc:
        # Covers a bad signature, a malformed token, and a missing required claim.
        raise _unauthorized(f"token rejected: {exc}") from exc

    subject = payload.get("sub")
    if not subject:
        raise _unauthorized("token carries no subject")

    return Claims(
        sub=subject,
        role=payload.get("role", AUDIENCE),
        email=payload.get("email"),
        app_metadata=payload.get("app_metadata") or {},
        raw=payload,
    )
