"""Integration tests that hit the real VidNavigator API.

Require VIDNAVIGATOR_API_KEY environment variable. Skipped automatically
when the key is not set, so ``pytest tests/`` remains safe to run offline.

Run only integration tests:
    pytest tests/test_integration.py -v
"""

import os
import time
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import pytest

from vidnavigator import VidNavigatorClient, VidNavigatorError


def _dump(obj):
    return obj.model_dump() if hasattr(obj, "model_dump") else obj.dict()


_api_key = os.getenv("VIDNAVIGATOR_API_KEY")
pytestmark = pytest.mark.skipif(not _api_key, reason="VIDNAVIGATOR_API_KEY not set")

TEST_VIDEO_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
TEST_VIDEO_FILE = FIXTURES_DIR / "video-test.mp4"


@pytest.fixture(scope="module")
def client():
    return VidNavigatorClient(api_key=_api_key, timeout=120)


# -- System ----------------------------------------------------------------

def test_health_check(client):
    health = client.health_check()
    assert health["status"] == "success"


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


# -- YouTube transcript ----------------------------------------------------

def test_youtube_transcript_segments(client):
    resp = client.get_youtube_transcript(video_url=TEST_VIDEO_URL)
    assert resp.status == "success"
    assert resp.data.video_info.title
    transcript = resp.data.transcript
    assert isinstance(transcript, list)
    assert len(transcript) > 0
    assert transcript[0].text


def test_youtube_transcript_plain_text(client):
    resp = client.get_youtube_transcript(
        video_url=TEST_VIDEO_URL,
        transcript_text=True,
    )
    assert isinstance(resp.data.transcript, str)
    assert len(resp.data.transcript) > 0


# -- Analysis --------------------------------------------------------------

def test_analyze_video_with_query(client):
    resp = client.analyze_video(
        video_url=TEST_VIDEO_URL,
        query="What is the main message of this song?",
    )
    analysis = resp.data.transcript_analysis
    assert analysis.summary


# -- Search ----------------------------------------------------------------

def test_search_videos(client):
    resp = client.search_videos(query="never gonna give you up")
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
        assert resp.usage.total_tokens > 0


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
