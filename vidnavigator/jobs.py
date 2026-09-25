"""Handles for VidNavigator background jobs.

Every speech-to-text and TikTok operation runs as a background job: submitting
returns a ``task_id`` immediately and the result is read by polling. An
:class:`AsyncJob` wraps one such job.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Dict, Optional

from .exceptions import AsyncJobTimeoutError, VidNavigatorError
from . import models

if TYPE_CHECKING:  # pragma: no cover
    from .client import VidNavigatorClient

# Polling is free and not rate-limited: poll quickly at first so short clips
# return fast, then settle into a steady interval.
POLL_INTERVAL = 3.0
FAST_POLL_INTERVAL = 1.0
FAST_POLL_WINDOW = 10.0
DEFAULT_JOB_TIMEOUT = 3600.0

TERMINAL_STATUSES = ("completed", "failed")

# job_type -> (poll route prefix, poll response model)
JOB_ROUTES = {
    "transcribe": ("/transcribe", models.TranscribeJobResponse),
    "extract_video": ("/extract/video", models.ExtractVideoJobResponse),
    "tweet_statement": ("/tweet/statement", models.TweetStatementJobResponse),
    "tiktok_profile": ("/tiktok/profile", models.TikTokProfileResponse),
    "tiktok_search": ("/tiktok/search", models.TikTokSearchResponse),
}


def _completed_result(resp: Any) -> Any:
    result = resp.data.result
    if result is None:
        raise VidNavigatorError(f"Job {resp.data.task_id} completed without a result")
    return result


def _finalize(job_type: str, resp: Any) -> Any:
    """Turn a completed poll response into the operation's result object."""
    if job_type == "transcribe":
        result = _completed_result(resp)
        if isinstance(result, models.TranscribeAllVideosData):
            return models.TranscribeAllVideosResponse(
                status=resp.status, data=result, usage=resp.usage
            )
        return models.TranscriptResponse(status=resp.status, data=result, usage=resp.usage)
    if job_type == "extract_video":
        return models.ExtractionApiResponse(
            status=resp.status, data=_completed_result(resp), usage=resp.usage
        )
    if job_type == "tweet_statement":
        return models.TweetStatementResponse(
            status=resp.status, data=_completed_result(resp), usage=resp.usage
        )
    # TikTok: the poll response itself is the (first page of the) result.
    return resp


class AsyncJob:
    """A background job on the VidNavigator API.

    Obtain one from a ``submit_*`` method, or rebuild one from a saved id with
    :meth:`VidNavigatorClient.resume_job`. Keep :attr:`task_id`: the job keeps
    running server-side even if your process stops waiting, and its result
    stays readable for 1 hour after it finishes.
    """

    def __init__(
        self,
        client: "VidNavigatorClient",
        job_type: str,
        task_id: str,
        *,
        submit_response: Any = None,
    ) -> None:
        if job_type not in JOB_ROUTES:
            raise ValueError(
                f"Unknown job_type {job_type!r}; expected one of {sorted(JOB_ROUTES)}"
            )
        if not task_id:
            raise ValueError("task_id is required")
        self._client = client
        self.job_type = job_type
        self.task_id = task_id
        self.submit_response = submit_response
        self.last_response: Any = None

    def __repr__(self) -> str:
        return f"AsyncJob(job_type={self.job_type!r}, task_id={self.task_id!r})"

    # -- Submit-time metadata -------------------------------------------------
    @property
    def data(self) -> Any:
        """The ``data`` block of the submit (``202``) response, if this handle came from a submit."""
        return self.submit_response.data if self.submit_response is not None else None

    @property
    def check_status_url(self) -> Optional[str]:
        return getattr(self.data, "check_status_url", None)

    @property
    def webhook_url(self) -> Optional[str]:
        """The webhook this job reports to, as echoed by the API (``None`` if none applies)."""
        return getattr(self.data, "webhook_url", None)

    # -- Polling --------------------------------------------------------------
    def refresh(self, *, include_usage: bool = False, **params: Any) -> Any:
        """Fetch the job once and return the typed poll response.

        Extra keyword arguments are sent as query parameters (TikTok jobs accept
        ``limit`` and ``cursor``).
        """
        path, model_cls = JOB_ROUTES[self.job_type]
        query: Dict[str, Any] = {k: v for k, v in params.items() if v is not None}
        if include_usage:
            query["include_usage"] = "true"
        raw = self._client._request("GET", f"{path}/{self.task_id}", params=query or None)
        from .client import _parse_model

        self.last_response = _parse_model(model_cls, raw)
        return self.last_response

    def status(self) -> str:
        """Fetch the job once and return its ``task_status``."""
        return self.refresh().data.task_status

    def done(self) -> bool:
        """Fetch the job once and report whether it reached ``completed`` or ``failed``."""
        return self.status() in TERMINAL_STATUSES

    def wait(
        self,
        *,
        timeout: Optional[float] = DEFAULT_JOB_TIMEOUT,
        include_usage: bool = False,
        poll_interval: float = POLL_INTERVAL,
        fast_start: bool = True,
        raise_on_failure: bool = True,
        **params: Any,
    ) -> Any:
        """Poll until the job finishes and return the final typed poll response.

        Polls every ``poll_interval`` seconds (every second for the first 10
        seconds when ``fast_start`` is on). If the job failed, raises the
        exception matching its ``error`` object unless ``raise_on_failure`` is
        False. If ``timeout`` seconds pass first, raises
        :class:`~vidnavigator.AsyncJobTimeoutError` carrying this job's
        ``task_id``; pass ``timeout=None`` to wait indefinitely.
        """
        start = time.monotonic()
        deadline = None if timeout is None else start + timeout
        resp = self.refresh(include_usage=include_usage, **params)
        while resp.data.task_status not in TERMINAL_STATUSES:
            now = time.monotonic()
            use_fast = fast_start and now - start < FAST_POLL_WINDOW
            delay = min(poll_interval, FAST_POLL_INTERVAL) if use_fast else poll_interval
            if deadline is not None:
                remaining = deadline - now
                if remaining <= 0:
                    raise AsyncJobTimeoutError(
                        f"{self.job_type} job {self.task_id} still "
                        f"{resp.data.task_status!r} after {timeout}s; it keeps running "
                        f"server-side, resume it with this task_id",
                        task_id=self.task_id,
                        job=self,
                    )
                delay = min(delay, remaining)
            time.sleep(delay)
            resp = self.refresh(include_usage=include_usage, **params)
        if raise_on_failure:
            resp.data.raise_for_error()
        return resp

    def result(
        self,
        *,
        timeout: Optional[float] = DEFAULT_JOB_TIMEOUT,
        include_usage: bool = False,
        poll_interval: float = POLL_INTERVAL,
        fast_start: bool = True,
        **params: Any,
    ) -> Any:
        """Wait for the job and return its result, raising if it failed.

        Returns the same object as the matching blocking method, e.g. a
        :class:`~vidnavigator.models.TranscriptResponse` for a transcription.
        """
        resp = self.wait(
            timeout=timeout,
            include_usage=include_usage,
            poll_interval=poll_interval,
            fast_start=fast_start,
            **params,
        )
        return _finalize(self.job_type, resp)
