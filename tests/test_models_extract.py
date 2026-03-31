"""Model parsing tests for extraction responses (no network)."""

from vidnavigator.client import _parse_model
from vidnavigator.models import ExtractionApiResponse


def test_extraction_api_response_with_usage():
    raw = {
        "status": "success",
        "data": {"mood": "upbeat", "topics": ["a", "b"]},
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        },
    }
    m = _parse_model(ExtractionApiResponse, raw)
    assert m.data["mood"] == "upbeat"
    assert m.usage.total_tokens == 150


def test_extraction_api_response_without_usage():
    raw = {"status": "success", "data": {"key": "value"}}
    m = _parse_model(ExtractionApiResponse, raw)
    assert m.usage is None
