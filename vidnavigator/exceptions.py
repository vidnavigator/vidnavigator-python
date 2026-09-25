"""Custom exception classes for VidNavigator SDK."""

from typing import Any, Dict, Optional


class VidNavigatorError(Exception):
    """Base class for all VidNavigator SDK errors.

    API errors carry the details from the JSON error body:

    - ``status_code``: HTTP status (``None`` for client-side errors)
    - ``error_code``: machine-readable code such as ``"invalid_schema"``
    - ``docs_url``: link to the relevant documentation, when provided
    - ``payload``: the full decoded error body
    """

    def __init__(
        self,
        message: str = "",
        *,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        docs_url: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.docs_url = docs_url
        self.payload = payload


class AuthenticationError(VidNavigatorError):
    """Raised when authentication fails (e.g., missing/invalid API key, HTTP 401)."""


class BadRequestError(VidNavigatorError):
    """Raised on HTTP 400 errors (invalid parameters)."""


class AccessDeniedError(VidNavigatorError):
    """Raised on HTTP 403 errors (insufficient permissions)."""


class NotFoundError(VidNavigatorError):
    """Raised when a requested resource is not found (HTTP 404)."""


class RateLimitExceeded(VidNavigatorError):
    """Raised when rate limits are exceeded (HTTP 429)."""


class TooManyActiveJobsError(RateLimitExceeded):
    """Raised when a job submit is rejected (HTTP 429) because too many jobs are already running.

    No task is created; retry once some of your running jobs finish.
    """


class PaymentRequiredError(VidNavigatorError):
    """Raised on HTTP 402: not enough credits (including at job submit time, when no task is created)."""


class GeoRestrictedError(VidNavigatorError):
    """Raised when content is not available in the user's region (HTTP 451)."""


class StorageQuotaExceededError(VidNavigatorError):
    """Raised when storage quota is exceeded (HTTP 413)."""


class SystemOverloadError(VidNavigatorError):
    """Raised when the API is temporarily overloaded or returns HTTP 503."""

    def __init__(
        self,
        message: str = "",
        *,
        retry_after_seconds: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.retry_after_seconds = retry_after_seconds


class ServerError(VidNavigatorError):
    """Raised on 5xx server errors (excluding overload mapped to SystemOverloadError)."""


class AsyncJobTimeoutError(VidNavigatorError):
    """Raised when a blocking call stops waiting for a job that has not finished.

    The job keeps running server-side and its result stays readable for 1 hour
    after it finishes. ``task_id`` identifies it; ``job`` is a ready-to-use
    :class:`~vidnavigator.AsyncJob` handle, so ``exc.job.result()`` resumes waiting.
    """

    def __init__(self, message: str, *, task_id: str, job: Any = None) -> None:
        super().__init__(message)
        self.task_id = task_id
        self.job = job


class WebhookSignatureError(VidNavigatorError):
    """Raised when a webhook delivery fails signature or timestamp verification."""


_STATUS_EXCEPTIONS = {
    400: BadRequestError,
    401: AuthenticationError,
    402: PaymentRequiredError,
    403: AccessDeniedError,
    404: NotFoundError,
    413: StorageQuotaExceededError,
    429: RateLimitExceeded,
    451: GeoRestrictedError,
}

_ERROR_CODE_EXCEPTIONS = {
    "too_many_active_jobs": TooManyActiveJobsError,
}


def error_from_response(
    status_code: Optional[int],
    payload: Optional[Dict[str, Any]] = None,
    *,
    reason: Optional[str] = None,
) -> VidNavigatorError:
    """Build the exception matching an API error status and body.

    Used both for HTTP error responses and for the ``error`` object of failed
    async jobs, so the same ``except`` clauses work for sync and async calls.
    """
    payload = payload or {}
    message = payload.get("message") or reason or ""
    error_code = payload.get("error_code") or payload.get("error")
    if not isinstance(error_code, str):
        error_code = None
    kwargs: Dict[str, Any] = {
        "status_code": status_code,
        "error_code": error_code,
        "docs_url": payload.get("docs_url"),
        "payload": payload,
    }

    exc_cls = _ERROR_CODE_EXCEPTIONS.get(error_code or "")
    if exc_cls is not None:
        return exc_cls(message, **kwargs)
    if status_code in _STATUS_EXCEPTIONS:
        return _STATUS_EXCEPTIONS[status_code](message, **kwargs)
    if status_code == 503:
        retry_int = None
        raw_retry = payload.get("retry_after_seconds")
        if raw_retry is not None:
            try:
                retry_int = int(raw_retry)
            except (TypeError, ValueError):
                retry_int = None
        return SystemOverloadError(message, retry_after_seconds=retry_int, **kwargs)
    if status_code is not None and status_code >= 500:
        return ServerError(message, **kwargs)
    return VidNavigatorError(f"Unexpected response ({status_code}): {message}", **kwargs)
