"""Custom exception classes for VidNavigator SDK."""

from typing import Optional


class VidNavigatorError(Exception):
    """Base class for all VidNavigator SDK errors."""


class AuthenticationError(VidNavigatorError):
    """Raised when authentication fails (e.g., missing/invalid API key)."""


class BadRequestError(VidNavigatorError):
    """Raised on HTTP 400 errors (invalid parameters)."""


class AccessDeniedError(VidNavigatorError):
    """Raised on HTTP 403 errors (insufficient permissions)."""


class NotFoundError(VidNavigatorError):
    """Raised when a requested resource is not found (HTTP 404)."""


class RateLimitExceeded(VidNavigatorError):
    """Raised when rate limits are exceeded (HTTP 429)."""


class PaymentRequiredError(VidNavigatorError):
    """Raised when the user has exceeded usage limits and must upgrade (HTTP 402)."""


class GeoRestrictedError(VidNavigatorError):
    """Raised when content is not available in the user's region (HTTP 451)."""


class StorageQuotaExceededError(VidNavigatorError):
    """Raised when storage quota is exceeded (HTTP 413)."""


class SystemOverloadError(VidNavigatorError):
    """Raised when the API is temporarily overloaded or returns HTTP 503."""

    def __init__(self, message: str, *, retry_after_seconds: Optional[int] = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class ServerError(VidNavigatorError):
    """Raised on 5xx server errors (excluding overload mapped to SystemOverloadError)."""
