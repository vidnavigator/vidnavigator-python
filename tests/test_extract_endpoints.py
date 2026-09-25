"""Unit tests for extract endpoints (mocked HTTP)."""

from unittest.mock import patch

import pytest

from vidnavigator import VidNavigatorClient

from .helpers import accepted, job


@pytest.fixture
def client():
    return VidNavigatorClient(api_key="test_key")


EXTRACT_USAGE = {
    "charges": [
        {
            "service_type": "analysis_request",
            "quantity": 1,
            "credits": 1,
            "tokens": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            },
        }
    ],
    "total_credits": 1,
}


def _run_extract(client, result, usage=None, **kwargs):
    """Call extract_video_data against a mocked submit + completed poll; return (resp, mock)."""
    responses = [
        accepted("extract_video"),
        job("extract_video", "completed", result=result, usage=usage),
    ]
    with patch.object(client, "_request", side_effect=responses) as req:
        resp = client.extract_video_data(**kwargs)
    return resp, req


def test_extract_video_data_posts_correct_path_and_body(client, no_sleep):
    schema = {
        "topic": {"type": "String", "description": "Main topic"},
    }
    resp, req = _run_extract(
        client,
        {"topic": "demo"},
        usage=EXTRACT_USAGE,
        video_url="https://youtube.com/watch?v=abc",
        schema=schema,
        what_to_extract="Focus on the intro",
        include_usage=True,
    )

    submit, poll = req.call_args_list
    assert submit == (
        ("POST", "/extract/video/async"),
        {
            "json_body": {
                "video_url": "https://youtube.com/watch?v=abc",
                "schema": schema,
                "transcribe": True,
                "what_to_extract": "Focus on the intro",
            }
        },
    )
    # include_usage is not accepted at submit time; it is sent on the poll.
    assert poll == (("GET", "/extract/video/task_1"), {"params": {"include_usage": "true"}})
    assert resp.status == "success"
    assert resp.data == {"topic": "demo"}
    assert resp.usage is not None
    assert resp.usage.total_credits == 1
    assert resp.usage.analysis_tokens.prompt_tokens == 10
    assert resp.usage.analysis_tokens.total_tokens == 15


def test_extract_video_data_can_disable_auto_transcription(client, no_sleep):
    _, req = _run_extract(
        client,
        {},
        video_url="https://example.com/v",
        schema={"x": {"type": "String", "description": "x"}},
        transcribe=False,
    )
    assert req.call_args_list[0][1]["json_body"]["transcribe"] is False


def test_extract_video_data_omits_what_to_extract_when_none(client, no_sleep):
    _, req = _run_extract(
        client,
        {},
        video_url="https://example.com/v",
        schema={"x": {"type": "String", "description": "x"}},
        include_usage=False,
    )
    body = req.call_args_list[0][1]["json_body"]
    assert "what_to_extract" not in body
    assert "include_usage" not in body
    assert req.call_args_list[1][1]["params"] is None


def test_extract_video_data_can_upload_schema_file(client, tmp_path, no_sleep):
    schema_file = tmp_path / "schema.yaml"
    schema_file.write_text("topic:\n  type: String\n  description: Main topic\n")

    resp, req = _run_extract(
        client,
        {"topic": "demo"},
        video_url="https://youtube.com/watch?v=abc",
        schema_file=str(schema_file),
        what_to_extract="Focus on the intro",
        transcribe=False,
        include_usage=True,
    )

    args, kwargs = req.call_args_list[0]
    assert args == ("POST", "/extract/video/async")
    assert kwargs["data"] == {
        "video_url": "https://youtube.com/watch?v=abc",
        "transcribe": "false",
        "what_to_extract": "Focus on the intro",
    }
    filename, _, content_type = kwargs["files"]["schema"]
    assert filename == "schema.yaml"
    assert content_type == "application/yaml"
    assert resp.data == {"topic": "demo"}

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


def test_extract_file_data_can_upload_schema_file(client, tmp_path):
    raw = {"status": "success", "data": {"summary": "hello"}}
    schema_file = tmp_path / "schema.json"
    schema_file.write_text('{"summary": {"type": "String", "description": "Short summary"}}')

    with patch.object(client, "_request", return_value=raw) as req:
        resp = client.extract_file_data(
            file_id="file_123",
            schema_file=str(schema_file),
            include_usage=True,
        )

    args, kwargs = req.call_args
    assert args == ("POST", "/extract/file")
    assert kwargs["data"] == {
        "file_id": "file_123",
        "include_usage": "true",
    }
    filename, _, content_type = kwargs["files"]["schema"]
    assert filename == "schema.json"
    assert content_type == "application/json"
    assert resp.data["summary"] == "hello"
