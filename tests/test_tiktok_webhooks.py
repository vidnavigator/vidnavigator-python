"""Unit tests for TikTok jobs: handles, blocking calls, webhook pass-through, filters."""

from datetime import date
from unittest.mock import patch

import pytest

from vidnavigator import Job, BadRequestError, VidNavigatorClient, VidNavigatorError
from vidnavigator.models import TikTokLiveSearchResponse, TikTokProfileResponse, TikTokSearchResponse

from .helpers import tiktok_task


@pytest.fixture
def client():
    return VidNavigatorClient(api_key="test_key")


def _profile_submit(webhook_url=None):
    return {
        "status": "success",
        "data": {
            "task_id": "p1",
            "task_status": "processing",
            "profile_url": "https://www.tiktok.com/@tiktok",
            "expires_at": "2026-09-25T12:00:00Z",
            "check_status_url": "/v1/tiktok/profile/p1",
            "message": "Task accepted",
            "webhook_url": webhook_url,
        },
    }


def _search_submit(webhook_url=None):
    return {
        "status": "success",
        "data": {
            "task_id": "s1",
            "task_status": "processing",
            "query": "ai tools",
            "max_results": 0,
            "parallel_search_slices": 1,
            "filters": {"sort_by": "most_liked", "published_within": "this_week"},
            "check_status_url": "/v1/tiktok/search/s1",
            "webhook_url": webhook_url,
        },
    }


def _profile(status, **extra):
    return tiktok_task(status, task_id="p1", items_key="videos", **extra)


def _search(status, **extra):
    return tiktok_task(status, task_id="s1", items_key="results", **extra)


# ---------------------------------------------------------------------------
# Profile scrape
# ---------------------------------------------------------------------------

def test_submit_tiktok_profile_scrape_returns_handle(client):
    raw = _profile_submit(webhook_url="https://example.com/hook")
    with patch.object(client, "_request", return_value=raw) as req:
        handle = client.submit_tiktok_profile_scrape(
            profile_url="https://www.tiktok.com/@tiktok",
            max_posts=10,
            after_datetime=date(2024, 1, 1),
            webhook_url="https://example.com/hook",
        )
    assert isinstance(handle, Job)
    assert handle.job_type == "tiktok_profile"
    assert handle.task_id == "p1"
    assert handle.webhook_url == "https://example.com/hook"
    assert handle.data.profile_url == "https://www.tiktok.com/@tiktok"
    req.assert_called_once_with(
        "POST",
        "/tiktok/profile",
        json_body={
            "profile_url": "https://www.tiktok.com/@tiktok",
            "max_posts": 10,
            "after_datetime": "2024-01-01",
            "webhook_url": "https://example.com/hook",
        },
    )


def test_submit_tiktok_profile_scrape_webhook_passthrough(client):
    with patch.object(client, "_request", return_value=_profile_submit()) as req:
        client.submit_tiktok_profile_scrape(profile_url="https://www.tiktok.com/@a")
        client.submit_tiktok_profile_scrape(profile_url="https://www.tiktok.com/@a", webhook_url="")
    first, second = req.call_args_list
    assert "webhook_url" not in first[1]["json_body"]
    assert second[1]["json_body"]["webhook_url"] == ""


def test_scrape_tiktok_profile_blocking(client, no_sleep):
    responses = [_profile_submit(), _profile("processing"), _profile("completed")]
    with patch.object(client, "_request", side_effect=responses) as req:
        resp = client.scrape_tiktok_profile(
            profile_url="https://www.tiktok.com/@tiktok", limit=10, include_usage=True,
        )
    assert isinstance(resp, TikTokProfileResponse)
    assert resp.data.is_completed
    assert req.call_args_list[0][0] == ("POST", "/tiktok/profile")
    assert req.call_args == (
        ("GET", "/tiktok/profile/p1"),
        {"params": {"limit": 10, "include_usage": "true"}},
    )


def test_profile_handle_result_with_cursor(client, no_sleep):
    handle = client.resume_job("tiktok_profile", "p1")
    with patch.object(client, "_request", return_value=_profile("completed")) as req:
        resp = handle.result(limit=5, cursor="abc")
    assert isinstance(resp, TikTokProfileResponse)
    req.assert_called_once_with("GET", "/tiktok/profile/p1", params={"limit": 5, "cursor": "abc"})


def test_profile_failure_reads_error_object(client, no_sleep):
    raw = _profile(
        "failed",
        error_message="Legacy text",
        error={"error": "invalid_url", "message": "Profile not found", "http_status": 400},
        webhook={"status": "delivered", "attempts": 1, "response_status": 200},
    )
    with patch.object(client, "_request", return_value=raw):
        handle = client.resume_job("tiktok_profile", "p1")
        with pytest.raises(BadRequestError, match="Profile not found") as exc_info:
            handle.result()
        failed = handle.wait(raise_on_failure=False)
    assert exc_info.value.error_code == "invalid_url"
    assert failed.data.webhook.status == "delivered"


def test_profile_failure_without_error_object_ignores_error_message(client, no_sleep):
    with patch.object(client, "_request", return_value=_profile("failed", error_message="boom")):
        with pytest.raises(VidNavigatorError) as exc_info:
            client.resume_job("tiktok_profile", "p1").result()
    assert "boom" not in str(exc_info.value)


def test_get_tiktok_profile_scrape_single_poll_still_available(client):
    with patch.object(client, "_request", return_value=_profile("processing")) as req:
        resp = client.get_tiktok_profile_scrape("p1", cursor="c", limit=20)
    assert resp.data.is_processing
    req.assert_called_once_with("GET", "/tiktok/profile/p1", params={"limit": 20, "cursor": "c"})


# ---------------------------------------------------------------------------
# Keyword search
# ---------------------------------------------------------------------------

def test_submit_tiktok_search_with_sort_window_and_webhook(client):
    raw = _search_submit(webhook_url="https://example.com/hook")
    with patch.object(client, "_request", return_value=raw) as req:
        handle = client.submit_tiktok_search(
            query="ai tools",
            sort_by="most_liked",
            published_within="this_week",
            webhook_url="https://example.com/hook",
        )
    assert handle.job_type == "tiktok_search"
    assert handle.webhook_url == "https://example.com/hook"
    assert handle.data.filters.sort_by == "most_liked"
    assert handle.data.filters.published_within == "this_week"
    req.assert_called_once_with(
        "POST",
        "/tiktok/search",
        json_body={
            "query": "ai tools",
            "sort_by": "most_liked",
            "published_within": "this_week",
            "webhook_url": "https://example.com/hook",
        },
    )


def test_submit_tiktok_search_omits_unset_params(client):
    with patch.object(client, "_request", return_value=_search_submit()) as req:
        client.submit_tiktok_search(query="ai tools")
    assert req.call_args[1]["json_body"] == {"query": "ai tools"}


def test_search_tiktok_blocking(client, no_sleep):
    responses = [_search_submit(), _search("processing"), _search("processing"), _search("completed",
                 stats={"pages_fetched": 3, "results_count": 60, "sort_by": "newest",
                        "published_within": "this_month"})]
    with patch.object(client, "_request", side_effect=responses) as req:
        resp = client.search_tiktok(query="ai tools", max_results=100, limit=5)
    assert isinstance(resp, TikTokSearchResponse)
    assert resp.data.stats.sort_by == "newest"
    assert resp.data.stats.published_within == "this_month"
    assert req.call_args_list[0][1]["json_body"] == {"query": "ai tools", "max_results": 100}
    assert req.call_args == (("GET", "/tiktok/search/s1"), {"params": {"limit": 5}})
    assert no_sleep.call_count == 2


def test_search_filters_echo_parses_nulls(client):
    raw = _search("completed", filters={"sort_by": None, "published_within": None,
                                        "after_datetime": "2026-09-01"})
    with patch.object(client, "_request", return_value=raw):
        resp = client.get_tiktok_search("s1")
    assert resp.data.filters.sort_by is None
    assert resp.data.filters.after_datetime == "2026-09-01"
    assert resp.data.error is None and resp.data.webhook is None


def test_submit_tiktok_search_country(client):
    raw = _search_submit()
    raw["data"]["country"] = "fr"
    with patch.object(client, "_request", return_value=raw) as req:
        handle = client.submit_tiktok_search(query="football", country="fr")
    assert handle.data.country == "fr"
    assert req.call_args[1]["json_body"] == {"query": "football", "country": "fr"}


def test_search_task_country_and_billing_stats(client):
    raw = _search("completed", country="fr", stats={
        "pages_fetched": "2", "videos_fetched": "58", "results_count": "41", "country": "fr",
        "parallel_search_slices": "2", "items_examined": "58", "items_filtered_out": "17",
        "items_deduplicated": "3"},
        webhook={"status": "delivered", "attempts": 1, "response_status": 200,
                 "last_error": None, "delivered_at": "2026-11-05T12:00:00+00:00"})
    with patch.object(client, "_request", return_value=raw):
        resp = client.get_tiktok_search("s1")
    stats = resp.data.stats
    assert resp.data.country == "fr" and stats.country == "fr"
    assert (stats.videos_fetched, stats.parallel_search_slices) == (58, 2)
    assert (stats.items_examined, stats.items_filtered_out, stats.items_deduplicated) == (58, 17, 3)
    assert resp.data.webhook.status == "delivered" and resp.data.webhook.attempts == 1


# ---------------------------------------------------------------------------
# LIVE search
# ---------------------------------------------------------------------------

LIVE_ROOM = {
    "id": "7704440240265644830",
    "title": "Ranked grind #fortnite #FYP",
    "url": "https://www.tiktok.com/@creator/live",
    "started_at": "2026-11-04T22:04:46Z",
    "author": {"id": "6628548115959152646", "unique_id": "creator", "nickname": "Creator",
               "sec_uid": "MS4wLjABAAAA", "followers": "576168", "avatar_url": "https://p16.example/a.webp"},
    "stats": {"viewers": "1296", "total_viewers": 232347, "likes": 301154, "comments": None, "shares": 360},
    "hashtags": ["fortnite", "FYP"],
    "category": "Gaming",
    "game_tags": ["Fortnite"],
    "cover_url": "https://p19.example/cover.webp",
    "stream_urls": {
        "default_quality": "hd",
        "flv": {"hd": "https://pull-f5.example/stream_hd.flv?expire=1795089584"},
        "hls": {"hd": "https://pull-hls.example/stream_hd/index.m3u8?expire=1795089584"},
        "audio_only": "https://pull-f5.example/stream.flv?expire=1795089584&only_audio=1",
        "expires_at": "2026-11-19T11:59:44Z",
    },
}


def _live_submit(**data):
    return {
        "status": "success",
        "data": {
            "task_id": "l1",
            "task_status": "processing",
            "query": "gaming",
            "country": "us",
            "max_results": 0,
            "include_stream_urls": True,
            "check_status_url": "/v1/tiktok/live/search/l1",
            "webhook_url": None,
            **data,
        },
    }


def _live(status, **extra):
    return tiktok_task(status, task_id="l1", items_key="results", **extra)


def test_submit_tiktok_live_search_returns_handle(client):
    raw = _live_submit(country="gb", max_results=20, include_stream_urls=False,
                       webhook_url="https://example.com/hook")
    with patch.object(client, "_request", return_value=raw) as req:
        handle = client.submit_tiktok_live_search(
            query="gaming", max_results=20, country="gb", include_stream_urls=False,
            webhook_url="https://example.com/hook",
        )
    assert isinstance(handle, Job)
    assert handle.job_type == "tiktok_live_search"
    assert handle.task_id == "l1"
    assert handle.data.country == "gb" and handle.data.include_stream_urls is False
    req.assert_called_once_with(
        "POST",
        "/tiktok/live/search",
        json_body={"query": "gaming", "max_results": 20, "country": "gb",
                   "include_stream_urls": False, "webhook_url": "https://example.com/hook"},
    )


def test_submit_tiktok_live_search_omits_unset_params(client):
    with patch.object(client, "_request", return_value=_live_submit()) as req:
        client.submit_tiktok_live_search(query="gaming")
    # Stream URLs are on by default server-side: nothing to send.
    assert req.call_args[1]["json_body"] == {"query": "gaming"}


def test_search_tiktok_live_blocking_parses_rooms(client, no_sleep):
    responses = [
        _live_submit(),
        _live("processing"),
        _live("completed", query="gaming", country="us", results=[LIVE_ROOM],
              stats={"pages_fetched": 1, "rooms_fetched": "44", "results_count": 44,
                     "has_more": False, "country": "us"},
              pagination={"limit": 10, "offset": 0, "total_items": 44, "has_next": True,
                          "has_prev": False, "next_cursor": "eyJvIjoxMH0="},
              webhook=None),
    ]
    with patch.object(client, "_request", side_effect=responses) as req:
        resp = client.search_tiktok_live(query="gaming", limit=10, include_usage=True)
    assert isinstance(resp, TikTokLiveSearchResponse)
    assert resp.data.is_completed and resp.data.country == "us"
    assert resp.data.stats.rooms_fetched == 44 and resp.data.stats.has_more is False
    room = resp.data.results[0]
    assert room.id == "7704440240265644830"
    assert room.started_at.isoformat() == "2026-11-04T22:04:46+00:00"
    assert room.author.followers == 576168 and room.author.sec_uid == "MS4wLjABAAAA"
    assert room.stats.viewers == 1296 and room.stats.comments is None
    assert room.hashtags == ["fortnite", "FYP"] and room.category == "Gaming"
    assert room.game_tags == ["Fortnite"]
    assert room.stream_urls.default_quality == "hd"
    assert room.stream_urls.flv["hd"].endswith("expire=1795089584")
    assert room.stream_urls.hls["hd"].endswith("expire=1795089584")
    assert "only_audio=1" in room.stream_urls.audio_only
    assert room.stream_urls.expires_at.isoformat() == "2026-11-19T11:59:44+00:00"
    assert resp.data.pagination.next_cursor == "eyJvIjoxMH0="
    assert req.call_args_list[0] == (("POST", "/tiktok/live/search"), {"json_body": {"query": "gaming"}})
    assert req.call_args == (
        ("GET", "/tiktok/live/search/l1"),
        {"params": {"limit": 10, "include_usage": "true"}},
    )


def test_live_room_without_stream_urls(client):
    room = {k: v for k, v in LIVE_ROOM.items() if k != "stream_urls"}
    with patch.object(client, "_request", return_value=_live("completed", results=[room])):
        resp = client.get_tiktok_live_search("l1")
    assert resp.data.results[0].stream_urls is None


def test_live_room_with_empty_hls(client):
    room = {**LIVE_ROOM, "stream_urls": {**LIVE_ROOM["stream_urls"], "hls": {}}}
    with patch.object(client, "_request", return_value=_live("completed", results=[room])):
        resp = client.get_tiktok_live_search("l1")
    assert resp.data.results[0].stream_urls.hls == {}


def test_get_tiktok_live_search_page(client):
    with patch.object(client, "_request", return_value=_live("completed")) as req:
        resp = client.get_tiktok_live_search("l1", cursor="abc", limit=25)
    assert isinstance(resp, TikTokLiveSearchResponse)
    req.assert_called_once_with("GET", "/tiktok/live/search/l1", params={"limit": 25, "cursor": "abc"})


def test_live_search_resume_and_failure(client, no_sleep):
    raw = _live("failed", error={"error": "search_failed", "message": "TikTok LIVE search failed.",
                                 "http_status": 502})
    with patch.object(client, "_request", return_value=raw) as req:
        handle = client.resume_job("tiktok_live_search", "l1")
        with pytest.raises(VidNavigatorError, match="TikTok LIVE search failed") as exc_info:
            handle.result()
    assert exc_info.value.error_code == "search_failed"
    assert req.call_args[0] == ("GET", "/tiktok/live/search/l1")


# ---------------------------------------------------------------------------
# Every page by default, and operation objects (parity with the JS SDK)
# ---------------------------------------------------------------------------

def _page(status, ids, next_cursor=None, **extra):
    return _search(
        status,
        results=[{"id": i, "url": f"https://www.tiktok.com/@c/video/{i}"} for i in ids],
        pagination={"limit": 500, "offset": 0, "total_items": 3, "has_next": next_cursor is not None,
                    "has_prev": False, "next_cursor": next_cursor},
        **extra,
    )


def test_search_tiktok_collects_every_page_by_default(client, no_sleep):
    responses = [
        _search_submit(),
        _page("processing", []),
        _page("completed", ["a"], next_cursor="c1"),
        _page("completed", ["a", "b"], next_cursor="c1"),
        _page("completed", ["c"]),
    ]
    with patch.object(client, "_request", side_effect=responses) as req:
        resp = client.search_tiktok(query="ai tools", include_usage=True)
    assert [r.id for r in resp.data.results] == ["a", "b", "c"]
    assert resp.data.pagination.has_next is False and resp.data.pagination.next_cursor is None
    assert resp.data.pagination.limit == 3
    gets = [c for c in req.call_args_list if c[0][0] == "GET"]
    # Status polls ask for one item; usage comes with the first full page only.
    assert [c[1]["params"] for c in gets] == [
        {"limit": 1},
        {"limit": 1},
        {"limit": 500, "include_usage": "true"},
        {"limit": 500, "cursor": "c1"},
    ]


def test_explicit_limit_still_returns_one_page(client, no_sleep):
    responses = [_search_submit(), _page("completed", ["a", "b"], next_cursor="c1")]
    with patch.object(client, "_request", side_effect=responses) as req:
        resp = client.search_tiktok(query="ai tools", limit=2)
    assert [r.id for r in resp.data.results] == ["a", "b"]
    assert resp.data.pagination.next_cursor == "c1"
    assert req.call_args == (("GET", "/tiktok/search/s1"), {"params": {"limit": 2}})


def test_profile_handle_result_collects_videos(client, no_sleep):
    pages = [
        _profile("completed", videos=[{"id": "1"}], pagination={"has_next": True, "next_cursor": "x"}),
        _profile("completed", videos=[{"id": "1"}], pagination={"has_next": True, "next_cursor": "x"}),
        _profile("completed", videos=[{"id": "2"}], pagination={"has_next": False, "next_cursor": None}),
    ]
    with patch.object(client, "_request", side_effect=pages):
        resp = client.resume_job("tiktok_profile", "p1").result()
    assert [v.id for v in resp.data.videos] == ["1", "2"]


def test_operation_objects_match_the_methods(client, no_sleep):
    expected = {
        "transcribe": "transcribe", "extract_video": "extract_video", "tweet_statement": "tweet_statement",
        "tiktok_profile": "tiktok_profile", "tiktok_search": "tiktok_search",
        "tiktok_live_search": "tiktok_live_search",
    }
    for attr, job_type in expected.items():
        op = getattr(client, attr)
        assert callable(op) and callable(op.submit) and callable(op.resume), attr
        assert op.job_type == job_type
        assert repr(op) == f"Operation(job_type={job_type!r})"
        resumed = op.resume("t1")
        assert isinstance(resumed, Job) and resumed.job_type == job_type and resumed.task_id == "t1"

    with patch.object(client, "_request", return_value=_search_submit()) as req:
        handle = client.tiktok_search.submit(query="ai tools", country="fr")
    assert isinstance(handle, Job) and handle.job_type == "tiktok_search" and handle.task_id == "s1"
    assert req.call_args[1]["json_body"] == {"query": "ai tools", "country": "fr"}

    responses = [_live_submit(), _live("completed", results=[LIVE_ROOM]), _live("completed", results=[LIVE_ROOM])]
    with patch.object(client, "_request", side_effect=responses) as req:
        resp = client.tiktok_live_search(query="gaming")
    assert isinstance(resp, TikTokLiveSearchResponse) and resp.data.results[0].category == "Gaming"
    assert req.call_args_list[0] == (("POST", "/tiktok/live/search"), {"json_body": {"query": "gaming"}})
