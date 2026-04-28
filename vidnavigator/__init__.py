"""VidNavigator Developer API Python client."""

__version__ = "1.0.3"

from .client import VidNavigatorClient
from .exceptions import (
    VidNavigatorError,
    AuthenticationError,
    AccessDeniedError,
    PaymentRequiredError,
    NotFoundError,
    RateLimitExceeded,
    BadRequestError,
    GeoRestrictedError,
    StorageQuotaExceededError,
    SystemOverloadError,
    ServerError,
)

__all__ = [
    "VidNavigatorClient",
    "VidNavigatorError",
    "AuthenticationError",
    "AccessDeniedError",
    "PaymentRequiredError",
    "NotFoundError",
    "RateLimitExceeded",
    "BadRequestError",
    "GeoRestrictedError",
    "StorageQuotaExceededError",
    "SystemOverloadError",
    "ServerError",
]
