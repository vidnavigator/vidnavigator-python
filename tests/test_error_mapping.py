"""Tests for HTTP status code -> exception mapping in _request()."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from vidnavigator import VidNavigatorClient
from vidnavigator.exceptions import (
    BadRequestError,
    PaymentRequiredError,
    AccessDeniedError,
    NotFoundError,
    StorageQuotaExceededError,
    RateLimitExceeded,
    GeoRestrictedError,
    SystemOverloadError,
    ServerError,
    VidNavigatorError,
)


@pytest.fixture
def client():
    return VidNavigatorClient(api_key="test_key")


def _mock_response(status_code, json_body=None):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.ok = 200 <= status_code < 300
    resp.reason = "Mocked"
    resp.text = ""
    resp.json.return_value = json_body or {"status": "error", "message": "test error"}
    return resp


ERROR_CASES = [
    (400, BadRequestError),
    (402, PaymentRequiredError),
    (403, AccessDeniedError),
    (404, NotFoundError),
    (413, StorageQuotaExceededError),
    (429, RateLimitExceeded),
    (451, GeoRestrictedError),
    (500, ServerError),
    (502, ServerError),
]


@pytest.mark.parametrize("status_code,expected_exc", ERROR_CASES)
def test_error_status_mapping(client, status_code, expected_exc):
    mock_resp = _mock_response(status_code)
    with patch.object(client.session, "request", return_value=mock_resp):
        with pytest.raises(expected_exc):
            client.health_check()


def test_503_maps_to_system_overload_with_retry(client):
    body = {
        "status": "error",
        "error": "system_overload",
        "message": "Too busy",
        "retry_after_seconds": 30,
    }
    mock_resp = _mock_response(503, body)
    with patch.object(client.session, "request", return_value=mock_resp):
        with pytest.raises(SystemOverloadError) as exc_info:
            client.health_check()
    assert exc_info.value.retry_after_seconds == 30
    assert "Too busy" in str(exc_info.value)


def test_503_without_retry_after(client):
    body = {"status": "error", "message": "overloaded"}
    mock_resp = _mock_response(503, body)
    with patch.object(client.session, "request", return_value=mock_resp):
        with pytest.raises(SystemOverloadError) as exc_info:
            client.health_check()
    assert exc_info.value.retry_after_seconds is None


def test_unexpected_status_raises_base_error(client):
    mock_resp = _mock_response(418)
    with patch.object(client.session, "request", return_value=mock_resp):
        with pytest.raises(VidNavigatorError, match="Unexpected response"):
            client.health_check()
