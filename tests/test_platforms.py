"""Live platform matrix: captions and speech-to-text on every supported platform.

Opt-in because it runs real transcriptions (billed). Enable with
``VIDNAVIGATOR_PLATFORM_TESTS=1`` plus the usual ``VIDNAVIGATOR_API_KEY`` (and
``VIDNAVIGATOR_BASE_URL`` for a local or staging API):

    VIDNAVIGATOR_PLATFORM_TESTS=1 pytest tests/test_platforms.py -v
"""

import os
import re

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import pytest

from vidnavigator import VidNavigatorClient

_api_key = os.getenv("VIDNAVIGATOR_API_KEY")
_base_url = os.getenv("VIDNAVIGATOR_BASE_URL")
pytestmark = pytest.mark.skipif(
    not (_api_key and os.getenv("VIDNAVIGATOR_PLATFORM_TESTS")),
    reason="set VIDNAVIGATOR_PLATFORM_TESTS=1 and VIDNAVIGATOR_API_KEY to run the platform matrix",
)

JOB_TIMEOUT = int(os.getenv("VIDNAVIGATOR_ASYNC_TIMEOUT_SECONDS", "900"))

# Caption extraction (get_transcript)
TRANSCRIPT_URLS = {
    "youtube": "https://www.youtube.com/watch?v=4czjS9h4Fpg",
    "youtube_shorts": "https://www.youtube.com/shorts/WhNzhnXO16c",
    "tiktok": "https://www.tiktok.com/@space_minds/video/7662062584748723459?lang=en",
    "x": "https://x.com/elonmusk/status/1857814606120436119",
    "facebook": "https://www.facebook.com/DenOfficial2022/videos/4945734342179124/",
    "vimeo": "https://vimeo.com/753580183",
    "rumble": "https://rumble.com/v7cphaw-we-were-born-corporate-slaves-since-1871..html?e9s=src_v1_viral",
    "dailymotion": "https://www.dailymotion.com/video/x8rfjqt",
}

# Speech-to-text (transcribe_video, a background job)
TRANSCRIBE_URLS = {
    "instagram": "https://www.instagram.com/whitehouse/reel/DaV4I-BRqur/",
    "tiktok": "https://www.tiktok.com/@space_minds/video/7662062584748723459?lang=en",
    "x": "https://x.com/elonmusk/status/1857814606120436119",
    "facebook": "https://www.facebook.com/DenOfficial2022/videos/4945734342179124/",
    "vimeo": "https://vimeo.com/753580183",
    "rumble": "https://rumble.com/v7cphaw-we-were-born-corporate-slaves-since-1871..html?e9s=src_v1_viral",
    "dailymotion": "https://www.dailymotion.com/video/x8rfjqt",
}

TWEET_URL = "https://x.com/arielhelwani/status/2091986569276408245"


@pytest.fixture(scope="module")
def client():
    kwargs = {"api_key": _api_key, "timeout": 300}
    if _base_url:
        kwargs["base_url"] = _base_url
    with VidNavigatorClient(**kwargs) as c:
        yield c


@pytest.mark.parametrize("platform,url", sorted(TRANSCRIPT_URLS.items()))
def test_get_transcript(client, platform, url):
    segments = client.get_transcript(video_url=url, include_usage=True)
    assert segments.data.video_info is not None
    assert isinstance(segments.data.transcript, list) and segments.data.transcript
    first = segments.data.transcript[0]
    assert first.text and first.end >= first.start

    text = client.get_transcript(video_url=url, transcript_text=True)
    assert isinstance(text.data.transcript, str) and text.data.transcript.strip()


@pytest.mark.parametrize("platform,url", sorted(TRANSCRIPT_URLS.items()))
def test_get_transcript_metadata_only(client, platform, url):
    resp = client.get_transcript(video_url=url, metadata_only=True)
    assert resp.data.video_info is not None
    assert not resp.data.transcript


@pytest.mark.parametrize("platform,url", sorted(TRANSCRIBE_URLS.items()))
def test_transcribe_video(client, platform, url):
    resp = client.transcribe_video(
        video_url=url, include_usage=True, timeout=JOB_TIMEOUT,
    )
    assert resp.data.video_info is not None
    assert isinstance(resp.data.transcript, list) and resp.data.transcript
    assert resp.usage is not None
    assert resp.usage.charge_for("transcription_hour") is not None


def test_transcribe_plain_text_handle(client):
    job = client.submit_transcribe_video(video_url=TRANSCRIBE_URLS["instagram"], transcript_text=True)
    resp = job.result(timeout=JOB_TIMEOUT)
    assert isinstance(resp.data.transcript, str) and resp.data.transcript.strip()


def test_extract_with_auto_transcription(client):
    resp = client.extract_video_data(
        video_url=TRANSCRIBE_URLS["instagram"],
        schema={
            "topic": {"type": "String", "description": "Main topic in a few words"},
            "sentiment": {
                "type": "Enum",
                "description": "Overall sentiment",
                "enum": ["positive", "negative", "neutral"],
            },
        },
        transcribe=True,
        include_usage=True,
        timeout=JOB_TIMEOUT,
    )
    assert resp.data.get("topic")
    assert resp.data.get("sentiment") in ("positive", "negative", "neutral")
    assert resp.usage.charge_for("analysis_request") is not None


def test_analyze_video_tiktok(client):
    resp = client.analyze_video(
        video_url=TRANSCRIPT_URLS["tiktok"], query="What is this video about?",
    )
    assert resp.data.transcript_analysis.summary


def test_tweet_statement_from_url(client):
    tweet_id = re.search(r"/status/(\d+)", TWEET_URL).group(1)
    resp = client.get_tweet_statement(tweet_id=tweet_id, include_usage=True, timeout=JOB_TIMEOUT)
    assert resp.data.final_statement
    assert resp.data.claim_type
    assert resp.usage is not None


def test_search_youtube_ai_tools(client):
    resp = client.search_youtube(query="ai tools", max_results=2)
    assert resp.data.results
    assert resp.data.results[0].url
