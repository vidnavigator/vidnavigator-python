"""Unit tests for extract endpoints (mocked HTTP)."""

from unittest.mock import patch

import pytest

from vidnavigator import VidNavigatorClient


@pytest.fixture
def client():
    return VidNavigatorClient(api_key="test_key")


def test_extract_video_data_posts_correct_path_and_body(client):
    raw = {
        "status": "success",
        "data": {"topic": "demo"},
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }
    schema = {
        "topic": {"type": "String", "description": "Main topic"},
    }
    with patch.object(client, "_request", return_value=raw) as req:
        resp = client.extract_video_data(
            video_url="https://youtube.com/watch?v=abc",
            schema=schema,
            what_to_extract="Focus on the intro",
            include_usage=True,
        )

    req.assert_called_once_with(
        "POST",
        "/extract/video",
        json_body={
            "video_url": "https://youtube.com/watch?v=abc",
            "schema": schema,
            "transcribe": True,
            "include_usage": True,
            "what_to_extract": "Focus on the intro",
        },
    )
    assert resp.status == "success"
    assert resp.data == {"topic": "demo"}
    assert resp.usage is not None
    assert resp.usage.prompt_tokens == 10
    assert resp.usage.total_tokens == 15


def test_extract_video_data_can_disable_auto_transcription(client):
    raw = {"status": "success", "data": {}}
    with patch.object(client, "_request", return_value=raw) as req:
        client.extract_video_data(
            video_url="https://example.com/v",
            schema={"x": {"type": "String", "description": "x"}},
            transcribe=False,
        )
    _, called_kwargs = req.call_args
    assert called_kwargs["json_body"]["transcribe"] is False


def test_extract_video_data_omits_what_to_extract_when_none(client):
    raw = {"status": "success", "data": {}}
    with patch.object(client, "_request", return_value=raw) as req:
        client.extract_video_data(
            video_url="https://example.com/v",
            schema={"x": {"type": "String", "description": "x"}},
            include_usage=False,
        )
    _, called_kwargs = req.call_args
    assert "what_to_extract" not in called_kwargs["json_body"]


def test_extract_file_data_posts_correct_path_and_body(client):
    raw = {"status": "success", "data": {"summary": "hello"}}
    schema = {"summary": {"type": "String", "description": "Short summary"}}
    with patch.object(client, "_request", return_value=raw) as req:
        resp = client.extract_file_data(
            file_id="file_123",
            schema=schema,
            include_usage=False,
        )

    req.assert_called_once_with(
        "POST",
        "/extract/file",
        json_body={
            "file_id": "file_123",
            "schema": schema,
            "include_usage": False,
        },
    )
    assert resp.status == "success"
    assert resp.data["summary"] == "hello"
    assert resp.usage is None
