"""Payload builders shared by the mocked unit tests."""


def accepted(job_type, task_id="task_1", webhook_url=None, **extra):
    """A 202 submit response."""
    return {
        "status": "success",
        "data": {
            "task_id": task_id,
            "task_status": "processing",
            "job_type": job_type,
            "expires_at": "2026-09-25T16:41:11.793711+00:00",
            "check_status_url": f"/v1/{job_type}/{task_id}",
            "webhook_url": webhook_url,
            "message": "Job started. Poll check_status_url for the result.",
            "docs_url": "https://docs.vidnavigator.com/guides/async-jobs",
            **extra,
        },
    }


def job(job_type, status, result=None, error=None, usage=None, webhook=None, task_id="task_1"):
    """A GET poll response for transcribe / extract_video / tweet_statement jobs."""
    raw = {
        "status": "success",
        "data": {
            "task_id": task_id,
            "task_status": status,
            "job_type": job_type,
            "request": {"video_url": "https://example.com/v"},
            "created_at": "2026-09-25T15:41:11.793000",
            "started_at": "2026-09-25T15:41:11.797000",
            "completed_at": None if status == "processing" else "2026-09-25T15:41:13.565000",
            "expires_at": "2026-09-25T16:41:13.565000",
            "check_status_url": f"/v1/{job_type}/{task_id}",
            "webhook": webhook,
        },
    }
    if result is not None:
        raw["data"]["result"] = result
    if error is not None:
        raw["data"]["error"] = error
    if usage is not None:
        raw["usage"] = usage
    return raw


def tiktok_task(status, task_id="p1", items_key="videos", **extra):
    """A GET poll response for TikTok profile (``videos``) or search (``results``) tasks."""
    return {
        "status": "success",
        "data": {"task_id": task_id, "task_status": status, items_key: [], **extra},
    }


def partial_youtube_search():
    """The 402 /youtube/search sends when credits run out after some videos were analysed."""
    return {
        "status": "partial",
        "error_code": "insufficient_credits_video_search",
        "message": "Credits ran out during video analysis. Returning partial results.",
        "data": {
            "results": [{"title": "R1", "url": "https://www.youtube.com/watch?v=abc", "relevance_score": 0.9}],
            "query": "q",
            "total_found": 1,
            "explanation": "Partial results — credit limit reached during analysis.",
        },
        "usage": {
            "charges": [{"service_type": "residential_request", "quantity": 1, "credits": 1}],
            "total_credits": 1,
            "credits_remaining_after": 0,
        },
    }


# The 402 /youtube/search sends when the search could not start for lack of credits.
YOUTUBE_SEARCH_NO_CREDITS = {
    "status": "error",
    "error": "insufficient_credits",
    "error_code": "insufficient_credits",
    "message": "Not enough credits.",
}
