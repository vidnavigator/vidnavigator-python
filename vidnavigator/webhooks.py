"""Helpers for receiving VidNavigator webhook deliveries.

Each delivery is signed in the ``X-VidNavigator-Signature`` header as
``t=<unix_ts>,v1=<hex>``, where ``v1`` is ``HMAC-SHA256(secret, f"{t}.{raw_body}")``.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import List, Optional, Tuple, Union

from .exceptions import WebhookSignatureError
from . import models

SIGNATURE_HEADER = "X-VidNavigator-Signature"
DELIVERY_HEADER = "X-VidNavigator-Delivery"
EVENT_HEADER = "X-VidNavigator-Event"
TASK_ID_HEADER = "X-VidNavigator-Task-Id"

DEFAULT_TOLERANCE_SECONDS = 300


def _to_bytes(value: Union[str, bytes]) -> bytes:
    return value.encode("utf-8") if isinstance(value, str) else value


def _parse_signature_header(header: str) -> Tuple[Optional[int], List[str]]:
    timestamp: Optional[int] = None
    signatures: List[str] = []
    for part in header.split(","):
        key, sep, value = part.strip().partition("=")
        if not sep:
            continue
        if key == "t":
            try:
                timestamp = int(value)
            except ValueError:
                timestamp = None
        elif key == "v1":
            signatures.append(value)
    return timestamp, signatures


def compute_webhook_signature(payload: Union[str, bytes], secret: str, timestamp: int) -> str:
    """Return the hex ``v1`` signature for *payload* signed at *timestamp*."""
    signed = f"{timestamp}.".encode("utf-8") + _to_bytes(payload)
    return hmac.new(_to_bytes(secret), signed, hashlib.sha256).hexdigest()


def verify_webhook_signature(
    payload: Union[str, bytes],
    signature_header: Optional[str],
    secret: str,
    *,
    tolerance_seconds: Optional[int] = DEFAULT_TOLERANCE_SECONDS,
    now: Optional[float] = None,
) -> None:
    """Verify a webhook delivery, raising :class:`WebhookSignatureError` if it is invalid.

    Parameters
    ----------
    payload:
        The **raw** request body, exactly as received (do not re-serialize parsed JSON).
    signature_header:
        Value of the ``X-VidNavigator-Signature`` header.
    secret:
        Your webhook signing secret from Studio → API.
    tolerance_seconds:
        Reject deliveries whose timestamp is further than this from *now*
        (default 5 minutes). Pass ``None`` to skip the freshness check.
    """
    if not signature_header:
        raise WebhookSignatureError("Missing webhook signature header")
    timestamp, signatures = _parse_signature_header(signature_header)
    if timestamp is None or not signatures:
        raise WebhookSignatureError("Malformed webhook signature header")

    expected = compute_webhook_signature(payload, secret, timestamp)
    if not any(hmac.compare_digest(expected, sig) for sig in signatures):
        raise WebhookSignatureError("Webhook signature does not match")

    if tolerance_seconds is not None:
        current = time.time() if now is None else now
        if abs(current - timestamp) > tolerance_seconds:
            raise WebhookSignatureError("Webhook timestamp is outside the tolerance window")


def construct_webhook_event(
    payload: Union[str, bytes],
    signature_header: Optional[str],
    secret: str,
    *,
    tolerance_seconds: Optional[int] = DEFAULT_TOLERANCE_SECONDS,
    now: Optional[float] = None,
) -> models.WebhookEvent:
    """Verify a webhook delivery and parse it into a :class:`~vidnavigator.models.WebhookEvent`."""
    verify_webhook_signature(
        payload,
        signature_header,
        secret,
        tolerance_seconds=tolerance_seconds,
        now=now,
    )
    try:
        raw = json.loads(_to_bytes(payload).decode("utf-8"))
    except ValueError as exc:
        raise WebhookSignatureError(f"Webhook body is not valid JSON: {exc}") from exc
    if hasattr(models.WebhookEvent, "model_validate"):
        return models.WebhookEvent.model_validate(raw)
    return models.WebhookEvent.parse_obj(raw)
