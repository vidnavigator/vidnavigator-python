"""Unit tests for all client methods (mocked HTTP, no API key needed)."""

from datetime import date, datetime, timezone
from unittest.mock import patch

import pytest

from vidnavigator import VidNavigatorClient
from vidnavigator.models import (
    TranscriptResponse,
    TranscribeAllVideosResponse,
    FilesListResponse,
    FileResponse,
    AnalysisResponse,
    VideoSearchResponse,
    FileSearchResponse,
    FileNamespacesResponse,
    NamespaceListResponse,
    NamespaceResponse,
    MessageResponse,
    UsageResponse,
    HealthResponse,
    TikTokProfileSubmitResponse,
    TikTokProfileResponse,
    TweetStatementResponse,
)


@pytest.fixture
def client():
    return VidNavigatorClient(api_key="test_key")


# ---------------------------------------------------------------------------
# Transcript endpoints
# ---------------------------------------------------------------------------

TRANSCRIPT_RAW = {
    "status": "success",
    "data": {
        "video_info": {"title": "Test", "duration": 60},
        "transcript": [{"text": "hi", "start": 0.0, "end": 1.0}],
    },
}

TRANSCRIPT_TEXT_RAW = {
    "status": "success",
    "data": {
        "video_info": {"title": "Test"},
        "transcript": "hello world full text",
    },
}


def test_get_transcript_basic(client):
    with patch.object(client, "_request", return_value=TRANSCRIPT_RAW) as req:
        resp = client.get_transcript(video_url="https://example.com/v")
    assert isinstance(resp, TranscriptResponse)
    assert resp.data.video_info.title == "Test"
    assert len(resp.data.transcript) == 1
    req.assert_called_once()


def test_get_transcript_with_all_params(client):
    with patch.object(client, "_request", return_value=TRANSCRIPT_RAW) as req:
        client.get_transcript(
            video_url="https://example.com/v",
            language="en",
            metadata_only=True,
            fallback_to_metadata=True,
            transcript_text=True,
        )
    _, kw = req.call_args
    body = kw["json_body"]
    assert body["language"] == "en"
    assert body["metadata_only"] is True
    assert body["fallback_to_metadata"] is True
    assert body["transcript_text"] is True


def test_get_youtube_transcript(client):
    with patch.object(client, "_request", return_value=TRANSCRIPT_RAW) as req:
        resp = client.get_youtube_transcript(video_url="https://youtube.com/watch?v=x")
    assert isinstance(resp, TranscriptResponse)
    args, _ = req.call_args
    assert args[1] == "/youtube/transcript"


def test_transcript_text_returns_string(client):
    with patch.object(client, "_request", return_value=TRANSCRIPT_TEXT_RAW):
        resp = client.get_youtube_transcript(
            video_url="https://youtube.com/watch?v=x",
            transcript_text=True,
        )
    assert isinstance(resp.data.transcript, str)


def test_transcribe_video_single(client):
    with patch.object(client, "_request", return_value=TRANSCRIPT_RAW):
        resp = client.transcribe_video(video_url="https://example.com/v")
    assert isinstance(resp, TranscriptResponse)


def test_transcribe_video_all_videos(client):
    raw = {
        "status": "success",
        "data": {
            "carousel_info": {"total_items": 3, "video_count": 2, "image_count": 1},
            "videos": [
                {
                    "index": 1,
                    "status": "success",
                    "video_info": {"title": "V1"},
                    "transcript": [{"text": "a", "start": 0, "end": 1}],
                },
            ],
        },
    }
    with patch.object(client, "_request", return_value=raw):
        resp = client.transcribe_video(
            video_url="https://example.com/carousel",
            all_videos=True,
        )
    assert isinstance(resp, TranscribeAllVideosResponse)
    assert resp.data.carousel_info.video_count == 2
    assert len(resp.data.videos) == 1


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------

FILES_LIST_RAW = {
    "status": "success",
    "data": {
        "files": [
            {
                "id": "f1",
                "name": "test.mp4",
                "status": "completed",
                "namespace_ids": ["ns1"],
                "namespaces": [{"id": "ns1", "name": "default"}],
            },
        ],
        "total_count": 1,
        "limit": 50,
        "offset": 0,
        "has_more": False,
    },
}

FILE_RAW = {
    "status": "success",
    "data": {
        "file_info": {
            "id": "f1",
            "name": "test.mp4",
            "has_transcript": True,
            "namespace_ids": ["ns1", "ns2"],
            "namespaces": [
                {"id": "ns1", "name": "default"},
                {"id": "ns2", "name": "Calls"},
            ],
        },
        "transcript": [{"text": "hi", "start": 0, "end": 1}],
    },
}


def test_get_files(client):
    with patch.object(client, "_request", return_value=FILES_LIST_RAW) as req:
        resp = client.get_files(limit=10, offset=0, status="completed")
    assert isinstance(resp, FilesListResponse)
    assert resp.data.total_count == 1
    f = resp.data.files[0]
    assert f.namespace_ids == ["ns1"]
    assert f.namespaces[0].name == "default"
    _, kw = req.call_args
    assert "namespace_id" not in kw["params"]


def test_get_files_with_namespace_filter(client):
    with patch.object(client, "_request", return_value=FILES_LIST_RAW) as req:
        client.get_files(namespace_id="ns1")
    _, kw = req.call_args
    assert kw["params"]["namespace_id"] == "ns1"


def test_get_file_with_transcript_text(client):
    with patch.object(client, "_request", return_value=FILE_RAW) as req:
        resp = client.get_file("f1", transcript_text=True)
    assert isinstance(resp, FileResponse)
    fi = resp.data.file_info
    assert fi.namespace_ids == ["ns1", "ns2"]
    assert len(fi.namespaces) == 2
    assert fi.namespaces[1].name == "Calls"
    _, kw = req.call_args
    assert kw["params"] == {"transcript_text": "true"}


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

ANALYSIS_RAW = {
    "status": "success",
    "data": {
        "video_info": {"title": "Test"},
        "transcript": "full text here",
        "transcript_analysis": {
            "summary": "A summary",
            "query_answer": {
                "answer": "42",
                "best_segment_index": 0,
                "relevant_segments": ["seg1"],
            },
        },
    },
}


def test_analyze_video(client):
    with patch.object(client, "_request", return_value=ANALYSIS_RAW) as req:
        resp = client.analyze_video(
            video_url="https://example.com/v",
            query="what?",
            transcript_text=True,
        )
    assert isinstance(resp, AnalysisResponse)
    assert resp.data.transcript_analysis.summary == "A summary"
    assert resp.data.transcript_analysis.query_answer.answer == "42"
    _, kw = req.call_args
    assert kw["json_body"]["transcript_text"] is True


def test_analyze_file(client):
    raw = {
        "status": "success",
        "data": {
            "file_info": {"id": "f1"},
            "transcript": [],
            "transcript_analysis": {"summary": "File summary"},
        },
    }
    with patch.object(client, "_request", return_value=raw):
        resp = client.analyze_file(file_id="f1")
    assert isinstance(resp, AnalysisResponse)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

SEARCH_VIDEO_RAW = {
    "status": "success",
    "data": {
        "results": [{"title": "R1", "relevance_score": 0.95}],
        "query": "test",
        "total_found": 1,
        "explanation": "top match",
    },
}

SEARCH_FILE_RAW = {
    "status": "success",
    "data": {
        "results": [
            {
                "id": "f1",
                "name": "a.mp4",
                "timestamps": [10.5, 22.0],
                "namespace_ids": ["ns1"],
                "namespaces": [{"id": "ns1", "name": "default"}],
            },
        ],
        "query": "test",
        "total_found": 1,
    },
}


def test_search_videos(client):
    with patch.object(client, "_request", return_value=SEARCH_VIDEO_RAW):
        resp = client.search_videos(query="test", start_year=2020)
    assert isinstance(resp, VideoSearchResponse)
    assert resp.data.total_found == 1


def test_search_files_with_namespace_ids(client):
    with patch.object(client, "_request", return_value=SEARCH_FILE_RAW) as req:
        resp = client.search_files(query="pricing", namespace_ids=["ns1", "ns2"])
    assert isinstance(resp, FileSearchResponse)
    r = resp.data.results[0]
    assert r.timestamps == [10.5, 22.0]
    assert r.namespace_ids == ["ns1"]
    assert r.namespaces[0].name == "default"
    _, kw = req.call_args
    assert kw["json_body"]["namespace_ids"] == ["ns1", "ns2"]


# ---------------------------------------------------------------------------
# Namespaces
# ---------------------------------------------------------------------------

NS_LIST_RAW = {
    "status": "success",
    "data": [
        {"id": "ns1", "name": "default", "user_id": "u1"},
        {"id": "ns2", "name": "Client Calls", "user_id": "u1"},
    ],
}

NS_CREATE_RAW = {
    "status": "success",
    "data": {"id": "ns3", "name": "New NS", "user_id": "u1"},
}

MSG_RAW = {"status": "success", "message": "Done"}


def test_get_namespaces(client):
    with patch.object(client, "_request", return_value=NS_LIST_RAW):
        resp = client.get_namespaces()
    assert isinstance(resp, NamespaceListResponse)
    assert len(resp.data) == 2
    assert resp.data[0].name == "default"


def test_create_namespace(client):
    with patch.object(client, "_request", return_value=NS_CREATE_RAW) as req:
        resp = client.create_namespace(name="New NS")
    assert isinstance(resp, NamespaceResponse)
    assert resp.data.id == "ns3"
    _, kw = req.call_args
    assert kw["json_body"]["name"] == "New NS"


def test_update_namespace(client):
    with patch.object(client, "_request", return_value=MSG_RAW) as req:
        resp = client.update_namespace("ns3", name="Renamed")
    assert isinstance(resp, MessageResponse)
    args, kw = req.call_args
    assert args[0] == "PUT"
    assert "/namespaces/ns3" in args[1]


def test_delete_namespace(client):
    with patch.object(client, "_request", return_value=MSG_RAW) as req:
        resp = client.delete_namespace("ns3")
    assert isinstance(resp, MessageResponse)
    args, _ = req.call_args
    assert args[0] == "DELETE"


FILE_NS_UPDATE_RAW = {
    "status": "success",
    "message": "File namespaces updated",
    "data": {
        "namespace_ids": ["ns1", "ns2"],
        "namespaces": [
            {"id": "ns1", "name": "default"},
            {"id": "ns2", "name": "Calls"},
        ],
    },
}


def test_update_file_namespaces(client):
    with patch.object(client, "_request", return_value=FILE_NS_UPDATE_RAW) as req:
        resp = client.update_file_namespaces("f1", namespace_ids=["ns1", "ns2"])
    assert isinstance(resp, FileNamespacesResponse)
    assert resp.data.namespace_ids == ["ns1", "ns2"]
    assert resp.data.namespaces[1].name == "Calls"
    _, kw = req.call_args
    assert kw["json_body"]["namespace_ids"] == ["ns1", "ns2"]


# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------

USAGE_RAW = {
    "status": "success",
    "data": {
        "credits": {"monthly_total": 500, "monthly_remaining": 480, "purchased": 0},
        "usage": {
            "standard_request": {"used": 3},
            "residential_request": {"used": 7},
            "search_request": {"used": 2},
            "analysis_request": {"used": 1},
            "transcription_hour": {"used": 0.5, "unit": "hours"},
        },
        "channels_indexed": {"used": 1, "limit": 5, "remaining": 4, "percentage": 20.0},
        "storage": {
            "used_bytes": 1024,
            "used_formatted": "1 KB",
            "limit_bytes": 1073741824,
            "limit_formatted": "1 GB",
            "remaining_bytes": 1073740800,
            "remaining_formatted": "1 GB",
            "percentage": 0.0,
        },
    },
}


def test_get_usage(client):
    with patch.object(client, "_request", return_value=USAGE_RAW):
        resp = client.get_usage()
    assert isinstance(resp, UsageResponse)
    d = resp.data
    assert d.credits.monthly_total == 500
    assert d.credits.purchased == 0
    assert d.usage.standard_request.used == 3
    assert d.usage.residential_request.used == 7
    assert d.usage.search_request.used == 2
    assert d.usage.analysis_request.used == 1
    assert d.usage.transcription_hour.unit == "hours"
    assert d.channels_indexed.used == 1
    assert d.channels_indexed.percentage == 20.0
    assert d.storage.used_formatted == "1 KB"


# ---------------------------------------------------------------------------
# TikTok
# ---------------------------------------------------------------------------

def test_submit_tiktok_profile_scrape(client):
    raw = {
        "status": "success",
        "data": {
            "task_id": "task_123",
            "task_status": "processing",
            "profile_url": "https://www.tiktok.com/@tiktok",
            "expires_at": "2026-04-26T12:00:00Z",
            "check_status_url": "/v1/tiktok/profile/task_123",
            "message": "Task accepted",
        },
    }
    with patch.object(client, "_request", return_value=raw) as req:
        resp = client.submit_tiktok_profile_scrape(
            profile_url="https://www.tiktok.com/@tiktok",
            max_posts=100,
            after_date=date(2024, 1, 1),
            before_date=datetime(2024, 12, 31, 10, 30, tzinfo=timezone.utc),
            min_likes=1000,
        )
    assert isinstance(resp, TikTokProfileSubmitResponse)
    assert resp.data.task_id == "task_123"
    req.assert_called_once_with(
        "POST",
        "/tiktok/profile",
        json_body={
            "profile_url": "https://www.tiktok.com/@tiktok",
            "max_posts": 100,
            "after_date": "2024-01-01",
            "before_date": "2024-12-31",
            "min_likes": 1000,
        },
    )


def test_get_tiktok_profile_scrape(client):
    raw = {
        "status": "success",
        "data": {
            "task_id": "task_123",
            "task_status": "completed",
            "profile_url": "https://www.tiktok.com/@tiktok",
            "profile": {"uploader": "tiktok"},
            "filters": {"max_posts": "10", "after_date": "2024-01-01"},
            "stats": {"videos_scanned": "10", "videos_matched": "1", "pages_consumed": "1"},
            "videos": [
                {
                    "id": "v1",
                    "title": "Demo",
                    "timestamp": "1776892618",
                    "published_at": "2026-04-22T21:16:58+00:00",
                    "views": "1,234",
                    "likes": "123",
                    "reposts": "4",
                    "comments": "5",
                    "url": "https://www.tiktok.com/@tiktok/video/1",
                }
            ],
            "pagination": {"limit": "50", "offset": "0", "total_items": "1", "has_next": False, "has_prev": False},
            "download_url": "https://storage.googleapis.com/bucket/task.json",
        },
    }
    with patch.object(client, "_request", return_value=raw) as req:
        resp = client.get_tiktok_profile_scrape("task_123", cursor="abc", limit=25)
    assert isinstance(resp, TikTokProfileResponse)
    assert resp.data.filters.max_posts == 10
    assert resp.data.stats.videos_scanned == 10
    assert resp.data.videos[0].views == 1234
    assert resp.data.videos[0].likes == 123
    assert resp.data.videos[0].published_at.isoformat() == "2026-04-22T21:16:58+00:00"
    assert resp.data.pagination.total_items == 1
    req.assert_called_once_with(
        "GET",
        "/tiktok/profile/task_123",
        params={"limit": 25, "cursor": "abc"},
    )


# ---------------------------------------------------------------------------
# Tweet analysis
# ---------------------------------------------------------------------------

def test_get_tweet_statement(client):
    raw = {
        "status": "success",
        "data": {
            "final_statement": "The author claims something nuanced.",
            "statement_query": "nuanced claim",
            "detailed_analysis": "A short analysis.",
            "topics": ["media"],
            "entities": ["Example"],
            "claim_type": "factual_claim",
            "intent": "inform",
            "tone": "serious",
            "emotion": "curiosity",
            "authority": "data_driven",
            "tweet_text": "Example tweet",
        },
    }
    with patch.object(client, "_request", return_value=raw) as req:
        resp = client.get_tweet_statement(tweet_id="1234567890")
    assert isinstance(resp, TweetStatementResponse)
    assert resp.data.final_statement.startswith("The author")
    req.assert_called_once_with(
        "POST",
        "/tweet/statement",
        json_body={"tweet_id": "1234567890"},
    )


# ---------------------------------------------------------------------------
# Error mapping
# ---------------------------------------------------------------------------

def test_health_check(client):
    raw = {
        "status": "success",
        "message": "OK",
        "version": "1.0.0",
        "endpoints": [{"path": "/health", "method": "GET", "auth_required": False}],
    }
    with patch.object(client, "_request", return_value=raw):
        resp = client.health_check()
    assert isinstance(resp, HealthResponse)
    assert resp.status == "success"
    assert resp.endpoints[0].path == "/health"
