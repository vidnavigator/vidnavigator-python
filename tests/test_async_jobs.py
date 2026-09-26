"""Unit tests for background jobs: submit handles, polling, blocking calls (mocked HTTP)."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from vidnavigator import (
    Job,
    JobTimeoutError,
    BadRequestError,
    PaymentRequiredError,
    RateLimitExceeded,
    ServerError,
    TooManyActiveJobsError,
    VidNavigatorClient,
    VidNavigatorError,
)
from vidnavigator.models import (
    ExtractionApiResponse,
    ExtractVideoJobResponse,
    TranscribeAllVideosResponse,
    TranscribeJobResponse,
    TranscriptResponse,
    TweetStatementResponse,
)

from .helpers import accepted, job


@pytest.fixture
def client():
    return VidNavigatorClient(api_key="test_key")


class FakeClock:
    """Deterministic monotonic clock that advances only when ``sleep`` is called."""

    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


@pytest.fixture
def clock():
    fake = FakeClock()
    with patch("vidnavigator.jobs.time.monotonic", fake.monotonic), \
            patch("vidnavigator.jobs.time.sleep", fake.sleep):
        yield fake


USAGE = {
    "charges": [
        {"service_type": "residential_request", "quantity": 1.0, "credits": 0.005},
        {"service_type": "transcription_hour", "quantity": 0.5, "credits": 0.5},
    ],
    "total_credits": 0.505,
}

TRANSCRIPT_RESULT = {
    "video_info": {"title": "Long podcast", "duration": 3600},
    "transcript": [{"text": "hello", "start": 0.0, "end": 1.5}],
}

CAROUSEL_RESULT = {
    "carousel_info": {"total_items": 3, "video_count": 2, "image_count": 1},
    "videos": [
        {"index": 1, "status": "success", "video_info": {"title": "V1"}, "transcript": "a"},
        {"index": 2, "status": "error", "error": "no_audio", "message": "No audio"},
    ],
}

TWEET_RESULT = {
    "final_statement": "The author claims X.",
    "detailed_analysis": "Analysis.",
    "topics": ["t1"],
    "claim_type": "factual_claim",
    "tweet_media_summary": "A long video about X.",
}

SCHEMA = {"mood": {"type": "String", "description": "One word mood"}}


# ---------------------------------------------------------------------------
# Submitting returns a handle
# ---------------------------------------------------------------------------

def test_submit_transcribe_video_returns_handle(client):
    with patch.object(client, "_request", return_value=accepted("transcribe")) as req:
        handle = client.submit_transcribe_video(video_url="https://example.com/v")
    assert isinstance(handle, Job)
    assert handle.task_id == "task_1"
    assert handle.job_type == "transcribe"
    assert handle.check_status_url == "/v1/transcribe/task_1"
    assert handle.webhook_url is None
    assert handle.data.docs_url.endswith("async-jobs")
    assert repr(handle) == "Job(job_type='transcribe', task_id='task_1')"
    req.assert_called_once_with(
        "POST",
        "/transcribe/async",
        json_body={
            "video_url": "https://example.com/v",
            "transcript_text": False,
            "all_videos": False,
        },
    )


def test_submit_transcribe_video_all_params(client):
    raw = accepted("transcribe", webhook_url="https://example.com/hook")
    with patch.object(client, "_request", return_value=raw) as req:
        handle = client.submit_transcribe_video(
            video_url="https://instagram.com/p/abc",
            transcript_text=True,
            all_videos=True,
            webhook_url="https://example.com/hook",
        )
    assert handle.webhook_url == "https://example.com/hook"
    assert req.call_args[1]["json_body"] == {
        "video_url": "https://instagram.com/p/abc",
        "transcript_text": True,
        "all_videos": True,
        "webhook_url": "https://example.com/hook",
    }


def test_empty_webhook_url_is_passed_through(client):
    with patch.object(client, "_request", return_value=accepted("transcribe")) as req:
        client.submit_transcribe_video(video_url="https://example.com/v", webhook_url="")
    assert req.call_args[1]["json_body"]["webhook_url"] == ""


def test_submit_without_task_id_raises(client):
    raw = {"status": "success", "data": {"task_status": "processing"}}
    with patch.object(client, "_request", return_value=raw):
        with pytest.raises(VidNavigatorError, match="task_id"):
            client.submit_transcribe_video(video_url="https://example.com/v")


def test_submit_extract_video_data_json(client):
    with patch.object(client, "_request", return_value=accepted("extract_video")) as req:
        handle = client.submit_extract_video_data(
            video_url="https://example.com/v",
            schema=SCHEMA,
            what_to_extract="Mood only",
            transcribe=False,
            webhook_url="https://example.com/hook",
        )
    assert handle.job_type == "extract_video"
    req.assert_called_once_with(
        "POST",
        "/extract/video/async",
        json_body={
            "video_url": "https://example.com/v",
            "schema": SCHEMA,
            "what_to_extract": "Mood only",
            "transcribe": False,
            "webhook_url": "https://example.com/hook",
        },
    )


def test_submit_extract_video_data_schema_file(client, tmp_path):
    schema_file = tmp_path / "schema.yml"
    schema_file.write_text("mood:\n  type: String\n  description: One word mood\n")
    with patch.object(client, "_request", return_value=accepted("extract_video")) as req:
        client.submit_extract_video_data(
            video_url="https://example.com/v",
            schema_file=str(schema_file),
            webhook_url="",
        )
    args, kwargs = req.call_args
    assert args == ("POST", "/extract/video/async")
    assert kwargs["data"] == {
        "video_url": "https://example.com/v",
        "transcribe": "true",
        "webhook_url": "",
    }
    filename, _, content_type = kwargs["files"]["schema"]
    assert filename == "schema.yml"
    assert content_type == "application/yaml"


@pytest.mark.parametrize(
    "kwargs",
    [{}, {"schema": SCHEMA, "schema_file": "schema.json"}],
    ids=["neither", "both"],
)
def test_extract_requires_exactly_one_schema(client, kwargs):
    with patch.object(client, "_request") as req:
        with pytest.raises(ValueError):
            client.extract_video_data(video_url="https://example.com/v", **kwargs)
    req.assert_not_called()


def test_extract_missing_schema_file(client, tmp_path):
    with pytest.raises(FileNotFoundError):
        client.submit_extract_video_data(
            video_url="https://example.com/v",
            schema_file=str(tmp_path / "missing.json"),
        )


def test_submit_tweet_statement(client):
    with patch.object(client, "_request", return_value=accepted("tweet_statement")) as req:
        handle = client.submit_tweet_statement(tweet_id="123", webhook_url="https://example.com/h")
    assert handle.job_type == "tweet_statement"
    req.assert_called_once_with(
        "POST",
        "/tweet/statement/async",
        json_body={"tweet_id": "123", "webhook_url": "https://example.com/h"},
    )


# ---------------------------------------------------------------------------
# Submit-time errors are typed
# ---------------------------------------------------------------------------

def _http_error(status_code, body):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.ok = False
    resp.reason = "Mocked"
    resp.json.return_value = body
    return resp


def test_submit_402_raises_payment_required(client):
    body = {"status": "error", "error": "limit_exceeded", "error_code": "limit_exceeded",
            "message": "Less than 60 seconds of transcription credit remaining"}
    with patch.object(client.session, "request", return_value=_http_error(402, body)) as req:
        with pytest.raises(PaymentRequiredError) as exc_info:
            client.transcribe_video(video_url="https://example.com/v")
    assert exc_info.value.status_code == 402
    assert exc_info.value.error_code == "limit_exceeded"
    req.assert_called_once()  # no polling when no task was created


def test_submit_429_raises_too_many_active_jobs(client):
    body = {"status": "error", "error": "too_many_active_jobs", "message": "Too many jobs"}
    with patch.object(client.session, "request", return_value=_http_error(429, body)):
        with pytest.raises(TooManyActiveJobsError) as exc_info:
            client.submit_extract_video_data(video_url="https://example.com/v", schema=SCHEMA)
    assert isinstance(exc_info.value, RateLimitExceeded)
    assert exc_info.value.status_code == 429


# ---------------------------------------------------------------------------
# Handle: status / done / refresh
# ---------------------------------------------------------------------------

def test_status_and_done_poll_once_each(client):
    handle = client.resume_job("transcribe", "task_1")
    responses = [job("transcribe", "processing"), job("transcribe", "completed", result=TRANSCRIPT_RESULT)]
    with patch.object(client, "_request", side_effect=responses) as req:
        assert handle.status() == "processing"
        assert handle.done() is True
    assert req.call_count == 2
    req.assert_called_with("GET", "/transcribe/task_1", params=None)
    assert isinstance(handle.last_response, TranscribeJobResponse)
    assert handle.last_response.data.is_completed


def test_refresh_with_usage(client):
    handle = client.resume_job("extract_video", "task_1")
    raw = job("extract_video", "completed", result={"mood": "cheerful"}, usage=USAGE)
    with patch.object(client, "_request", return_value=raw) as req:
        resp = handle.refresh(include_usage=True)
    assert isinstance(resp, ExtractVideoJobResponse)
    assert resp.data.result == {"mood": "cheerful"}
    assert resp.usage.total_credits == 0.505
    req.assert_called_once_with("GET", "/extract/video/task_1", params={"include_usage": "true"})


def test_resume_job_validation(client):
    with pytest.raises(ValueError, match="job_type"):
        client.resume_job("transcript", "task_1")
    with pytest.raises(ValueError, match="task_id"):
        client.resume_job("transcribe", "")
    handle = client.resume_job("tweet_statement", "abc")
    assert handle.data is None and handle.check_status_url is None


def test_webhook_status_is_parsed(client):
    webhook = {"status": "failed", "attempts": 5, "response_status": 500,
               "last_error": "HTTP 500", "delivered_at": None}
    raw = job("transcribe", "completed", result=TRANSCRIPT_RESULT, webhook=webhook)
    with patch.object(client, "_request", return_value=raw):
        resp = client.resume_job("transcribe", "task_1").refresh()
    assert resp.data.webhook.status == "failed"
    assert resp.data.webhook.attempts == 5


# ---------------------------------------------------------------------------
# Handle: result()
# ---------------------------------------------------------------------------

def test_result_transcript_segments_with_usage(client, clock):
    handle = client.resume_job("transcribe", "task_1")
    responses = [
        job("transcribe", "processing"),
        job("transcribe", "completed", result=TRANSCRIPT_RESULT, usage=USAGE),
    ]
    with patch.object(client, "_request", side_effect=responses) as req:
        resp = handle.result(include_usage=True)
    assert isinstance(resp, TranscriptResponse)
    assert resp.status == "success"
    assert resp.data.video_info.title == "Long podcast"
    assert resp.data.transcript[0].text == "hello"
    assert resp.usage.charge_for("transcription_hour").quantity == 0.5
    for call in req.call_args_list:
        assert call == (("GET", "/transcribe/task_1"), {"params": {"include_usage": "true"}})


def test_result_transcript_plain_text(client, no_sleep):
    raw = job("transcribe", "completed", result={"video_info": {"title": "T"}, "transcript": "full"})
    with patch.object(client, "_request", return_value=raw):
        resp = client.resume_job("transcribe", "task_1").result()
    assert resp.data.transcript == "full"
    no_sleep.assert_not_called()  # already finished on the first poll


def test_result_carousel(client, no_sleep):
    with patch.object(client, "_request", return_value=job("transcribe", "completed", result=CAROUSEL_RESULT)):
        resp = client.resume_job("transcribe", "task_1").result()
    assert isinstance(resp, TranscribeAllVideosResponse)
    assert resp.data.carousel_info.video_count == 2
    assert resp.data.videos[1].error == "no_audio"


def test_result_extract(client, no_sleep):
    with patch.object(client, "_request", return_value=job("extract_video", "completed", result={"mood": "x"})):
        resp = client.resume_job("extract_video", "task_1").result()
    assert isinstance(resp, ExtractionApiResponse)
    assert resp.data == {"mood": "x"}
    assert resp.video_info is None


def test_result_tweet(client, no_sleep):
    raw = job("tweet_statement", "completed", result=TWEET_RESULT, usage=USAGE)
    with patch.object(client, "_request", return_value=raw):
        resp = client.resume_job("tweet_statement", "task_1").result(include_usage=True)
    assert isinstance(resp, TweetStatementResponse)
    assert resp.data.final_statement == "The author claims X."
    assert resp.usage.total_credits == 0.505


def test_result_completed_without_result_raises(client, no_sleep):
    with patch.object(client, "_request", return_value=job("transcribe", "completed")):
        with pytest.raises(VidNavigatorError, match="without a result"):
            client.resume_job("transcribe", "task_1").result()


# ---------------------------------------------------------------------------
# Failures are read from the `error` object
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "http_status,code,exc_cls",
    [
        (400, "unsupported_platform", BadRequestError),
        (402, "limit_exceeded", PaymentRequiredError),
        (500, "audio_extraction_failed", ServerError),
        (502, "tweet_fetch_failed", ServerError),
    ],
)
def test_failed_job_raises_exception_from_error_object(client, no_sleep, http_status, code, exc_cls):
    error = {"error": code, "message": f"{code} happened", "http_status": http_status}
    with patch.object(client, "_request", return_value=job("transcribe", "failed", error=error)):
        with pytest.raises(exc_cls) as exc_info:
            client.resume_job("transcribe", "task_1").result()
    exc = exc_info.value
    assert exc.error_code == code
    assert exc.status_code == http_status
    assert str(exc) == f"{code} happened"


def test_failed_job_ignores_deprecated_error_message(client, no_sleep):
    raw = job("transcribe", "failed")
    raw["data"]["error_message"] = "legacy text"
    with patch.object(client, "_request", return_value=raw):
        with pytest.raises(VidNavigatorError) as exc_info:
            client.resume_job("transcribe", "task_1").result()
    assert "legacy text" not in str(exc_info.value)
    assert "without error details" in str(exc_info.value)


def test_wait_can_return_failed_job(client, no_sleep):
    error = {"error": "limit_exceeded", "message": "No credits", "http_status": 402}
    with patch.object(client, "_request", return_value=job("transcribe", "failed", error=error)):
        resp = client.resume_job("transcribe", "task_1").wait(raise_on_failure=False)
    assert resp.data.is_failed
    assert resp.data.error.http_status == 402


# ---------------------------------------------------------------------------
# Wait loop: terminal states, schedule, timeout
# ---------------------------------------------------------------------------

def test_wait_keeps_polling_unknown_non_terminal_status(client, clock):
    responses = [
        job("transcribe", "queued"),
        job("transcribe", "processing"),
        job("transcribe", "downloading"),
        job("transcribe", "completed", result=TRANSCRIPT_RESULT),
    ]
    with patch.object(client, "_request", side_effect=responses) as req:
        resp = client.resume_job("transcribe", "task_1").wait()
    assert resp.data.is_completed
    assert req.call_count == 4


def test_poll_schedule_fast_start_then_three_seconds(client, clock):
    responses = [job("transcribe", "processing")] * 15 + [
        job("transcribe", "completed", result=TRANSCRIPT_RESULT)
    ]
    with patch.object(client, "_request", side_effect=responses):
        client.resume_job("transcribe", "task_1").wait()
    # 1s polls until 10s have elapsed, then every 3s.
    assert clock.sleeps == [1.0] * 10 + [3.0] * 5


def test_poll_schedule_without_fast_start(client, clock):
    responses = [job("transcribe", "processing")] * 3 + [
        job("transcribe", "completed", result=TRANSCRIPT_RESULT)
    ]
    with patch.object(client, "_request", side_effect=responses):
        client.resume_job("transcribe", "task_1").wait(fast_start=False)
    assert clock.sleeps == [3.0, 3.0, 3.0]


def test_poll_interval_is_configurable(client, clock):
    responses = [job("transcribe", "processing")] * 2 + [
        job("transcribe", "completed", result=TRANSCRIPT_RESULT)
    ]
    with patch.object(client, "_request", side_effect=responses):
        client.resume_job("transcribe", "task_1").wait(poll_interval=0.5)
    assert clock.sleeps == [0.5, 0.5]


def test_timeout_error_carries_task_id_and_resumable_handle(client, clock):
    with patch.object(client, "_request", side_effect=[accepted("transcribe", task_id="t-42")] +
                      [job("transcribe", "processing", task_id="t-42")] * 50):
        with pytest.raises(JobTimeoutError) as exc_info:
            client.transcribe_video(video_url="https://example.com/v", timeout=12)
    exc = exc_info.value
    assert exc.task_id == "t-42"
    assert "t-42" in str(exc)
    assert isinstance(exc.job, Job) and exc.job.task_id == "t-42"
    # Sleeps never overshoot the deadline.
    assert sum(clock.sleeps) == pytest.approx(12)

    # The handle on the error resumes waiting on the same job.
    with patch.object(client, "_request",
                      return_value=job("transcribe", "completed", result=TRANSCRIPT_RESULT, task_id="t-42")) as req:
        resp = exc.job.result()
    assert resp.data.video_info.title == "Long podcast"
    req.assert_called_with("GET", "/transcribe/t-42", params=None)


def test_timeout_none_waits_until_finished(client, clock):
    responses = [job("transcribe", "processing")] * 40 + [
        job("transcribe", "completed", result=TRANSCRIPT_RESULT)
    ]
    with patch.object(client, "_request", side_effect=responses):
        client.resume_job("transcribe", "task_1").wait(timeout=None)
    assert sum(clock.sleeps) > 60


# ---------------------------------------------------------------------------
# Blocking one-liners
# ---------------------------------------------------------------------------

def test_transcribe_video_blocking(client, no_sleep):
    responses = [
        accepted("transcribe"),
        job("transcribe", "processing"),
        job("transcribe", "completed", result=TRANSCRIPT_RESULT, usage=USAGE),
    ]
    with patch.object(client, "_request", side_effect=responses) as req:
        resp = client.transcribe_video(
            video_url="https://example.com/v", transcript_text=True, include_usage=True,
        )
    assert isinstance(resp, TranscriptResponse)
    assert resp.usage.total_credits == 0.505
    calls = req.call_args_list
    assert calls[0] == (("POST", "/transcribe/async"), {"json_body": {
        "video_url": "https://example.com/v", "transcript_text": True, "all_videos": False,
    }})
    assert calls[1] == calls[2] == (("GET", "/transcribe/task_1"), {"params": {"include_usage": "true"}})


def test_transcribe_video_all_videos_blocking(client, no_sleep):
    responses = [accepted("transcribe"), job("transcribe", "completed", result=CAROUSEL_RESULT)]
    with patch.object(client, "_request", side_effect=responses):
        resp = client.transcribe_video(video_url="https://instagram.com/p/x", all_videos=True)
    assert isinstance(resp, TranscribeAllVideosResponse)


def test_extract_video_data_blocking(client, no_sleep):
    responses = [accepted("extract_video"), job("extract_video", "completed", result={"mood": "calm"})]
    with patch.object(client, "_request", side_effect=responses) as req:
        resp = client.extract_video_data(
            video_url="https://example.com/v", schema=SCHEMA, include_usage=True,
        )
    assert resp.data == {"mood": "calm"}
    post, get = req.call_args_list
    assert post[0] == ("POST", "/extract/video/async")
    assert "include_usage" not in post[1]["json_body"]
    assert get == (("GET", "/extract/video/task_1"), {"params": {"include_usage": "true"}})


def test_get_tweet_statement_blocking(client, no_sleep):
    responses = [accepted("tweet_statement"), job("tweet_statement", "completed", result=TWEET_RESULT)]
    with patch.object(client, "_request", side_effect=responses) as req:
        resp = client.get_tweet_statement(tweet_id="123")
    assert resp.data.claim_type == "factual_claim"
    assert req.call_args_list[0] == (("POST", "/tweet/statement/async"), {"json_body": {"tweet_id": "123"}})


def test_blocking_failure_raises(client, no_sleep):
    error = {"error": "tweet_fetch_failed", "message": "Could not fetch tweet", "http_status": 502}
    responses = [accepted("tweet_statement"), job("tweet_statement", "failed", error=error)]
    with patch.object(client, "_request", side_effect=responses):
        with pytest.raises(ServerError, match="Could not fetch tweet"):
            client.get_tweet_statement(tweet_id="123")


def test_many_jobs_in_parallel(client, no_sleep):
    """Submit several jobs, then collect them: the non-blocking shape."""
    submits = [accepted("transcribe", task_id=f"t{i}") for i in range(3)]
    with patch.object(client, "_request", side_effect=submits):
        handles = [client.submit_transcribe_video(video_url=f"https://example.com/{i}") for i in range(3)]
    assert [h.task_id for h in handles] == ["t0", "t1", "t2"]

    def poll(method, path, params=None):
        task_id = path.rsplit("/", 1)[1]
        result = {"video_info": {"title": task_id}, "transcript": task_id}
        return job("transcribe", "completed", result=result, task_id=task_id)

    with patch.object(client, "_request", side_effect=poll):
        titles = [h.result().data.video_info.title for h in handles]
    assert titles == ["t0", "t1", "t2"]


# ---------------------------------------------------------------------------
# Guard: the synchronous speech-to-text endpoints are never called
# ---------------------------------------------------------------------------

SYNC_ONLY_PATHS = {"/transcribe", "/extract/video", "/tweet/statement"}


def test_no_method_calls_synchronous_speech_to_text_endpoints(client, no_sleep, tmp_path):
    seen = []

    def fake_request(method, url, **kwargs):
        path = url[len(client.base_url):]
        seen.append((method, path))
        resp = MagicMock(spec=requests.Response)
        resp.ok = True
        resp.status_code = 200
        if method == "POST":
            job_type = {"/transcribe/async": "transcribe", "/extract/video/async": "extract_video",
                        "/tweet/statement/async": "tweet_statement"}[path]
            resp.json.return_value = accepted(job_type)
        else:
            job_type = {"/transcribe/task_1": "transcribe", "/extract/video/task_1": "extract_video",
                        "/tweet/statement/task_1": "tweet_statement"}[path]
            result = {"transcribe": TRANSCRIPT_RESULT, "extract_video": {"a": 1},
                      "tweet_statement": TWEET_RESULT}[job_type]
            resp.json.return_value = job(job_type, "completed", result=result)
        return resp

    schema_file = tmp_path / "s.json"
    schema_file.write_text('{"a": {"type": "Integer", "description": "a"}}')
    with patch.object(client.session, "request", side_effect=fake_request):
        client.transcribe_video(video_url="https://example.com/v")
        client.transcribe_video(video_url="https://example.com/v", all_videos=True)
        client.extract_video_data(video_url="https://example.com/v", schema={"a": {}})
        client.extract_video_data(video_url="https://example.com/v", schema_file=str(schema_file))
        client.get_tweet_statement(tweet_id="1")

    posted = {path for method, path in seen if method == "POST"}
    assert posted == {"/transcribe/async", "/extract/video/async", "/tweet/statement/async"}
    assert not posted & SYNC_ONLY_PATHS
