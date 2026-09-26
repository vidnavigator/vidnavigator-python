"""Unit tests for TikTok jobs: handles, blocking calls, webhook pass-through, filters."""

from datetime import date
from unittest.mock import patch

import pytest

from vidnavigator import Job, BadRequestError, VidNavigatorClient, VidNavigatorError
from vidnavigator.models import TikTokProfileResponse, TikTokSearchResponse

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
