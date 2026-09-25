"""Tests for HTTP status code -> exception mapping in _request()."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from vidnavigator import VidNavigatorClient
from vidnavigator.exceptions import (
    AuthenticationError,
    TooManyActiveJobsError,
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
    (401, AuthenticationError),
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


def test_401_maps_to_authentication_error(client):
    body = {"error": "Invalid API key format", "message": "API key must follow the format"}
    with patch.object(client.session, "request", return_value=_mock_response(401, body)):
        with pytest.raises(AuthenticationError) as exc_info:
            client.health_check()
    assert exc_info.value.status_code == 401
    assert "API key must follow" in str(exc_info.value)


def test_error_carries_code_status_docs_and_payload(client):
    body = {
        "status": "error",
        "error": "invalid_schema",
        "message": "Schema is invalid",
        "docs_url": "https://docs.vidnavigator.com/reference/errors",
    }
    with patch.object(client.session, "request", return_value=_mock_response(400, body)):
        with pytest.raises(BadRequestError) as exc_info:
            client.health_check()
    exc = exc_info.value
    assert exc.status_code == 400
    assert exc.error_code == "invalid_schema"
    assert exc.docs_url == "https://docs.vidnavigator.com/reference/errors"
    assert exc.payload == body
    assert exc.message == "Schema is invalid"


def test_error_code_field_takes_precedence(client):
    body = {"status": "error", "error": "limit_exceeded", "error_code": "insufficient_credits_video_search"}
    with patch.object(client.session, "request", return_value=_mock_response(402, body)):
        with pytest.raises(PaymentRequiredError) as exc_info:
            client.health_check()
    assert exc_info.value.error_code == "insufficient_credits_video_search"


def test_too_many_active_jobs_maps_to_subclass(client):
    body = {"status": "error", "error": "too_many_active_jobs", "message": "Slow down"}
    with patch.object(client.session, "request", return_value=_mock_response(429, body)):
        with pytest.raises(TooManyActiveJobsError) as exc_info:
            client.health_check()
    assert isinstance(exc_info.value, RateLimitExceeded)


def test_non_json_error_body_uses_text(client):
    resp = _mock_response(500)
    resp.json.side_effect = ValueError("no json")
    resp.text = "<html>Bad gateway</html>"
    with patch.object(client.session, "request", return_value=resp):
        with pytest.raises(ServerError, match="Bad gateway"):
            client.health_check()


def test_network_error_wrapped(client):
    with patch.object(client.session, "request", side_effect=requests.ConnectionError("down")):
        with pytest.raises(VidNavigatorError, match="Request failed"):
            client.health_check()


def test_system_overload_keeps_structured_fields(client):
    body = {"status": "error", "error": "system_overload", "message": "Busy", "retry_after_seconds": "12"}
    with patch.object(client.session, "request", return_value=_mock_response(503, body)):
        with pytest.raises(SystemOverloadError) as exc_info:
            client.health_check()
    assert exc_info.value.retry_after_seconds == 12
    assert exc_info.value.error_code == "system_overload"
    assert exc_info.value.status_code == 503
