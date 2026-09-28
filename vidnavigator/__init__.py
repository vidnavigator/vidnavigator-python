"""VidNavigator Developer API Python client."""

__version__ = "2.1.0"

from .client import VidNavigatorClient
from .async_client import AsyncVidNavigatorClient
from .jobs import AsyncJob, Job
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
    "AsyncVidNavigatorClient",
    "Job",
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
    "JobTimeoutError",
    "WebhookSignatureError",
    "construct_webhook_event",
    "verify_webhook_signature",
]
