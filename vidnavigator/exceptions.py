"""Custom exception classes for VidNavigator SDK."""

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


class ServerError(VidNavigatorError):
    """Raised on 5xx server errors.""" 