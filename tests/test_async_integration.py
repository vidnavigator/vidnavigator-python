"""Live integration tests for AsyncVidNavigatorClient.

Require VIDNAVIGATOR_API_KEY (and httpx); skipped otherwise. Set
VIDNAVIGATOR_BASE_URL to test a local or staging API.
"""

import asyncio
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import pytest

httpx = pytest.importorskip("httpx")

from vidnavigator import (  # noqa: E402
    AsyncJob,
    AsyncVidNavigatorClient,
    AuthenticationError,
    BadRequestError,
    JobTimeoutError,
    NotFoundError,
    VidNavigatorError,
)

_api_key = os.getenv("VIDNAVIGATOR_API_KEY")
_base_url = os.getenv("VIDNAVIGATOR_BASE_URL")
pytestmark = pytest.mark.skipif(not _api_key, reason="VIDNAVIGATOR_API_KEY not set")

YT = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
SCHEMA = {"mood": {"type": "String", "description": "One word describing the mood"}}
TRANSCRIBE_URL = os.getenv("VIDNAVIGATOR_TRANSCRIBE_URL")
TWEET_ID = os.getenv("VIDNAVIGATOR_TWEET_ID")
JOB_TIMEOUT = int(os.getenv("VIDNAVIGATOR_ASYNC_TIMEOUT_SECONDS", "300"))
TEST_VIDEO_FILE = Path(__file__).resolve().parent / "fixtures" / "video-test.mp4"


def run(coro_fn):
    """Run ``coro_fn(client)`` with a fresh client (one event loop per test)."""
    async def main():
        kwargs = {"api_key": _api_key, "timeout": 120}
        if _base_url:
            kwargs["base_url"] = _base_url
        async with AsyncVidNavigatorClient(**kwargs) as client:
            return await coro_fn(client)
    return asyncio.run(main())


def test_health_usage_and_transcript():
    async def go(client):
        health, usage, transcript = await asyncio.gather(
            client.health_check(),
            client.get_usage(),
            client.get_transcript(video_url=YT, transcript_text=True),
        )
        return health, usage, transcript

    health, usage, transcript = run(go)
    assert health.status == "success"
    assert usage.data.credits is not None or usage.data.storage is not None
    assert isinstance(transcript.data.transcript, str) and transcript.data.transcript


def test_invalid_api_key():
    async def main():
        kwargs = {"api_key": "vna_invalid_sdk_test_key"}
        if _base_url:
            kwargs["base_url"] = _base_url
        async with AsyncVidNavigatorClient(**kwargs) as client:
            await client.get_files(limit=1)

    with pytest.raises(AuthenticationError):
        asyncio.run(main())


def test_extract_video_data_blocking_and_handle():
    async def go(client):
        blocking = await client.extract_video_data(
            video_url=YT, schema=SCHEMA, transcribe=False, include_usage=True, timeout=JOB_TIMEOUT,
        )
        handle = await client.submit_extract_video_data(
            video_url=YT, schema=SCHEMA, transcribe=False, webhook_url="",
        )
        status = await handle.status()
        result = await handle.result(timeout=JOB_TIMEOUT)
        resumed = await client.resume_job("extract_video", handle.task_id).result()
        return blocking, handle, status, result, resumed

    blocking, handle, status, result, resumed = run(go)
    assert "mood" in blocking.data
    assert blocking.video_info is not None and blocking.video_info.title
    assert isinstance(handle, AsyncJob) and handle.webhook_url is None
    assert status in ("processing", "completed")
    assert resumed.data == result.data


def test_concurrent_jobs_with_gather():
    async def go(client):
        return await asyncio.gather(*(
            client.extract_video_data(
                video_url=YT,
                schema={"answer": {"type": "String", "description": question}},
                transcribe=False,
                timeout=JOB_TIMEOUT,
            )
            for question in ("The main theme", "The mood", "The intended audience")
        ))

    results = run(go)
    assert len(results) == 3
    assert all("answer" in r.data for r in results)  # the LLM may leave a field empty


def test_invalid_schema_rejected_at_submit():
    async def go(client):
        await client.submit_extract_video_data(
            video_url=YT, schema={"x": {"type": "NotAType", "description": "?"}},
        )

    with pytest.raises(BadRequestError) as exc_info:
        run(go)
    assert exc_info.value.error_code == "invalid_schema"


def test_failed_job_raises_from_error_object():
    async def go(client):
        handle = await client.submit_transcribe_video(video_url=YT)  # YouTube: unsupported by STT
        failed = await handle.wait(raise_on_failure=False, timeout=JOB_TIMEOUT)
        try:
            await handle.result()
        except BadRequestError as exc:
            return failed, exc
        return failed, None

    failed, exc = run(go)
    assert failed.data.is_failed and failed.data.error.error == "unsupported_platform"
    assert exc is not None and exc.error_code == "unsupported_platform"


def test_timeout_keeps_task_id_and_resumes():
    async def go(client):
        handle = await client.submit_extract_video_data(
            video_url=YT, schema=SCHEMA, transcribe=False, webhook_url="",
        )
        try:
            await handle.wait(timeout=0)
            resumed = client.resume_job("extract_video", handle.task_id)
        except JobTimeoutError as exc:
            assert exc.task_id == handle.task_id
            resumed = exc.job
        return await resumed.result(timeout=JOB_TIMEOUT)

    assert "mood" in run(go).data


@pytest.mark.parametrize("job_type", ["transcribe", "extract_video", "tweet_statement"])
def test_unknown_task_not_found(job_type):
    async def go(client):
        await client.resume_job(job_type, "00000000-0000-0000-0000-000000000000").status()

    with pytest.raises(NotFoundError) as exc_info:
        run(go)
    assert exc_info.value.error_code == "task_not_found"


def test_tiktok_search_and_pagination():
    async def go(client):
        first = await client.search_tiktok(query="ai tools", max_results=6, limit=3, timeout=JOB_TIMEOUT)
        page2 = None
        if first.data.pagination and first.data.pagination.has_next:
            page2 = await client.get_tiktok_search(
                first.data.task_id, cursor=first.data.pagination.next_cursor, limit=3,
            )
        return first, page2

    first, page2 = run(go)
    assert first.data.is_completed
    assert first.data.results is not None
    if page2 is not None:
        assert page2.data.results is not None


@pytest.mark.skipif(not TRANSCRIBE_URL, reason="VIDNAVIGATOR_TRANSCRIBE_URL not set")
def test_transcribe_video():
    async def go(client):
        return await client.transcribe_video(
            video_url=TRANSCRIBE_URL, transcript_text=True, include_usage=True, timeout=JOB_TIMEOUT,
        )

    resp = run(go)
    assert isinstance(resp.data.transcript, str) and resp.data.transcript
    assert resp.usage is not None


@pytest.mark.skipif(not TWEET_ID, reason="VIDNAVIGATOR_TWEET_ID not set")
def test_tweet_statement():
    async def go(client):
        return await client.get_tweet_statement(tweet_id=TWEET_ID, timeout=JOB_TIMEOUT)

    assert run(go).data.final_statement


def test_file_upload_extract_and_delete():
    if not TEST_VIDEO_FILE.exists():
        pytest.skip(f"Test fixture not found: {TEST_VIDEO_FILE}")

    async def go(client):
        uploaded = await client.upload_file(str(TEST_VIDEO_FILE), wait_for_completion=True)
        file_id = uploaded.get("file_id")
        try:
            for _ in range(60):
                info = await client.get_file(file_id)
                if info.data.file_info.status == "completed":
                    break
                await asyncio.sleep(3)
            extracted = await client.extract_file_data(
                file_id=file_id,
                schema={"gist": {"type": "String", "description": "One sentence summary"}},
            )
            return file_id, extracted
        finally:
            if file_id:
                try:
                    await client.delete_file(file_id)
                except VidNavigatorError:
                    pass

    file_id, extracted = run(go)
    assert file_id
    assert isinstance(extracted.data, dict)
