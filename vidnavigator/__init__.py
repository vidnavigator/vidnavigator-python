"""VidNavigator Developer API Python client."""

__version__ = "2.0.0"

from .client import VidNavigatorClient
from .jobs import Job
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
    JobTimeoutError,
    WebhookSignatureError,
)
from .webhooks import construct_webhook_event, verify_webhook_signature

__all__ = [
    "VidNavigatorClient",
    "Job",
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
    "JobTimeoutError",
    "WebhookSignatureError",
    "construct_webhook_event",
    "verify_webhook_signature",
]
