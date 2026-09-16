# ABOUTME: FastAPI dependencies that turn an Authorization header into a verified caller.
# ABOUTME: Endpoints take CurrentUser or AdminUser; they never read an id from the request.

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from mani.auth.jwt import Claims, verify_token
from mani.errors import ErrorCategory, ServiceError

# auto_error=False so a missing header raises our own error shape rather than FastAPI's.
_bearer = HTTPBearer(auto_error=False, description="Supabase access token")


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Claims:
    if credentials is None:
        raise ServiceError(
            "request carried no bearer token",
            ErrorCategory.UNAUTHENTICATED,
            user_message="Please sign in to continue.",
        )
    return verify_token(credentials.credentials)


def require_admin(user: Annotated[Claims, Depends(current_user)]) -> Claims:
    if not user.is_admin:
        raise ServiceError(
            f"user {user.user_id} is not an admin",
            ErrorCategory.FORBIDDEN,
            user_message="You do not have access to this.",
        )
    return user


CurrentUser = Annotated[Claims, Depends(current_user)]
AdminUser = Annotated[Claims, Depends(require_admin)]
