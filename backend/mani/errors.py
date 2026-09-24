# ABOUTME: The error type services raise and routers translate into HTTP responses.
# ABOUTME: Every raise carries a category and a sentence safe to show the user.

from enum import StrEnum


class ErrorCategory(StrEnum):
    RATE_LIMITED = "rate_limited"
    LLM_UNAVAILABLE = "llm_unavailable"
    LLM_TIMEOUT = "llm_timeout"
    STORAGE_ERROR = "storage_error"
    AUTH_PROVIDER_ERROR = "auth_provider_error"
    CONFIG_ERROR = "config_error"
    NOT_FOUND = "not_found"
    INVALID_REQUEST = "invalid_request"
    # The request contradicts one already made, e.g. a message id reused for a new message.
    CONFLICT = "conflict"
    # No usable token. Distinct from FORBIDDEN because a client refreshes its session
    # on 401 and gives up on 403 - collapsing the two makes an expired token look like
    # a permission failure and logs the person out instead of renewing them.
    UNAUTHENTICATED = "unauthenticated"
    FORBIDDEN = "forbidden"
    UNKNOWN = "unknown"


STATUS_BY_CATEGORY = {
    ErrorCategory.RATE_LIMITED: 429,
    ErrorCategory.LLM_UNAVAILABLE: 502,
    ErrorCategory.LLM_TIMEOUT: 504,
    ErrorCategory.STORAGE_ERROR: 500,
    ErrorCategory.AUTH_PROVIDER_ERROR: 502,
    ErrorCategory.CONFIG_ERROR: 500,
    ErrorCategory.NOT_FOUND: 404,
    ErrorCategory.INVALID_REQUEST: 422,
    ErrorCategory.CONFLICT: 409,
    ErrorCategory.UNAUTHENTICATED: 401,
    ErrorCategory.FORBIDDEN: 403,
    ErrorCategory.UNKNOWN: 500,
}


class ServiceError(Exception):
    """Raised by services. `message` is for logs, `user_message` for the client."""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        *,
        retryable: bool = False,
        user_message: str = "Something went wrong. Please try again.",
    ) -> None:
        super().__init__(message)
        self.category = category
        self.retryable = retryable
        self.user_message = user_message

    @property
    def status_code(self) -> int:
        return STATUS_BY_CATEGORY[self.category]
