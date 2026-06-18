"""Service-layer exceptions — stable error codes, no ORM/FastAPI dependency."""

from __future__ import annotations


class ServiceError(Exception):
    """Base service error with a stable code and user-safe message."""

    code: str = "service_error"

    def __init__(self, message: str, detail: str | None = None):
        self.message = message
        self.detail = detail
        super().__init__(message)


class IndexNotReadyError(ServiceError):
    code = "index_not_ready"


class InvalidSearchRequestError(ServiceError):
    code = "invalid_search_request"


class UnsupportedSearchModeError(ServiceError):
    code = "unsupported_search_mode"


class UserNotFoundError(ServiceError):
    code = "user_not_found"


class ProfileNotReadyError(ServiceError):
    code = "profile_not_ready"


class ServiceInitializationError(ServiceError):
    code = "service_initialization_error"
