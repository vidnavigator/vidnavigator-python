"""Unit tests for webhook signature verification and event parsing."""

import hashlib
import hmac
import json

import pytest

from vidnavigator import (
    WebhookSignatureError,
    construct_webhook_event,
    verify_webhook_signature,
)
from vidnavigator.webhooks import compute_webhook_signature

SECRET = "whsec_test"
NOW = 1_790_000_000

EVENT = {
    "id": "evt_9f2c1b4e8a7d4c1e9b3a5f6d7c8e9a0b",
    "type": "transcribe.completed",
    "created_at": "2026-09-25T15:41:13Z",
    "api_version": "1.0.0",
    "data": {
        "task_id": "task_1",
        "task_status": "completed",
        "job_type": "transcribe",
        "check_status_url": "/v1/transcribe/task_1",
        "result": {"video_info": {"title": "T"}, "transcript": "hello"},
        "result_truncated": False,
    },
}
BODY = json.dumps(EVENT).encode("utf-8")


def _header(body=BODY, secret=SECRET, ts=NOW):
    sig = hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


def test_compute_signature_matches_spec():
    expected = hmac.new(SECRET.encode(), f"{NOW}.".encode() + BODY, hashlib.sha256).hexdigest()
    assert compute_webhook_signature(BODY, SECRET, NOW) == expected
    assert compute_webhook_signature(BODY.decode(), SECRET, NOW) == expected


def test_verify_valid_signature_bytes_and_str():
    verify_webhook_signature(BODY, _header(), SECRET, now=NOW)
    verify_webhook_signature(BODY.decode("utf-8"), _header(), SECRET, now=NOW + 10)


def test_verify_accepts_any_matching_v1():
    good = _header().split("v1=")[1]
    header = f"t={NOW},v1={'0' * 64},v1={good}"
    verify_webhook_signature(BODY, header, SECRET, now=NOW)


def test_verify_tolerates_whitespace_in_header():
    ts, v1 = _header().split(",")
    verify_webhook_signature(BODY, f" {ts} , {v1} ", SECRET, now=NOW)


@pytest.mark.parametrize(
    "header",
    [None, "", "garbage", f"t={NOW}", "v1=abc", f"t=notanint,v1=abc"],
    ids=["none", "empty", "garbage", "no-v1", "no-t", "bad-t"],
)
def test_verify_rejects_missing_or_malformed_header(header):
    with pytest.raises(WebhookSignatureError):
        verify_webhook_signature(BODY, header, SECRET, now=NOW)


def test_verify_rejects_wrong_secret():
    with pytest.raises(WebhookSignatureError, match="does not match"):
        verify_webhook_signature(BODY, _header(secret="other"), SECRET, now=NOW)


def test_verify_rejects_tampered_body():
    with pytest.raises(WebhookSignatureError, match="does not match"):
        verify_webhook_signature(BODY + b" ", _header(), SECRET, now=NOW)


def test_verify_rejects_stale_and_future_timestamps():
    with pytest.raises(WebhookSignatureError, match="tolerance"):
        verify_webhook_signature(BODY, _header(), SECRET, now=NOW + 301)
    with pytest.raises(WebhookSignatureError, match="tolerance"):
        verify_webhook_signature(BODY, _header(), SECRET, now=NOW - 301)


def test_verify_custom_or_disabled_tolerance():
    verify_webhook_signature(BODY, _header(), SECRET, now=NOW + 3000, tolerance_seconds=3600)
    verify_webhook_signature(BODY, _header(), SECRET, now=NOW + 10 ** 6, tolerance_seconds=None)


def test_construct_webhook_event_parses_completed_event():
    event = construct_webhook_event(BODY, _header(), SECRET, now=NOW)
    assert event.id.startswith("evt_")
    assert event.type == "transcribe.completed"
    assert event.api_version == "1.0.0"
    assert event.data.task_id == "task_1"
    assert event.data.task_status == "completed"
    assert event.data.result["transcript"] == "hello"
    assert event.data.result_truncated is False


def test_construct_webhook_event_failed_and_tiktok_events():
    failed = {
        "id": "evt_1",
        "type": "extract_video.failed",
        "data": {
            "task_id": "t",
            "task_status": "failed",
            "error": {"error": "video_too_long", "message": "x", "http_status": 400},
        },
    }
    body = json.dumps(failed).encode()
    event = construct_webhook_event(body, _header(body), SECRET, now=NOW)
    assert event.data.error.error == "video_too_long"
    assert event.data.result is None

    tiktok = {
        "id": "evt_2",
        "type": "tiktok_search.completed",
        "data": {
            "task_id": "s1",
            "task_status": "completed",
            "result": {"stats": {"results_count": 42}, "download_url_available": True},
        },
    }
    body = json.dumps(tiktok).encode()
    event = construct_webhook_event(body, _header(body), SECRET, now=NOW)
    assert event.data.result["stats"] == {"results_count": 42}
    assert event.data.result["download_url_available"] is True


def test_construct_webhook_event_verifies_before_parsing():
    with pytest.raises(WebhookSignatureError):
        construct_webhook_event(BODY, _header(secret="other"), SECRET, now=NOW)


def test_construct_webhook_event_rejects_non_json_body():
    body = b"not json"
    with pytest.raises(WebhookSignatureError, match="JSON"):
        construct_webhook_event(body, _header(body), SECRET, now=NOW)
