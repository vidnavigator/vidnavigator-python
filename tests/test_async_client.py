"""Unit tests for AsyncVidNavigatorClient and AsyncJob (httpx MockTransport, no network)."""

import asyncio
import inspect
import json
from unittest.mock import patch

import httpx
import pytest

import vidnavigator.async_client as async_client_module
from vidnavigator import (
    AsyncJob,
    AsyncVidNavigatorClient,
    AuthenticationError,
    BadRequestError,
    JobTimeoutError,
    NotFoundError,
    PaymentRequiredError,
    ServerError,
    SystemOverloadError,
    TooManyActiveJobsError,
    VidNavigatorClient,
    VidNavigatorError,
)
from vidnavigator.client import USER_AGENT
from vidnavigator.models import (
    ExtractionApiResponse,
    TikTokSearchResponse,
    TranscribeAllVideosResponse,
    TranscriptResponse,
    TweetStatementResponse,
)

from .helpers import accepted, job, tiktok_task

BASE = "https://api.test/v1"

TRANSCRIPT_RESULT = {
    "video_info": {"title": "Long podcast", "duration": 3600},
    "transcript": [{"text": "hello", "start": 0.0, "end": 1.5}],
}
USAGE = {
    "charges": [{"service_type": "transcription_hour", "quantity": 0.5, "credits": 0.5}],
    "total_credits": 0.5,
}
SCHEMA = {"mood": {"type": "String", "description": "One word mood"}}


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
        if isinstance(item, Exception):
            raise item
        if isinstance(item, httpx.Response):
            return item
        status, body = item if isinstance(item, tuple) else (200, item)
        return httpx.Response(status, json=body)

    def calls(self, method=None, path=None):
        return [r for r in self.requests
                if (method is None or r.method == method) and (path is None or r.url.path == path)]


def make_client(api, **kwargs):
    http = httpx.AsyncClient(transport=httpx.MockTransport(api))
    return AsyncVidNavigatorClient(api_key="test_key", base_url=BASE, http_client=http, **kwargs)


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def instant_sleep():
    """Make AsyncJob polling instant while recording the requested delays."""
    delays = []
    real_sleep = asyncio.sleep

    async def fake_sleep(seconds):
        delays.append(seconds)
        await real_sleep(0)  # still yield to the event loop, like a real sleep

    with patch("vidnavigator.jobs.asyncio.sleep", fake_sleep):
        yield delays


def body(request):
    return json.loads(request.content)


# ---------------------------------------------------------------------------
# Parity with the sync client
# ---------------------------------------------------------------------------

SYNC_ONLY = {"get_youtube_transcript", "search_videos", "close"}


def _public_methods(cls):
    return {name for name, member in inspect.getmembers(cls, inspect.isfunction)
            if not name.startswith("_")}


def test_async_client_mirrors_every_sync_method():
    sync = _public_methods(VidNavigatorClient) - SYNC_ONLY
    missing = sync - _public_methods(AsyncVidNavigatorClient)
    assert not missing, f"AsyncVidNavigatorClient is missing: {sorted(missing)}"


@pytest.mark.parametrize("name", sorted(_public_methods(VidNavigatorClient) - SYNC_ONLY))
def test_async_methods_share_sync_signatures(name):
    sync_sig = inspect.signature(getattr(VidNavigatorClient, name))
    async_method = getattr(AsyncVidNavigatorClient, name)
    assert inspect.signature(async_method).parameters.keys() == sync_sig.parameters.keys()
    for param, sync_param in sync_sig.parameters.items():
        assert inspect.signature(async_method).parameters[param].default == sync_param.default, param
    if name != "resume_job":
        assert inspect.iscoroutinefunction(async_method), f"{name} should be async"


def test_async_job_mirrors_job():
    from vidnavigator import Job

    for name in ("refresh", "status", "done", "wait", "result"):
        assert inspect.iscoroutinefunction(getattr(AsyncJob, name)), name
        assert (inspect.signature(getattr(AsyncJob, name)).parameters.keys()
                == inspect.signature(getattr(Job, name)).parameters.keys())


# ---------------------------------------------------------------------------
# Construction and transport
# ---------------------------------------------------------------------------

def test_requires_api_key(monkeypatch):
    monkeypatch.delenv("VIDNAVIGATOR_API_KEY", raising=False)
    with pytest.raises(AuthenticationError):
        AsyncVidNavigatorClient()


def test_reads_api_key_from_env(monkeypatch):
    monkeypatch.setenv("VIDNAVIGATOR_API_KEY", "env_key")
    api = Api().on("GET", "/v1/health", {"status": "success"})

    async def go():
        http = httpx.AsyncClient(transport=httpx.MockTransport(api))
        client = AsyncVidNavigatorClient(base_url=BASE, http_client=http)
        await client.health_check()
        await http.aclose()

    run(go())
    assert api.requests[0].headers["X-API-Key"] == "env_key"


def test_missing_httpx_has_helpful_error(monkeypatch):
    monkeypatch.setattr(async_client_module, "httpx", None)
    with pytest.raises(ImportError, match=r"vidnavigator\[async\]"):
        AsyncVidNavigatorClient(api_key="k")


def test_sends_auth_headers_and_base_url():
    api = Api().on("GET", "/v1/health", {"status": "success", "version": "1.0.0"})

    async def go():
        async with make_client(api) as client:
            return await client.health_check()

    resp = run(go())
    assert resp.version == "1.0.0"
    request = api.requests[0]
    assert str(request.url) == f"{BASE}/health"
    assert request.headers["X-API-Key"] == "test_key"
    assert request.headers["User-Agent"] == USER_AGENT
    assert request.headers["Accept"] == "application/json"


def test_aclose_closes_owned_client_only():
    async def go():
        owned = AsyncVidNavigatorClient(api_key="k")
        await owned.aclose()
        passed = httpx.AsyncClient()
        client = AsyncVidNavigatorClient(api_key="k", http_client=passed)
        await client.aclose()
        closed_passed = passed.is_closed
        await passed.aclose()
        return owned.http_client.is_closed, closed_passed

    owned_closed, passed_closed = run(go())
    assert owned_closed is True
    assert passed_closed is False


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "status,body_,exc_cls,code",
    [
        (400, {"error": "invalid_schema", "message": "bad"}, BadRequestError, "invalid_schema"),
        (401, {"error": "Invalid API key format", "message": "bad key"}, AuthenticationError, None),
        (402, {"error": "limit_exceeded", "error_code": "limit_exceeded", "message": "no"}, PaymentRequiredError, "limit_exceeded"),
        (404, {"error": "task_not_found", "message": "gone"}, NotFoundError, "task_not_found"),
        (429, {"error": "too_many_active_jobs", "message": "slow"}, TooManyActiveJobsError, "too_many_active_jobs"),
        (500, {"error": "boom", "message": "boom"}, ServerError, "boom"),
    ],
)
def test_error_mapping(status, body_, exc_cls, code):
    api = Api().on("GET", "/v1/usage", (status, {"status": "error", **body_}))

    async def go():
        async with make_client(api) as client:
            await client.get_usage()

    with pytest.raises(exc_cls) as exc_info:
        run(go())
    assert exc_info.value.status_code == status
    if code:
        assert exc_info.value.error_code == code


def test_503_retry_after():
    api = Api().on("GET", "/v1/usage", (503, {"status": "error", "message": "busy", "retry_after_seconds": 7}))

    async def go():
        async with make_client(api) as client:
            await client.get_usage()

    with pytest.raises(SystemOverloadError) as exc_info:
        run(go())
    assert exc_info.value.retry_after_seconds == 7


def test_non_json_error_body():
    api = Api().on("GET", "/v1/usage", httpx.Response(502, text="<html>Bad gateway</html>"))

    async def go():
        async with make_client(api) as client:
            await client.get_usage()

    with pytest.raises(ServerError, match="Bad gateway"):
        run(go())


def test_network_error_is_wrapped():
    api = Api().on("GET", "/v1/usage", httpx.ConnectError("connection refused"))

    async def go():
        async with make_client(api) as client:
            await client.get_usage()

    with pytest.raises(VidNavigatorError, match="Request failed"):
        run(go())


# ---------------------------------------------------------------------------
# Plain endpoints
# ---------------------------------------------------------------------------

def test_get_transcript_body_and_parse():
    api = Api().on("POST", "/v1/transcript", {"status": "success", "data": TRANSCRIPT_RESULT})

    async def go():
        async with make_client(api) as client:
            return await client.get_transcript(video_url="https://youtu.be/x", language="fr", transcript_text=True)

    resp = run(go())
    assert isinstance(resp, TranscriptResponse)
    assert body(api.requests[0]) == {
        "video_url": "https://youtu.be/x",
        "metadata_only": False,
        "fallback_to_metadata": False,
        "transcript_text": True,
        "include_usage": False,
        "language": "fr",
    }


def test_get_files_query_params():
    raw = {"status": "success", "data": {"files": [], "total_count": 0, "limit": 5, "offset": 10, "has_more": False}}
    api = Api().on("GET", "/v1/files", raw)

    async def go():
        async with make_client(api) as client:
            return await client.get_files(limit=5, offset=10, namespace_id="ns1")

    run(go())
    assert dict(api.requests[0].url.params) == {"limit": "5", "offset": "10", "namespace_id": "ns1"}


def test_extract_file_data_schema_file_multipart(tmp_path):
    schema_file = tmp_path / "schema.yaml"
    schema_file.write_text("summary:\n  type: String\n  description: Summary\n")
    api = Api().on("POST", "/v1/extract/file", {"status": "success", "data": {"summary": "hi"}})

    async def go():
        async with make_client(api) as client:
            return await client.extract_file_data(file_id="f1", schema_file=str(schema_file), include_usage=True)

    resp = run(go())
    assert resp.data == {"summary": "hi"}
    request = api.requests[0]
    assert request.headers["Content-Type"].startswith("multipart/form-data")
    content = request.content.decode()
    assert 'name="file_id"' in content and "f1" in content
    assert 'name="include_usage"' in content and "true" in content
    assert 'filename="schema.yaml"' in content
    assert "Content-Type: application/yaml" in content


def test_upload_file_multipart(tmp_path):
    media = tmp_path / "clip.mp3"
    media.write_bytes(b"ID3fakeaudio")
    api = Api().on("POST", "/v1/upload/file", (201, {"status": "success", "file_id": "f9"}))

    async def go():
        async with make_client(api) as client:
            return await client.upload_file(str(media), namespace_ids=["ns1"])

    resp = run(go())
    assert resp["file_id"] == "f9"
    content = api.requests[0].content
    assert b'filename="clip.mp3"' in content and b"ID3fakeaudio" in content
    assert b'["ns1"]' in content


def test_upload_missing_file_raises_before_request(tmp_path):
    api = Api()

    async def go():
        async with make_client(api) as client:
            await client.upload_file(str(tmp_path / "nope.mp4"))

    with pytest.raises(FileNotFoundError):
        run(go())
    assert api.requests == []


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

def test_submit_returns_async_job():
    api = Api().on("POST", "/v1/transcribe/async", (202, accepted("transcribe", webhook_url="https://h.example")))

    async def go():
        async with make_client(api) as client:
            return await client.submit_transcribe_video(video_url="https://ig/x", webhook_url="https://h.example")

    handle = run(go())
    assert isinstance(handle, AsyncJob)
    assert handle.task_id == "task_1" and handle.job_type == "transcribe"
    assert handle.webhook_url == "https://h.example"
    assert repr(handle) == "AsyncJob(job_type='transcribe', task_id='task_1')"
    assert body(api.requests[0]) == {
        "video_url": "https://ig/x", "transcript_text": False, "all_videos": False,
        "webhook_url": "https://h.example",
    }


def test_transcribe_video_blocking(instant_sleep):
    api = (Api()
           .on("POST", "/v1/transcribe/async", (202, accepted("transcribe")))
           .on("GET", "/v1/transcribe/task_1",
               job("transcribe", "processing"),
               job("transcribe", "processing"),
               job("transcribe", "completed", result=TRANSCRIPT_RESULT, usage=USAGE)))

    async def go():
        async with make_client(api) as client:
            return await client.transcribe_video(video_url="https://ig/x", include_usage=True)

    resp = run(go())
    assert isinstance(resp, TranscriptResponse)
    assert resp.data.video_info.title == "Long podcast"
    assert resp.usage.total_credits == 0.5
    polls = api.calls("GET", "/v1/transcribe/task_1")
    assert len(polls) == 3
    assert all(dict(p.url.params) == {"include_usage": "true"} for p in polls)
    assert instant_sleep == [1.0, 1.0]  # fast-start polling


def test_carousel_result(instant_sleep):
    carousel = {"carousel_info": {"video_count": 2}, "videos": [{"index": 1, "transcript": "a"}]}
    api = (Api().on("POST", "/v1/transcribe/async", (202, accepted("transcribe")))
           .on("GET", "/v1/transcribe/task_1", job("transcribe", "completed", result=carousel)))

    async def go():
        async with make_client(api) as client:
            return await client.transcribe_video(video_url="https://ig/p", all_videos=True)

    assert isinstance(run(go()), TranscribeAllVideosResponse)


def test_extract_video_data_blocking_with_schema_file(tmp_path, instant_sleep):
    schema_file = tmp_path / "s.json"
    schema_file.write_text(json.dumps(SCHEMA))
    done = job("extract_video", "completed", result={"mood": "calm"})
    done["data"]["video_info"] = {"title": "Clip"}
    api = (Api().on("POST", "/v1/extract/video/async", (202, accepted("extract_video")))
           .on("GET", "/v1/extract/video/task_1", done))

    async def go():
        async with make_client(api) as client:
            return await client.extract_video_data(video_url="https://ig/x", schema_file=str(schema_file))

    resp = run(go())
    assert isinstance(resp, ExtractionApiResponse)
    assert resp.data == {"mood": "calm"}
    assert resp.video_info.title == "Clip"
    content = api.calls("POST")[0].content.decode()
    assert 'name="transcribe"' in content and 'filename="s.json"' in content
    assert "include_usage" not in content


def test_get_tweet_statement_blocking(instant_sleep):
    result = {"final_statement": "Claim.", "claim_type": "opinion"}
    api = (Api().on("POST", "/v1/tweet/statement/async", (202, accepted("tweet_statement")))
           .on("GET", "/v1/tweet/statement/task_1", job("tweet_statement", "completed", result=result)))

    async def go():
        async with make_client(api) as client:
            return await client.get_tweet_statement(tweet_id="123")

    resp = run(go())
    assert isinstance(resp, TweetStatementResponse)
    assert resp.data.final_statement == "Claim."
    assert body(api.calls("POST")[0]) == {"tweet_id": "123"}


def test_search_tiktok_blocking_passes_limit(instant_sleep):
    submit = {"status": "success", "data": {"task_id": "s1", "task_status": "processing"}}
    api = (Api().on("POST", "/v1/tiktok/search", (202, submit))
           .on("GET", "/v1/tiktok/search/s1",
               tiktok_task("processing", task_id="s1", items_key="results"),
               tiktok_task("completed", task_id="s1", items_key="results")))

    async def go():
        async with make_client(api) as client:
            return await client.search_tiktok(query="ai tools", sort_by="newest", limit=5)

    resp = run(go())
    assert isinstance(resp, TikTokSearchResponse) and resp.data.is_completed
    assert body(api.calls("POST")[0]) == {"query": "ai tools", "sort_by": "newest"}
    assert dict(api.calls("GET")[-1].url.params) == {"limit": "5"}


def test_job_failure_raises_from_error_object(instant_sleep):
    error = {"error": "unsupported_platform", "message": "No YouTube", "http_status": 400}
    api = (Api().on("POST", "/v1/transcribe/async", (202, accepted("transcribe")))
           .on("GET", "/v1/transcribe/task_1", job("transcribe", "failed", error=error)))

    async def go():
        async with make_client(api) as client:
            handle = await client.submit_transcribe_video(video_url="https://youtube.com/x")
            failed = await handle.wait(raise_on_failure=False)
            with pytest.raises(BadRequestError) as exc_info:
                await handle.result()
            return failed, exc_info.value

    failed, exc = run(go())
    assert failed.data.is_failed and failed.data.error.http_status == 400
    assert exc.error_code == "unsupported_platform"


def test_status_done_refresh_and_resume():
    api = Api().on("GET", "/v1/extract/video/t9",
                   job("extract_video", "processing", task_id="t9"),
                   job("extract_video", "completed", result={"a": 1}, task_id="t9"))

    async def go():
        async with make_client(api) as client:
            handle = client.resume_job("extract_video", "t9")
            first = await handle.status()
            finished = await handle.done()
            refreshed = await handle.refresh(include_usage=True)
            return handle, first, finished, refreshed

    handle, first, finished, refreshed = run(go())
    assert (first, finished) == ("processing", True)
    assert refreshed.data.result == {"a": 1}
    assert handle.last_response is refreshed
    assert dict(api.requests[-1].url.params) == {"include_usage": "true"}


def test_timeout_carries_task_id_and_resumable_async_handle():
    clock = {"now": 0.0}

    async def fake_sleep(seconds):
        clock["now"] += seconds

    api = (Api().on("POST", "/v1/transcribe/async", (202, accepted("transcribe", task_id="t-42")))
           .on("GET", "/v1/transcribe/t-42", job("transcribe", "processing", task_id="t-42")))

    async def go():
        async with make_client(api) as client:
            with pytest.raises(JobTimeoutError) as exc_info:
                await client.transcribe_video(video_url="https://ig/x", timeout=5)
            exc = exc_info.value
            api.routes[("GET", "/v1/transcribe/t-42")] = [
                job("transcribe", "completed", result=TRANSCRIPT_RESULT, task_id="t-42")]
            resumed = await exc.job.result()
            return exc, resumed

    with patch("vidnavigator.jobs.time.monotonic", lambda: clock["now"]), \
            patch("vidnavigator.jobs.asyncio.sleep", fake_sleep):
        exc, resumed = run(go())
    assert exc.task_id == "t-42"
    assert isinstance(exc.job, AsyncJob)
    assert clock["now"] == pytest.approx(5)
    assert resumed.data.video_info.title == "Long podcast"


def test_many_jobs_concurrently_with_gather(instant_sleep):
    api = Api()
    for i in range(5):
        api.on("POST", "/v1/transcribe/async", (202, accepted("transcribe", task_id=f"t{i}")))
        api.on("GET", f"/v1/transcribe/t{i}",
               job("transcribe", "processing", task_id=f"t{i}"),
               job("transcribe", "completed", task_id=f"t{i}",
                   result={"video_info": {"title": f"video {i}"}, "transcript": "x"}))

    async def go():
        async with make_client(api) as client:
            return await asyncio.gather(*(
                client.transcribe_video(video_url=f"https://ig/{i}") for i in range(5)
            ))

    results = run(go())
    assert [r.data.video_info.title for r in results] == [f"video {i}" for i in range(5)]
    # The jobs overlapped: all five were submitted before the first one finished.
    last_submit = max(i for i, r in enumerate(api.requests) if r.method == "POST")
    polls = {}
    first_completion = None
    for i, r in enumerate(api.requests):
        if r.method == "GET":
            polls[r.url.path] = polls.get(r.url.path, 0) + 1
            if polls[r.url.path] == 2 and first_completion is None:
                first_completion = i
    assert last_submit < first_completion


def test_polling_does_not_block_the_event_loop():
    """While one job is waiting between polls, other coroutines keep running."""
    api = (Api().on("POST", "/v1/transcribe/async", (202, accepted("transcribe")))
           .on("GET", "/v1/transcribe/task_1",
               job("transcribe", "processing"),
               job("transcribe", "completed", result=TRANSCRIPT_RESULT)))
    polls_seen_by_ticker = []

    async def ticker():
        for _ in range(3):
            polls_seen_by_ticker.append(len(api.calls("GET")))
            await asyncio.sleep(0.01)

    async def go():
        async with make_client(api) as client:
            handle = await client.submit_transcribe_video(video_url="https://ig/x")
            await asyncio.gather(handle.result(poll_interval=0.05, fast_start=False), ticker())

    run(go())
    # The ticker kept running after the first poll, while the job slept 50 ms before the second.
    assert polls_seen_by_ticker == [1, 1, 1]
    assert len(api.calls("GET")) == 2
