"""Unit tests for /watch: submit, polling, the blocking call, sync and async clients (mocked HTTP)."""

import asyncio
import json
from unittest.mock import patch

import httpx
import pytest

from vidnavigator import (
    AsyncJob,
    AsyncVidNavigatorClient,
    BadRequestError,
    Job,
    NotFoundError,
    PaymentRequiredError,
    VidNavigatorClient,
    construct_webhook_event,
)
from vidnavigator.models import VideoScene, WatchJobResponse, WatchResponse

from .helpers import accepted, job

BASE = "https://api.test/v1"

SCENES = [
    {"start": 0.0, "end": 4.0, "description": "A presenter stands in front of a world map.",
     "on_screen_text": "BREAKING NEWS"},
    {"start": 4.0, "end": 12.5, "description": "Aerial view of a harbour at dusk.", "on_screen_text": ""},
]
WATCH_RESULT = {
    "video_info": {"title": "Evening news", "duration": 12.5, "url": "https://example.com/v"},
    "transcript": [{"text": "Good evening.", "start": 0.4, "end": 1.6}],
    "scenes": SCENES,
    "frames_analyzed": 9,
}
USAGE = {
    "charges": [
        {"service_type": "standard_request", "quantity": 1.0, "credits": 0.0001},
        {"service_type": "frame_analysis", "quantity": 9.0, "credits": 0.009},
    ],
    "total_credits": 0.0091,
}


@pytest.fixture
def client():
    return VidNavigatorClient(api_key="test_key")


# ---------------------------------------------------------------------------
# Submitting
# ---------------------------------------------------------------------------

def test_submit_watch_video_returns_handle(client):
    with patch.object(client, "_request", return_value=accepted("watch")) as req:
        handle = client.submit_watch_video(video_url="https://example.com/v")
    assert isinstance(handle, Job)
    assert handle.job_type == "watch" and handle.task_id == "task_1"
    assert handle.check_status_url == "/v1/watch/task_1"
    assert repr(handle) == "Job(job_type='watch', task_id='task_1')"
    # `detail` is left to the API's default when it is not given.
    req.assert_called_once_with(
        "POST",
        "/watch/async",
        json_body={
            "video_url": "https://example.com/v",
            "include_transcript": True,
            "transcript_text": False,
        },
    )


def test_submit_watch_video_all_params(client):
    raw = accepted("watch", webhook_url="https://example.com/hook")
    with patch.object(client, "_request", return_value=raw) as req:
        handle = client.submit_watch_video(
            video_url="https://www.tiktok.com/@a/video/1",
            detail="high",
            include_transcript=False,
            transcript_text=True,
            webhook_url="https://example.com/hook",
        )
    assert handle.webhook_url == "https://example.com/hook"
    assert req.call_args[1]["json_body"] == {
        "video_url": "https://www.tiktok.com/@a/video/1",
        "detail": "high",
        "include_transcript": False,
        "transcript_text": True,
        "webhook_url": "https://example.com/hook",
    }


def test_no_max_frames_parameter(client):
    with pytest.raises(TypeError):
        client.submit_watch_video(video_url="https://example.com/v", max_frames=10)


def test_empty_webhook_url_is_passed_through(client):
    with patch.object(client, "_request", return_value=accepted("watch")) as req:
        client.submit_watch_video(video_url="https://example.com/v", webhook_url="")
    assert req.call_args[1]["json_body"]["webhook_url"] == ""


# ---------------------------------------------------------------------------
# Reading the job
# ---------------------------------------------------------------------------

def test_refresh_returns_typed_job(client):
    handle = client.resume_job("watch", "task_1")
    with patch.object(client, "_request", return_value=job("watch", "processing")) as req:
        resp = handle.refresh()
    assert isinstance(resp, WatchJobResponse)
    assert resp.data.is_processing and resp.data.result is None
    assert req.call_args == (("GET", "/watch/task_1"), {"params": None})
    assert handle.last_response is resp


def test_result_scenes_and_transcript_with_usage(client, no_sleep):
    handle = client.resume_job("watch", "task_1")
    responses = [job("watch", "processing"), job("watch", "completed", result=WATCH_RESULT, usage=USAGE)]
    with patch.object(client, "_request", side_effect=responses) as req:
        resp = handle.result(include_usage=True)
    assert isinstance(resp, WatchResponse)
    assert resp.status == "success"
    assert resp.data.video_info.title == "Evening news"
    assert resp.data.frames_analyzed == 9
    assert resp.data.transcript[0].text == "Good evening."
    assert resp.data.transcript_error is None
    scenes = resp.data.scenes
    assert all(isinstance(scene, VideoScene) for scene in scenes)
    assert [(s.start, s.end) for s in scenes] == [(0.0, 4.0), (4.0, 12.5)]
    assert scenes[0].on_screen_text == "BREAKING NEWS" and scenes[1].on_screen_text == ""
    assert resp.usage.charge_for("frame_analysis").quantity == 9.0
    for call in req.call_args_list:
        assert call == (("GET", "/watch/task_1"), {"params": {"include_usage": "true"}})


def test_result_without_speech_keeps_the_scenes(client, no_sleep):
    result = {
        "video_info": {"title": "Silent clip"},
        "transcript": [],
        "transcript_error": {"error": "transcript_not_available", "message": "No transcript found for this video."},
        "scenes": SCENES,
        "frames_analyzed": 4,
    }
    with patch.object(client, "_request", return_value=job("watch", "completed", result=result)):
        resp = client.resume_job("watch", "task_1").result()
    assert resp.data.transcript == []
    assert resp.data.transcript_error.error == "transcript_not_available"
    assert len(resp.data.scenes) == 2


def test_result_scenes_only_and_plain_text(client, no_sleep):
    scenes_only = {"video_info": {"title": "T"}, "scenes": SCENES, "frames_analyzed": 4}
    with patch.object(client, "_request", return_value=job("watch", "completed", result=scenes_only)):
        resp = client.resume_job("watch", "task_1").result()
    assert resp.data.transcript is None  # include_transcript=False: the field is left out

    as_text = {**WATCH_RESULT, "transcript": "Good evening."}
    with patch.object(client, "_request", return_value=job("watch", "completed", result=as_text)):
        resp = client.resume_job("watch", "task_1").result()
    assert resp.data.transcript == "Good evening."


@pytest.mark.parametrize(
    "http_status, code, exc_cls",
    [
        (404, "frames_not_available", NotFoundError),
        (400, "video_too_long", BadRequestError),
        (402, "insufficient_credits", PaymentRequiredError),
    ],
)
def test_failed_job_raises_the_matching_exception(client, no_sleep, http_status, code, exc_cls):
    error = {"error": code, "message": "nope", "http_status": http_status}
    with patch.object(client, "_request", return_value=job("watch", "failed", error=error)):
        with pytest.raises(exc_cls) as exc_info:
            client.resume_job("watch", "task_1").result()
    assert exc_info.value.error_code == code


# ---------------------------------------------------------------------------
# Blocking call and operation object
# ---------------------------------------------------------------------------

def test_watch_video_blocking(client, no_sleep):
    responses = [
        accepted("watch"),
        job("watch", "processing"),
        job("watch", "completed", result=WATCH_RESULT, usage=USAGE),
    ]
    with patch.object(client, "_request", side_effect=responses) as req:
        resp = client.watch_video(video_url="https://example.com/v", detail="low", include_usage=True)
    assert isinstance(resp, WatchResponse)
    assert resp.usage.total_credits == 0.0091
    calls = req.call_args_list
    assert calls[0] == (("POST", "/watch/async"), {"json_body": {
        "video_url": "https://example.com/v", "include_transcript": True, "transcript_text": False,
        "detail": "low",
    }})
    assert calls[1] == calls[2] == (("GET", "/watch/task_1"), {"params": {"include_usage": "true"}})


def test_operation_object(client, no_sleep):
    op = client.watch
    assert op.job_type == "watch" and repr(op) == "Operation(job_type='watch')"
    resumed = op.resume("t9")
    assert isinstance(resumed, Job) and resumed.job_type == "watch" and resumed.task_id == "t9"

    with patch.object(client, "_request", return_value=accepted("watch")) as req:
        handle = op.submit(video_url="https://example.com/v", include_transcript=False)
    assert handle.job_type == "watch"
    assert req.call_args[1]["json_body"]["include_transcript"] is False

    responses = [accepted("watch"), job("watch", "completed", result=WATCH_RESULT)]
    with patch.object(client, "_request", side_effect=responses):
        resp = op(video_url="https://example.com/v")
    assert len(resp.data.scenes) == 2


def test_the_synchronous_endpoint_is_never_called(client, no_sleep):
    responses = [accepted("watch"), job("watch", "completed", result=WATCH_RESULT)]
    with patch.object(client, "_request", side_effect=responses) as req:
        client.watch_video(video_url="https://example.com/v")
    assert ("POST", "/watch") not in [call[0] for call in req.call_args_list]


# ---------------------------------------------------------------------------
# Async client
# ---------------------------------------------------------------------------

class Api:
    """A scripted fake API: queued responses per (method, path), recording every request."""

    def __init__(self):
        self.routes = {}
        self.requests = []

    def on(self, method, path, *responses):
        self.routes.setdefault((method, path), []).extend(responses)
        return self

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        queue = self.routes.get((request.method, request.url.path))
        if not queue:
            return httpx.Response(404, json={"status": "error", "error": "route_not_mocked"})
        item = queue.pop(0) if len(queue) > 1 else queue[0]
        status, payload = item if isinstance(item, tuple) else (200, item)
        return httpx.Response(status, json=payload)


def make_async_client(api):
    http = httpx.AsyncClient(transport=httpx.MockTransport(api))
    return AsyncVidNavigatorClient(api_key="test_key", base_url=BASE, http_client=http)


@pytest.fixture
def instant_sleep():
    real_sleep = asyncio.sleep

    async def fake_sleep(seconds):
        await real_sleep(0)

    with patch("vidnavigator.jobs.asyncio.sleep", fake_sleep):
        yield


def test_async_submit_and_result(instant_sleep):
    api = (Api()
           .on("POST", "/v1/watch/async", (202, accepted("watch", webhook_url="https://h.example")))
           .on("GET", "/v1/watch/task_1",
               job("watch", "processing"),
               job("watch", "completed", result=WATCH_RESULT, usage=USAGE)))

    async def go():
        async with make_async_client(api) as client:
            handle = await client.submit_watch_video(
                video_url="https://example.com/v", detail="high", webhook_url="https://h.example")
            assert isinstance(handle, AsyncJob) and handle.job_type == "watch"
            assert client.watch.resume("t9").job_type == "watch"
            return await handle.result(include_usage=True)

    resp = asyncio.run(go())
    assert isinstance(resp, WatchResponse)
    assert resp.data.scenes[0].on_screen_text == "BREAKING NEWS"
    assert resp.usage.charge_for("frame_analysis").credits == 0.009
    assert json.loads(api.requests[0].content) == {
        "video_url": "https://example.com/v", "include_transcript": True, "transcript_text": False,
        "detail": "high", "webhook_url": "https://h.example",
    }


def test_async_watch_video_blocking(instant_sleep):
    api = (Api()
           .on("POST", "/v1/watch/async", (202, accepted("watch")))
           .on("GET", "/v1/watch/task_1", job("watch", "completed", result=WATCH_RESULT)))

    async def go():
        async with make_async_client(api) as client:
            return await client.watch(video_url="https://example.com/v", include_transcript=False)

    resp = asyncio.run(go())
    assert isinstance(resp, WatchResponse) and resp.data.frames_analyzed == 9
    assert json.loads(api.requests[0].content)["include_transcript"] is False


# ---------------------------------------------------------------------------
# Webhook event
# ---------------------------------------------------------------------------

def test_watch_webhook_event_is_parsed():
    import hashlib
    import hmac
    import time

    secret = "whsec_test"
    payload = json.dumps({
        "id": "evt_1", "type": "watch.completed", "created_at": "2026-11-15T10:00:00Z", "api_version": "1.0.0",
        "data": {"task_id": "task_1", "task_status": "completed", "job_type": "watch",
                 "check_status_url": "/v1/watch/task_1", "result": WATCH_RESULT},
    })
    timestamp = str(int(time.time()))
    signature = hmac.new(secret.encode(), f"{timestamp}.{payload}".encode(), hashlib.sha256).hexdigest()
    event = construct_webhook_event(payload, f"t={timestamp},v1={signature}", secret)
    assert event.type == "watch.completed"
    assert event.data.job_type == "watch"
    assert event.data.result["scenes"][0]["on_screen_text"] == "BREAKING NEWS"
