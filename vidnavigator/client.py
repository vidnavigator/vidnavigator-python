"""VidNavigator Developer API Python client."""

from __future__ import annotations

import json
import mimetypes
import os
import warnings
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union
import requests

from .exceptions import (
    AuthenticationError,
    VidNavigatorError,
    error_from_response,
)
from .jobs import DEFAULT_JOB_TIMEOUT, AsyncJob
from . import models


DEFAULT_BASE_URL = "https://api.vidnavigator.com/v1"
USER_AGENT = "vidnavigator-python/2.0.0"


def _parse_model(model_cls: Any, raw: Any) -> Any:
    """Parse JSON dict into a Pydantic model (v1: parse_obj, v2: model_validate)."""
    if hasattr(model_cls, "model_validate"):
        return model_cls.model_validate(raw)
    return model_cls.parse_obj(raw)


def _format_datetime(value: Union[str, date, datetime]) -> str:
    """Serialize TikTok profile date/datetime filters."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _guess_schema_content_type(file_path: str) -> str:
    """Return a stable content type for uploaded JSON/YAML schema files."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in {".yaml", ".yml"}:
        return "application/yaml"
    if ext == ".json":
        return "application/json"
    return mimetypes.guess_type(file_path)[0] or "application/octet-stream"


class VidNavigatorClient:
    """Client for interacting with the VidNavigator Developer API.

    Parameters
    ----------
    api_key:
        Your VidNavigator API key. This is sent via the *X-API-Key* header.
    base_url:
        Override the default API base URL (useful for testing/staging).
    timeout:
        Request timeout (seconds).
    session:
        Optional *requests.Session* to use. If *None*, a new session is created.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int | float = 30,
        session: Optional[requests.Session] = None,
    ) -> None:
        api_key = api_key or os.getenv("VIDNAVIGATOR_API_KEY")
        if not api_key:
            raise AuthenticationError(
                "API key was not provided. Pass it explicitly or set the VIDNAVIGATOR_API_KEY env var."
            )

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "X-API-Key": api_key,
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            }
        )

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------
    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        files: Any = None,
        stream: bool = False,
    ) -> Any:
        body = json_body
        url = f"{self.base_url}{path}"

        try:
            response = self.session.request(
                method,
                url,
                params=params,
                json=body,
                data=data,
                files=files,
                timeout=self.timeout,
                stream=stream,
            )
        except requests.RequestException as exc:
            raise VidNavigatorError(f"Request failed: {exc}") from exc

        if stream:
            return response

        try:
            payload = response.json()
        except ValueError:
            payload = {"status": "error", "message": response.text}

        if response.ok:
            return payload

        if not isinstance(payload, dict):
            payload = {"status": "error", "message": str(payload)}
        raise error_from_response(response.status_code, payload, reason=response.reason)

    def _job_from_submit(self, job_type: str, model_cls: Any, raw: Any) -> AsyncJob:
        submitted = _parse_model(model_cls, raw)
        task_id = submitted.data.task_id if submitted.data is not None else None
        if not task_id:
            raise VidNavigatorError(f"{job_type} submit response did not include a task_id")
        return AsyncJob(self, job_type, task_id, submit_response=submitted)

    # ---------------------------------------------------------------------
    # Background jobs
    # ---------------------------------------------------------------------

    def resume_job(self, job_type: str, task_id: str) -> AsyncJob:
        """Rebuild the handle of a job submitted earlier from its ``task_id``.

        *job_type* is one of ``"transcribe"``, ``"extract_video"``,
        ``"tweet_statement"``, ``"tiktok_profile"`` or ``"tiktok_search"``.
        Use it after an :class:`~vidnavigator.AsyncJobTimeoutError`, a restart,
        or a webhook delivery. Results stay readable for 1 hour after the job
        finishes.
        """
        return AsyncJob(self, job_type, task_id)

    # ---------------------------------------------------------------------
    # Public API methods
    # ---------------------------------------------------------------------

    # Transcripts ------------------------------------------------------------------
    def get_transcript(
        self,
        *,
        video_url: str,
        language: Optional[str] = None,
        metadata_only: bool = False,
        fallback_to_metadata: bool = False,
        transcript_text: bool = False,
        include_usage: bool = False,
    ) -> models.TranscriptResponse:
        """Extract a transcript from any supported online video.

        The endpoint auto-detects the platform from *video_url* (YouTube, Vimeo,
        X/Twitter, TikTok, Facebook, Dailymotion, Loom, etc.). For Instagram, use
        :meth:`transcribe_video` (speech-to-text) instead.

        Set *include_usage* to receive a per-call ``usage`` block on the response.
        """
        payload: Dict[str, Any] = {
            "video_url": video_url,
            "metadata_only": metadata_only,
            "fallback_to_metadata": fallback_to_metadata,
            "transcript_text": transcript_text,
            "include_usage": include_usage,
        }
        if language:
            payload["language"] = language
        raw = self._request("POST", "/transcript", json_body=payload)
        return _parse_model(models.TranscriptResponse, raw)

    def get_youtube_transcript(
        self,
        *,
        video_url: str,
        language: Optional[str] = None,
        metadata_only: bool = False,
        fallback_to_metadata: bool = False,
        transcript_text: bool = False,
        include_usage: bool = False,
    ) -> models.TranscriptResponse:
        """Deprecated alias for :meth:`get_transcript`.

        The API now exposes a single ``/transcript`` endpoint that auto-detects
        YouTube URLs, so this simply forwards to :meth:`get_transcript`.
        """
        warnings.warn(
            "get_youtube_transcript() is deprecated; use get_transcript() instead. "
            "The API now has a single /transcript endpoint that auto-detects YouTube.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.get_transcript(
            video_url=video_url,
            language=language,
            metadata_only=metadata_only,
            fallback_to_metadata=fallback_to_metadata,
            transcript_text=transcript_text,
            include_usage=include_usage,
        )

    def submit_transcribe_video(
        self,
        *,
        video_url: str,
        transcript_text: bool = False,
        all_videos: bool = False,
        webhook_url: Optional[str] = None,
    ) -> AsyncJob:
        """Start a speech-to-text transcription job and return its handle immediately.

        Call ``.result()`` on the handle to wait for a
        :class:`~vidnavigator.models.TranscriptResponse` (or
        :class:`~vidnavigator.models.TranscribeAllVideosResponse` when
        *all_videos* is True), or ``.status()`` to check on it.

        *webhook_url* is passed through to the API: it overrides your
        account-level default webhook, and ``""`` opts this job out of it.
        Polling works whether or not a webhook is configured.
        """
        payload: Dict[str, Any] = {
            "video_url": video_url,
            "transcript_text": transcript_text,
            "all_videos": all_videos,
        }
        if webhook_url is not None:
            payload["webhook_url"] = webhook_url
        raw = self._request("POST", "/transcribe/async", json_body=payload)
        return self._job_from_submit("transcribe", models.AsyncJobSubmitResponse, raw)

    def transcribe_video(
        self,
        *,
        video_url: str,
        transcript_text: bool = False,
        all_videos: bool = False,
        include_usage: bool = False,
        webhook_url: Optional[str] = None,
        timeout: Optional[float] = DEFAULT_JOB_TIMEOUT,
    ) -> Union[models.TranscriptResponse, models.TranscribeAllVideosResponse]:
        """Transcribe an online video using speech-to-text and wait for the result.

        Runs as a background job (``POST /transcribe/async`` then polling), so
        long media is not subject to the synchronous endpoint's duration limit.
        When *all_videos* is True (carousel posts), the response includes
        *carousel_info* and *videos* instead of a single *video_info*.

        Raises :class:`~vidnavigator.AsyncJobTimeoutError` (carrying the
        ``task_id``) if the job is still running after *timeout* seconds.
        """
        job = self.submit_transcribe_video(
            video_url=video_url,
            transcript_text=transcript_text,
            all_videos=all_videos,
            webhook_url=webhook_url,
        )
        return job.result(timeout=timeout, include_usage=include_usage)

    # Files ------------------------------------------------------------------------
    def get_files(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        namespace_id: Optional[str] = None,
    ) -> models.FilesListResponse:
        """Retrieve a paginated list of uploaded files.

        Parameters
        ----------
        namespace_id:
            Filter by namespace. Only files in this namespace are returned.
        """
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        if namespace_id is not None:
            params["namespace_id"] = namespace_id
        raw = self._request("GET", "/files", params=params)
        return _parse_model(models.FilesListResponse, raw)

    def get_file(
        self,
        file_id: str,
        *,
        transcript_text: bool = False,
    ) -> models.FileResponse:
        """Retrieve details (and transcript) for a specific file."""
        params: Optional[Dict[str, Any]] = None
        if transcript_text:
            params = {"transcript_text": "true"}
        raw = self._request("GET", f"/file/{file_id}", params=params)
        return _parse_model(models.FileResponse, raw)

    # Analysis ---------------------------------------------------------------------
    def analyze_video(
        self,
        *,
        video_url: str,
        query: Optional[str] = None,
        transcript_text: bool = False,
        include_usage: bool = False,
    ) -> models.AnalysisResponse:
        payload: Dict[str, Any] = {
            "video_url": video_url,
            "transcript_text": transcript_text,
            "include_usage": include_usage,
        }
        if query:
            payload["query"] = query
        raw = self._request("POST", "/analyze/video", json_body=payload)
        return _parse_model(models.AnalysisResponse, raw)

    def analyze_file(
        self,
        *,
        file_id: str,
        query: Optional[str] = None,
        transcript_text: bool = False,
        include_usage: bool = False,
    ) -> models.AnalysisResponse:
        payload: Dict[str, Any] = {
            "file_id": file_id,
            "transcript_text": transcript_text,
            "include_usage": include_usage,
        }
        if query:
            payload["query"] = query
        raw = self._request("POST", "/analyze/file", json_body=payload)
        return _parse_model(models.AnalysisResponse, raw)

    # Extraction -------------------------------------------------------------------
    def submit_extract_video_data(
        self,
        *,
        video_url: str,
        schema: Optional[Dict[str, Any]] = None,
        schema_file: Optional[str] = None,
        what_to_extract: Optional[str] = None,
        transcribe: bool = True,
        webhook_url: Optional[str] = None,
    ) -> AsyncJob:
        """Start a structured-data extraction job and return its handle immediately.

        Pass ``schema`` to send a JSON request body, or ``schema_file`` to upload a
        JSON/YAML schema file as multipart/form-data. The schema is validated at
        submit time, so an invalid one raises before anything is billed.
        ``.result()`` on the handle returns an
        :class:`~vidnavigator.models.ExtractionApiResponse`.
        """
        raw = self._post_extract_video(
            "/extract/video/async",
            {
                "video_url": video_url,
                "transcribe": transcribe,
                "what_to_extract": what_to_extract,
                "webhook_url": webhook_url,
            },
            schema=schema,
            schema_file=schema_file,
        )
        return self._job_from_submit("extract_video", models.AsyncJobSubmitResponse, raw)

    def extract_video_data(
        self,
        *,
        video_url: str,
        schema: Optional[Dict[str, Any]] = None,
        schema_file: Optional[str] = None,
        what_to_extract: Optional[str] = None,
        transcribe: bool = True,
        include_usage: bool = False,
        webhook_url: Optional[str] = None,
        timeout: Optional[float] = DEFAULT_JOB_TIMEOUT,
    ) -> models.ExtractionApiResponse:
        """Extract structured data from an online video transcript and wait for the result.

        Runs as a background job (``POST /extract/video/async`` then polling).
        The extracted fields are in ``.data``. ``.video_info`` is not populated,
        because job results carry only the extracted data.
        """
        job = self.submit_extract_video_data(
            video_url=video_url,
            schema=schema,
            schema_file=schema_file,
            what_to_extract=what_to_extract,
            transcribe=transcribe,
            webhook_url=webhook_url,
        )
        return job.result(timeout=timeout, include_usage=include_usage)

    def _post_extract_video(
        self,
        path: str,
        fields: Dict[str, Any],
        *,
        schema: Optional[Dict[str, Any]],
        schema_file: Optional[str],
    ) -> Any:
        """POST an extract/video request as JSON, or multipart when *schema_file* is set.

        ``None`` values in *fields* are omitted.
        """
        if (schema is None) == (schema_file is None):
            raise ValueError("Pass exactly one of schema or schema_file.")
        fields = {k: v for k, v in fields.items() if v is not None}

        if schema_file is not None:
            if not os.path.isfile(schema_file):
                raise FileNotFoundError(schema_file)
            data = {
                k: ("true" if v else "false") if isinstance(v, bool) else v
                for k, v in fields.items()
            }
            filename = os.path.basename(schema_file)
            content_type = _guess_schema_content_type(schema_file)
            with open(schema_file, "rb") as fp:
                files = {"schema": (filename, fp, content_type)}
                return self._request("POST", path, data=data, files=files)

        return self._request("POST", path, json_body={**fields, "schema": schema})

    # TikTok -----------------------------------------------------------------------
    def submit_tiktok_profile_scrape(
        self,
        *,
        profile_url: str,
        max_posts: Optional[int] = None,
        after_datetime: Optional[Union[str, date, datetime]] = None,
        before_datetime: Optional[Union[str, date, datetime]] = None,
        min_likes: Optional[int] = None,
        max_likes: Optional[int] = None,
        webhook_url: Optional[str] = None,
    ) -> AsyncJob:
        """Start a TikTok profile scrape job and return its handle immediately.

        Datetime filters must be YYYY-MM-DD strings or ISO format with timezone.
        ``date`` and ``datetime`` values are accepted and serialized automatically.

        ``.result(limit=..., cursor=...)`` on the handle waits and returns a
        :class:`~vidnavigator.models.TikTokProfileResponse` page; page further
        with :meth:`get_tiktok_profile_scrape`. *webhook_url* is passed through
        (``""`` opts out of your account default); the event carries ``stats``
        only.
        """
        payload: Dict[str, Any] = {"profile_url": profile_url}
        if max_posts is not None:
            payload["max_posts"] = max_posts
        if after_datetime is not None:
            payload["after_datetime"] = _format_datetime(after_datetime)
        if before_datetime is not None:
            payload["before_datetime"] = _format_datetime(before_datetime)
        if min_likes is not None:
            payload["min_likes"] = min_likes
        if max_likes is not None:
            payload["max_likes"] = max_likes
        if webhook_url is not None:
            payload["webhook_url"] = webhook_url
        raw = self._request("POST", "/tiktok/profile", json_body=payload)
        return self._job_from_submit("tiktok_profile", models.TikTokProfileSubmitResponse, raw)

    def scrape_tiktok_profile(
        self,
        *,
        profile_url: str,
        max_posts: Optional[int] = None,
        after_datetime: Optional[Union[str, date, datetime]] = None,
        before_datetime: Optional[Union[str, date, datetime]] = None,
        min_likes: Optional[int] = None,
        max_likes: Optional[int] = None,
        webhook_url: Optional[str] = None,
        limit: int = 50,
        include_usage: bool = False,
        timeout: Optional[float] = DEFAULT_JOB_TIMEOUT,
    ) -> models.TikTokProfileResponse:
        """Scrape a TikTok profile and wait for the first page of *limit* videos.

        Page further with :meth:`get_tiktok_profile_scrape` using
        ``response.data.task_id`` and ``response.data.pagination.next_cursor``.
        """
        job = self.submit_tiktok_profile_scrape(
            profile_url=profile_url,
            max_posts=max_posts,
            after_datetime=after_datetime,
            before_datetime=before_datetime,
            min_likes=min_likes,
            max_likes=max_likes,
            webhook_url=webhook_url,
        )
        return job.result(timeout=timeout, include_usage=include_usage, limit=limit)

    def get_tiktok_profile_scrape(
        self,
        task_id: str,
        *,
        cursor: Optional[str] = None,
        limit: int = 50,
        include_usage: bool = False,
    ) -> models.TikTokProfileResponse:
        """Fetch a TikTok profile scrape task once and retrieve a page of videos.

        Set *include_usage* to receive a ``usage`` block (only populated once the
        task is ``completed``). Polling itself is free.
        """
        params: Dict[str, Any] = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        if include_usage:
            params["include_usage"] = "true"
        raw = self._request("GET", f"/tiktok/profile/{task_id}", params=params)
        return _parse_model(models.TikTokProfileResponse, raw)

    def submit_tiktok_search(
        self,
        *,
        query: str,
        max_results: Optional[int] = None,
        parallel_search_slices: Optional[int] = None,
        sort_by: Optional[str] = None,
        published_within: Optional[str] = None,
        after_datetime: Optional[Union[str, date, datetime]] = None,
        before_datetime: Optional[Union[str, date, datetime]] = None,
        min_likes: Optional[int] = None,
        max_likes: Optional[int] = None,
        min_views: Optional[int] = None,
        max_views: Optional[int] = None,
        webhook_url: Optional[str] = None,
    ) -> AsyncJob:
        """Start a TikTok keyword search job and return its handle immediately.

        Parameters
        ----------
        sort_by:
            ``"relevance"``, ``"most_liked"`` or ``"newest"`` (applied by TikTok).
            When omitted, results come back newest first.
        published_within:
            ``"all"``, ``"past_24_hours"``, ``"this_week"``, ``"this_month"``,
            ``"last_3_months"`` or ``"last_6_months"`` (rolling windows).
        webhook_url:
            Passed through to the API (``""`` opts out of your account
            default). The event carries ``stats`` only.
        """
        payload: Dict[str, Any] = {"query": query}
        if max_results is not None:
            payload["max_results"] = max_results
        if parallel_search_slices is not None:
            payload["parallel_search_slices"] = parallel_search_slices
        if sort_by is not None:
            payload["sort_by"] = sort_by
        if published_within is not None:
            payload["published_within"] = published_within
        if after_datetime is not None:
            payload["after_datetime"] = _format_datetime(after_datetime)
        if before_datetime is not None:
            payload["before_datetime"] = _format_datetime(before_datetime)
        if min_likes is not None:
            payload["min_likes"] = min_likes
        if max_likes is not None:
            payload["max_likes"] = max_likes
        if min_views is not None:
            payload["min_views"] = min_views
        if max_views is not None:
            payload["max_views"] = max_views
        if webhook_url is not None:
            payload["webhook_url"] = webhook_url
        raw = self._request("POST", "/tiktok/search", json_body=payload)
        return self._job_from_submit("tiktok_search", models.TikTokSearchSubmitResponse, raw)

    def search_tiktok(
        self,
        *,
        query: str,
        max_results: Optional[int] = None,
        parallel_search_slices: Optional[int] = None,
        sort_by: Optional[str] = None,
        published_within: Optional[str] = None,
        after_datetime: Optional[Union[str, date, datetime]] = None,
        before_datetime: Optional[Union[str, date, datetime]] = None,
        min_likes: Optional[int] = None,
        max_likes: Optional[int] = None,
        min_views: Optional[int] = None,
        max_views: Optional[int] = None,
        webhook_url: Optional[str] = None,
        limit: int = 50,
        include_usage: bool = False,
        timeout: Optional[float] = DEFAULT_JOB_TIMEOUT,
    ) -> models.TikTokSearchResponse:
        """Run a TikTok keyword search and wait for the first page of *limit* results.

        Page further with :meth:`get_tiktok_search`. See
        :meth:`submit_tiktok_search` for the parameters.
        """
        job = self.submit_tiktok_search(
            query=query,
            max_results=max_results,
            parallel_search_slices=parallel_search_slices,
            sort_by=sort_by,
            published_within=published_within,
            after_datetime=after_datetime,
            before_datetime=before_datetime,
            min_likes=min_likes,
            max_likes=max_likes,
            min_views=min_views,
            max_views=max_views,
            webhook_url=webhook_url,
        )
        return job.result(timeout=timeout, include_usage=include_usage, limit=limit)

    def get_tiktok_search(
        self,
        task_id: str,
        *,
        cursor: Optional[str] = None,
        limit: int = 50,
        include_usage: bool = False,
    ) -> models.TikTokSearchResponse:
        """Fetch a TikTok keyword search task once and retrieve a page of results.

        Set *include_usage* to receive a ``usage`` block (only populated once the
        task is ``completed``). Polling itself is free.
        """
        params: Dict[str, Any] = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        if include_usage:
            params["include_usage"] = "true"
        raw = self._request("GET", f"/tiktok/search/{task_id}", params=params)
        return _parse_model(models.TikTokSearchResponse, raw)

    def extract_file_data(
        self,
        *,
        file_id: str,
        schema: Optional[Dict[str, Any]] = None,
        schema_file: Optional[str] = None,
        what_to_extract: Optional[str] = None,
        include_usage: bool = False,
    ) -> models.ExtractionApiResponse:
        """Extract structured data from an uploaded file's transcript using a custom schema.

        Pass ``schema`` to send a JSON request body, or ``schema_file`` to upload a
        JSON/YAML schema file as multipart/form-data.
        """
        if (schema is None) == (schema_file is None):
            raise ValueError("Pass exactly one of schema or schema_file.")

        if schema_file is not None:
            if not os.path.isfile(schema_file):
                raise FileNotFoundError(schema_file)
            data: Dict[str, Any] = {
                "file_id": file_id,
                "include_usage": "true" if include_usage else "false",
            }
            if what_to_extract is not None:
                data["what_to_extract"] = what_to_extract
            filename = os.path.basename(schema_file)
            content_type = _guess_schema_content_type(schema_file)
            with open(schema_file, "rb") as fp:
                files = {"schema": (filename, fp, content_type)}
                raw = self._request("POST", "/extract/file", data=data, files=files)
            return _parse_model(models.ExtractionApiResponse, raw)

        payload: Dict[str, Any] = {
            "file_id": file_id,
            "schema": schema,
            "include_usage": include_usage,
        }
        if what_to_extract is not None:
            payload["what_to_extract"] = what_to_extract
        raw = self._request("POST", "/extract/file", json_body=payload)
        return _parse_model(models.ExtractionApiResponse, raw)

    # Search -----------------------------------------------------------------------
    def search_youtube(
        self,
        *,
        query: str,
        use_enhanced_search: bool = True,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
        focus: str = "relevance",
        duration: Optional[int] = None,
        max_results: Optional[int] = None,
        include_usage: bool = False,
    ) -> models.VideoSearchResponse:
        """Search YouTube for videos with AI analysis and ranking.

        Parameters
        ----------
        focus:
            One of ``"relevance"`` (default), ``"popularity"``, or ``"brevity"``.
        max_results:
            Maximum number of candidate videos to analyse and return. Each
            candidate incurs one ``residential_request``, so lowering this caps
            cost. Defaults to the plan ceiling when omitted.
        include_usage:
            When True, the response includes a per-call ``usage`` block.
        """
        payload: Dict[str, Any] = {
            "query": query,
            "use_enhanced_search": use_enhanced_search,
            "focus": focus,
            "include_usage": include_usage,
        }
        if start_year is not None:
            payload["start_year"] = start_year
        if end_year is not None:
            payload["end_year"] = end_year
        if duration is not None:
            payload["duration"] = duration
        if max_results is not None:
            payload["max_results"] = max_results
        raw = self._request("POST", "/youtube/search", json_body=payload)
        return _parse_model(models.VideoSearchResponse, raw)

    def search_videos(
        self,
        *,
        query: str,
        use_enhanced_search: bool = True,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
        focus: str = "relevance",
        duration: Optional[int] = None,
        max_results: Optional[int] = None,
        include_usage: bool = False,
    ) -> models.VideoSearchResponse:
        """Deprecated alias for :meth:`search_youtube`.

        The endpoint moved from ``/search/video`` to ``/youtube/search``.
        """
        warnings.warn(
            "search_videos() is deprecated; use search_youtube() instead. "
            "The endpoint moved to /youtube/search.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.search_youtube(
            query=query,
            use_enhanced_search=use_enhanced_search,
            start_year=start_year,
            end_year=end_year,
            focus=focus,
            duration=duration,
            max_results=max_results,
            include_usage=include_usage,
        )

    def search_files(
        self,
        *,
        query: str,
        namespace_ids: Optional[List[str]] = None,
        include_usage: bool = False,
    ) -> models.FileSearchResponse:
        payload: Dict[str, Any] = {"query": query, "include_usage": include_usage}
        if namespace_ids is not None:
            payload["namespace_ids"] = namespace_ids
        raw = self._request("POST", "/search/file", json_body=payload)
        return _parse_model(models.FileSearchResponse, raw)

    # Namespaces -------------------------------------------------------------------
    def get_namespaces(self) -> models.NamespaceListResponse:
        """List all namespaces for the authenticated user."""
        raw = self._request("GET", "/namespaces")
        return _parse_model(models.NamespaceListResponse, raw)

    def create_namespace(self, name: str) -> models.NamespaceResponse:
        """Create a new namespace."""
        raw = self._request("POST", "/namespaces", json_body={"name": name})
        return _parse_model(models.NamespaceResponse, raw)

    def update_namespace(self, namespace_id: str, name: str) -> models.MessageResponse:
        """Rename a namespace."""
        raw = self._request(
            "PUT",
            f"/namespaces/{namespace_id}",
            json_body={"name": name},
        )
        return _parse_model(models.MessageResponse, raw)

    def delete_namespace(self, namespace_id: str) -> models.MessageResponse:
        """Delete a namespace."""
        raw = self._request("DELETE", f"/namespaces/{namespace_id}")
        return _parse_model(models.MessageResponse, raw)

    def update_file_namespaces(
        self,
        file_id: str,
        namespace_ids: List[str],
    ) -> models.FileNamespacesResponse:
        """Replace namespace assignments for a file.

        Returns the updated *namespace_ids* and resolved *namespaces*.
        """
        raw = self._request(
            "PUT",
            f"/file/{file_id}/namespaces",
            json_body={"namespace_ids": namespace_ids},
        )
        return _parse_model(models.FileNamespacesResponse, raw)

    # Uploads ----------------------------------------------------------------------
    def upload_file(
        self,
        file_path: str,
        *,
        wait_for_completion: bool = False,
        namespace_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Upload an audio or video file.

        Parameters
        ----------
        file_path: str
            Path to the local file.
        wait_for_completion: bool
            If *True*, the call will wait until processing finishes before returning.
        namespace_ids: Optional[List[str]]
            Namespace IDs to assign (sent as a JSON array string per API spec).
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(file_path)

        data: Dict[str, Any] = {
            "wait_for_completion": "true" if wait_for_completion else "false",
        }
        if namespace_ids is not None:
            data["namespace_ids"] = json.dumps(namespace_ids)

        filename = os.path.basename(file_path)
        content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

        with open(file_path, "rb") as fp:
            files = {"file": (filename, fp, content_type)}
            return self._request("POST", "/upload/file", data=data, files=files)

    def retry_file_processing(self, file_id: str) -> Dict[str, Any]:
        return self._request("POST", f"/file/{file_id}/retry")

    def cancel_file_upload(self, file_id: str) -> Dict[str, Any]:
        return self._request("POST", f"/file/{file_id}/cancel")

    def delete_file(self, file_id: str) -> Dict[str, Any]:
        return self._request("DELETE", f"/file/{file_id}/delete")

    def get_file_url(self, file_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/file/{file_id}/url")

    # System -----------------------------------------------------------------------
    def get_usage(self) -> models.UsageResponse:
        """Retrieve current API usage and storage information."""
        raw = self._request("GET", "/usage")
        return _parse_model(models.UsageResponse, raw)

    def health_check(self) -> models.HealthResponse:
        raw = self._request("GET", "/health")
        return _parse_model(models.HealthResponse, raw)

    # Tweet analysis ---------------------------------------------------------------
    def submit_tweet_statement(
        self,
        *,
        tweet_id: str,
        webhook_url: Optional[str] = None,
    ) -> AsyncJob:
        """Start a tweet claim analysis job and return its handle immediately.

        ``.result()`` on the handle returns a
        :class:`~vidnavigator.models.TweetStatementResponse`. *webhook_url* is
        passed through (``""`` opts out of your account default).
        """
        payload: Dict[str, Any] = {"tweet_id": tweet_id}
        if webhook_url is not None:
            payload["webhook_url"] = webhook_url
        raw = self._request("POST", "/tweet/statement/async", json_body=payload)
        return self._job_from_submit("tweet_statement", models.AsyncJobSubmitResponse, raw)

    def get_tweet_statement(
        self,
        *,
        tweet_id: str,
        include_usage: bool = False,
        webhook_url: Optional[str] = None,
        timeout: Optional[float] = DEFAULT_JOB_TIMEOUT,
    ) -> models.TweetStatementResponse:
        """Extract a structured claim analysis from an X/Twitter tweet and wait for it.

        Runs as a background job (``POST /tweet/statement/async`` then polling),
        so tweets carrying long videos work too.
        """
        job = self.submit_tweet_statement(tweet_id=tweet_id, webhook_url=webhook_url)
        return job.result(timeout=timeout, include_usage=include_usage)

    # Convenience ------------------------------------------------------------------
    def close(self) -> None:
        """Close the underlying HTTP session."""
        self.session.close()

    def __enter__(self) -> "VidNavigatorClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
