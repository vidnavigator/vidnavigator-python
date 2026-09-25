"""VidNavigator Developer API Python client."""

__version__ = "2.0.0"

from .client import VidNavigatorClient
from .jobs import AsyncJob
from .exceptions import (
    VidNavigatorError,
    AuthenticationError,
    AccessDeniedError,
    PaymentRequiredError,
    NotFoundError,
    RateLimitExceeded,
    TooManyActiveJobsError,
    BadRequestError,
    GeoRestrictedError,
    StorageQuotaExceededError,
    SystemOverloadError,
    ServerError,
    AsyncJobTimeoutError,
    WebhookSignatureError,
)
from .webhooks import construct_webhook_event, verify_webhook_signature

__all__ = [
    "VidNavigatorClient",
    "AsyncJob",
    "VidNavigatorError",
    "AuthenticationError",
    "AccessDeniedError",
    "PaymentRequiredError",
    "NotFoundError",
    "RateLimitExceeded",
    "TooManyActiveJobsError",
    "BadRequestError",
    "GeoRestrictedError",
    "StorageQuotaExceededError",
    "SystemOverloadError",
    "ServerError",
    "AsyncJobTimeoutError",
    "WebhookSignatureError",
    "construct_webhook_event",
    "verify_webhook_signature",
]
