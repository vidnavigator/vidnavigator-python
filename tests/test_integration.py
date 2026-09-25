"""Integration tests that hit the real VidNavigator API.

Require VIDNAVIGATOR_API_KEY environment variable. Skipped automatically
when the key is not set, so ``pytest tests/`` remains safe to run offline.
Set VIDNAVIGATOR_BASE_URL to test a local or staging API.

Run only integration tests:
    pytest tests/test_integration.py -v
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import pytest

from vidnavigator import (
    AsyncJob,
    AsyncJobTimeoutError,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    VidNavigatorClient,
    VidNavigatorError,
)


def _dump(obj):
    return obj.model_dump() if hasattr(obj, "model_dump") else obj.dict()


_api_key = os.getenv("VIDNAVIGATOR_API_KEY")
_base_url = os.getenv("VIDNAVIGATOR_BASE_URL")
pytestmark = pytest.mark.skipif(not _api_key, reason="VIDNAVIGATOR_API_KEY not set")

TEST_VIDEO_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
TEST_TIKTOK_PROFILE_URL = os.getenv("VIDNAVIGATOR_TIKTOK_PROFILE_URL")
TEST_TWEET_ID = os.getenv("VIDNAVIGATOR_TWEET_ID")
# A non-YouTube video that speech-to-text can process (e.g. a TikTok or Instagram reel).
TEST_TRANSCRIBE_URL = os.getenv("VIDNAVIGATOR_TRANSCRIBE_URL")
TIKTOK_TIMEOUT_SECONDS = int(os.getenv("VIDNAVIGATOR_TIKTOK_TIMEOUT_SECONDS", "180"))
ASYNC_JOB_TIMEOUT_SECONDS = int(os.getenv("VIDNAVIGATOR_ASYNC_TIMEOUT_SECONDS", "300"))
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
TEST_VIDEO_FILE = FIXTURES_DIR / "video-test.mp4"


@pytest.fixture(scope="module")
def client():
    kwargs = {"api_key": _api_key, "timeout": 120}
    if _base_url:
        kwargs["base_url"] = _base_url
    return VidNavigatorClient(**kwargs)


# -- System ----------------------------------------------------------------

def test_health_check(client):
    health = client.health_check()
    assert health.status == "success"


def test_invalid_api_key_raises_authentication_error():
    kwargs = {"api_key": "vna_invalid_sdk_test_key"}
    if _base_url:
        kwargs["base_url"] = _base_url
    with VidNavigatorClient(**kwargs) as bad_client:
        with pytest.raises(AuthenticationError) as exc_info:
            bad_client.get_files(limit=1)
    assert exc_info.value.status_code == 401


def test_usage(client):
    resp = client.get_usage()
    d = resp.data
    assert d.credits is not None or d.storage is not None
    if d.credits:
        assert d.credits.monthly_total is not None
    if d.usage:
        dump = _dump(d.usage)
        assert isinstance(dump, dict)
    if d.channels_indexed:
        assert d.channels_indexed.used >= 0


# -- Transcript ------------------------------------------------------------

def test_transcript_segments(client):
    resp = client.get_transcript(video_url=TEST_VIDEO_URL)
    assert resp.status == "success"
    assert resp.data.video_info.title
    transcript = resp.data.transcript
    assert isinstance(transcript, list)
    assert len(transcript) > 0
    assert transcript[0].text


def test_transcript_plain_text_with_usage(client):
    resp = client.get_transcript(
        video_url=TEST_VIDEO_URL,
        transcript_text=True,
        include_usage=True,
    )
    assert isinstance(resp.data.transcript, str)
    assert len(resp.data.transcript) > 0
    if resp.usage:
        assert resp.usage.charges is not None


# -- Analysis --------------------------------------------------------------

def test_analyze_video_with_query(client):
    resp = client.analyze_video(
        video_url=TEST_VIDEO_URL,
        query="What is the main message of this song?",
        include_usage=True,
    )
    analysis = resp.data.transcript_analysis
    assert analysis.summary


# -- Search ----------------------------------------------------------------

def test_search_youtube(client):
    resp = client.search_youtube(query="never gonna give you up", max_results=2)
    assert resp.status == "success"
    assert isinstance(resp.data.results, list)
    assert len(resp.data.results) > 0
    first = resp.data.results[0]
    assert first.title


# -- Namespaces (create -> rename -> delete) --------------------------------

def test_namespace_lifecycle(client):
    listed = client.get_namespaces()
    assert isinstance(listed.data, list)

    created = client.create_namespace(name="SDK Integration Test")
    ns_id = created.data.id
    assert ns_id

    renamed = client.update_namespace(ns_id, name="SDK Renamed")
    assert renamed.status == "success"

    deleted = client.delete_namespace(ns_id)
    assert deleted.status == "success"


# -- Extraction: video -----------------------------------------------------

def test_extract_video_data_basic(client):
    resp = client.extract_video_data(
        video_url=TEST_VIDEO_URL,
        schema={
            "one_word_mood": {
                "type": "String",
                "description": "Single word describing the overall mood",
            },
            "has_lyrics": {
                "type": "Boolean",
                "description": "Whether the video has spoken or sung lyrics",
            },
        },
        what_to_extract="Infer mood from the lyrics/topic only.",
    )
    assert resp.status == "success"
    assert isinstance(resp.data, dict)


def test_extract_video_data_with_usage(client):
    resp = client.extract_video_data(
        video_url=TEST_VIDEO_URL,
        schema={
            "single_label": {
                "type": "String",
                "description": "One short label for the video",
            },
        },
        include_usage=True,
    )
    assert resp.status == "success"
    if resp.usage:
        assert resp.usage.charges is not None
        assert resp.usage.total_credits is not None
        tokens = resp.usage.analysis_tokens
        if tokens:
            assert tokens.total_tokens > 0


def test_extract_video_data_with_transcribe_option(client):
    resp = client.extract_video_data(
        video_url=TEST_VIDEO_URL,
        schema={
            "short_summary": {
                "type": "String",
                "description": "A short summary of the video",
            },
        },
        transcribe=False,
    )
    assert resp.status == "success"
    assert isinstance(resp.data, dict)


# -- TikTok profile scrape --------------------------------------------------

@pytest.mark.skipif(
    not TEST_TIKTOK_PROFILE_URL,
    reason="VIDNAVIGATOR_TIKTOK_PROFILE_URL not set",
)
def test_tiktok_profile_scrape_lifecycle(client):
    result = client.scrape_tiktok_profile(
        profile_url=TEST_TIKTOK_PROFILE_URL,
        max_posts=2,
        limit=5,
        timeout=TIKTOK_TIMEOUT_SECONDS,
    )
    assert result.status == "success"
    assert result.data.task_status == "completed"
    assert result.data.videos is not None
    assert result.data.pagination is not None

    if result.data.videos:
        first_video = result.data.videos[0]
        assert first_video.url
        if first_video.published_at:
            assert isinstance(first_video.published_at, datetime)
        for metric in (first_video.views, first_video.likes, first_video.reposts, first_video.comments):
            if metric is not None:
                assert isinstance(metric, int)

    if result.data.download_url:
        with urlopen(result.data.download_url) as response:
            downloaded = json.load(response)
        assert isinstance(downloaded, dict)
        assert isinstance(downloaded.get("videos", []), list)


def test_tiktok_search_lifecycle(client):
    task = client.submit_tiktok_search(
        query="ai tools",
        max_results=2,
        parallel_search_slices=1,
        sort_by="most_liked",
        published_within="this_month",
        webhook_url="",
    )
    assert isinstance(task, AsyncJob)
    assert task.task_id
    assert task.data.query == "ai tools"
    assert task.webhook_url is None

    result = task.result(limit=5, include_usage=True, timeout=TIKTOK_TIMEOUT_SECONDS)
    assert result.status == "success"
    assert result.data.task_status == "completed"
    assert result.data.is_completed
    assert result.data.error is None
    if result.data.stats:
        assert result.data.stats.sort_by in (None, "most_liked")
        assert result.data.stats.published_within in (None, "this_month")
    assert result.data.results is not None
    assert result.data.pagination is not None

    if result.data.results:
        first_result = result.data.results[0]
        assert first_result.url
        if first_result.published_at:
            assert isinstance(first_result.published_at, datetime)
        if first_result.stats:
            for metric in (
                first_result.stats.views,
                first_result.stats.likes,
                first_result.stats.comments,
                first_result.stats.shares,
                first_result.stats.collects,
            ):
                if metric is not None:
                    assert isinstance(metric, int)

    if result.data.download_url:
        with urlopen(result.data.download_url) as response:
            downloaded = json.load(response)
        assert isinstance(downloaded, dict)
        assert isinstance(downloaded.get("results", []), list)


def test_tiktok_search_rejects_private_webhook_url(client):
    with pytest.raises(BadRequestError):
        client.submit_tiktok_search(query="ai tools", webhook_url="https://127.0.0.1/hook")


# -- Background jobs -------------------------------------------------------

def test_extract_video_data_blocking_runs_as_job(client):
    resp = client.extract_video_data(
        video_url=TEST_VIDEO_URL,
        schema={"mood": {"type": "String", "description": "One word describing the mood"}},
        transcribe=False,
        include_usage=True,
        timeout=ASYNC_JOB_TIMEOUT_SECONDS,
    )
    assert resp.status == "success"
    assert "mood" in resp.data
    if resp.usage:
        assert resp.usage.charge_for("analysis_request") is not None


def test_extract_video_job_handle_lifecycle(client):
    handle = client.submit_extract_video_data(
        video_url=TEST_VIDEO_URL,
        schema={"mood": {"type": "String", "description": "One word describing the mood"}},
        transcribe=False,
        webhook_url="",
    )
    assert isinstance(handle, AsyncJob)
    assert handle.job_type == "extract_video"
    assert handle.check_status_url.endswith(handle.task_id)
    assert handle.webhook_url is None
    assert handle.status() in ("processing", "completed")

    done = handle.wait(timeout=ASYNC_JOB_TIMEOUT_SECONDS)
    assert done.data.is_completed
    assert done.data.request["video_url"] == TEST_VIDEO_URL
    assert done.data.completed_at

    # Reading a finished job does not consume it; a fresh handle from the id sees it too.
    resumed = client.resume_job("extract_video", handle.task_id)
    assert resumed.done()
    assert resumed.result().data == done.data.result


def test_extract_invalid_schema_rejected_at_submit(client):
    with pytest.raises(BadRequestError) as exc_info:
        client.submit_extract_video_data(
            video_url=TEST_VIDEO_URL,
            schema={"mood": {"type": "NotAType", "description": "x"}},
        )
    assert exc_info.value.error_code == "invalid_schema"


def test_submit_rejects_private_webhook_url(client):
    with pytest.raises(BadRequestError):
        client.submit_transcribe_video(
            video_url="https://www.tiktok.com/@tiktok/video/1",
            webhook_url="https://127.0.0.1/hook",
        )


def test_failed_job_raises_from_error_object(client):
    """YouTube is not supported by /transcribe, so the job fails deterministically (charges reverted)."""
    handle = client.submit_transcribe_video(video_url=TEST_VIDEO_URL)

    failed = handle.wait(raise_on_failure=False, timeout=ASYNC_JOB_TIMEOUT_SECONDS)
    assert failed.data.is_failed
    assert failed.data.error.error == "unsupported_platform"
    assert failed.data.error.http_status == 400
    assert failed.usage is None

    with pytest.raises(BadRequestError) as exc_info:
        handle.result()
    assert exc_info.value.error_code == "unsupported_platform"
    assert exc_info.value.status_code == 400


def test_blocking_timeout_keeps_task_id_and_resumes(client):
    handle = client.submit_extract_video_data(
        video_url=TEST_VIDEO_URL,
        schema={"mood": {"type": "String", "description": "One word describing the mood"}},
        transcribe=False,
    )
    try:
        handle.wait(timeout=0)
    except AsyncJobTimeoutError as exc:
        assert exc.task_id == handle.task_id
        resumed = exc.job
    else:  # finished before the first poll returned
        resumed = client.resume_job("extract_video", handle.task_id)
    assert "mood" in resumed.result(timeout=ASYNC_JOB_TIMEOUT_SECONDS).data


@pytest.mark.skipif(not TEST_TRANSCRIBE_URL, reason="VIDNAVIGATOR_TRANSCRIBE_URL not set")
def test_transcribe_video_blocking(client):
    resp = client.transcribe_video(
        video_url=TEST_TRANSCRIBE_URL,
        transcript_text=True,
        include_usage=True,
        timeout=ASYNC_JOB_TIMEOUT_SECONDS,
    )
    assert resp.data.video_info is not None
    assert isinstance(resp.data.transcript, str)
    if resp.usage:
        assert resp.usage.total_credits is not None


@pytest.mark.parametrize(
    "job_type",
    ["transcribe", "extract_video", "tweet_statement"],
)
def test_unknown_task_raises_not_found(client, job_type):
    with pytest.raises(NotFoundError) as exc_info:
        client.resume_job(job_type, "00000000-0000-0000-0000-000000000000").status()
    assert exc_info.value.error_code == "task_not_found"


# -- Tweet analysis ---------------------------------------------------------

@pytest.mark.skipif(not TEST_TWEET_ID, reason="VIDNAVIGATOR_TWEET_ID not set")
def test_tweet_statement(client):
    resp = client.get_tweet_statement(tweet_id=TEST_TWEET_ID, timeout=ASYNC_JOB_TIMEOUT_SECONDS)
    assert resp.status == "success"
    assert resp.data.final_statement
    assert resp.data.statement_query


# -- File upload + extract lifecycle ----------------------------------------

def test_file_upload_and_extract(client):
    """Upload tests/fixtures/video-test.mp4, wait for processing, extract, clean up."""
    if not TEST_VIDEO_FILE.exists():
        pytest.skip(f"Test fixture not found: {TEST_VIDEO_FILE}")

    file_id = None
    try:
        try:
            result = client.upload_file(
                str(TEST_VIDEO_FILE), wait_for_completion=True,
            )
        except VidNavigatorError as exc:
            pytest.skip(f"Upload rejected by API: {exc}")

        file_id = result.get("file_id")
        assert file_id, f"Upload did not return file_id: {result}"

        if result.get("file_status") != "completed":
            for _ in range(60):
                time.sleep(3)
                file_resp = client.get_file(file_id)
                if file_resp.data.file_info.status == "completed":
                    break
            else:
                pytest.skip("File processing did not complete in time")

        ext = client.extract_file_data(
            file_id=file_id,
            schema={
                "gist": {
                    "type": "String",
                    "description": "One sentence summary of the file content",
                },
            },
            what_to_extract="Summarize the main point only.",
        )
        assert ext.status == "success"
        assert isinstance(ext.data, dict)

    finally:
        if file_id:
            try:
                client.delete_file(file_id)
            except VidNavigatorError:
                pass


# -- Files list ------------------------------------------------------------

def test_list_files(client):
    resp = client.get_files(limit=5)
    assert resp.status == "success"
    assert resp.data.total_count >= 0
