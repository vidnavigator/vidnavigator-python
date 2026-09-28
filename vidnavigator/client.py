"""VidNavigator Developer API Python client."""

from __future__ import annotations

import warnings
from typing import Any, Dict, List, Optional, Union
import requests

from .exceptions import VidNavigatorError
from .jobs import DEFAULT_JOB_TIMEOUT, Job
from . import _core, models
from ._core import (  # noqa: F401  (re-exported for backwards compatibility)
    DEFAULT_BASE_URL,
    USER_AGENT,
    DateLike,
    Request,
    format_datetime as _format_datetime,
    guess_schema_content_type as _guess_schema_content_type,
    parse_model as _parse_model,
)


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
        api_key = _core.resolve_api_key(api_key)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update(_core.default_headers(api_key))

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
        url = f"{self.base_url}{path}"
        try:
            response = self.session.request(
                method,
                url,
                params=params,
                json=json_body,
                data=data,
                files=files,
                timeout=self.timeout,
                stream=stream,
            )
        except requests.RequestException as exc:
            raise VidNavigatorError(f"Request failed: {exc}") from exc

        if stream:
            return response
        return _core.decode_response(response, ok=response.ok, reason_attr="reason")

    def _call(self, req: Request) -> Any:
        """Send a request built by :mod:`vidnavigator._core` and parse the response."""
        if req.upload is None:
            raw = self._request(req.method, req.path, **req.kwargs)
        else:
            up = req.upload
            with open(up.path, "rb") as fp:
                files = {up.field: (up.filename, fp, up.content_type)}
                raw = self._request(req.method, req.path, files=files, **req.kwargs)
        return req.parse(raw)

    def _submit(self, req: Request) -> Job:
        submitted = self._call(req)
        task_id = _core.submitted_task_id(req.job_type, submitted)
        return Job(self, req.job_type, task_id, submit_response=submitted)

    # ---------------------------------------------------------------------
    # Background jobs
    # ---------------------------------------------------------------------

    def resume_job(self, job_type: str, task_id: str) -> Job:
        """Rebuild the handle of a job submitted earlier from its ``task_id``.

        *job_type* is one of ``"transcribe"``, ``"extract_video"``,
        ``"tweet_statement"``, ``"tiktok_profile"`` or ``"tiktok_search"``.
        Use it after an :class:`~vidnavigator.JobTimeoutError`, a restart,
        or a webhook delivery. Results stay readable for 1 hour after the job
        finishes.
        """
        return Job(self, job_type, task_id)

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
        return self._call(_core.get_transcript(
            video_url=video_url,
            language=language,
            metadata_only=metadata_only,
            fallback_to_metadata=fallback_to_metadata,
            transcript_text=transcript_text,
            include_usage=include_usage,
        ))

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
    ) -> Job:
        """Start a speech-to-text transcription job and return its handle immediately.

        Call ``.result()`` on the handle to wait for a
        :class:`~vidnavigator.models.TranscriptResponse` (or
        :class:`~vidnavigator.models.TranscribeAllVideosResponse` when
        *all_videos* is True), or ``.status()`` to check on it.

        *webhook_url* is passed through to the API: it overrides your
        account-level default webhook, and ``""`` opts this job out of it.
        Polling works whether or not a webhook is configured.
        """
        return self._submit(_core.submit_transcribe_video(
            video_url=video_url,
            transcript_text=transcript_text,
            all_videos=all_videos,
            webhook_url=webhook_url,
        ))

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

        Raises :class:`~vidnavigator.JobTimeoutError` (carrying the
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
        return self._call(_core.get_files(
            limit=limit, offset=offset, status=status, namespace_id=namespace_id,
        ))

    def get_file(
        self,
        file_id: str,
        *,
        transcript_text: bool = False,
    ) -> models.FileResponse:
        """Retrieve details (and transcript) for a specific file."""
        return self._call(_core.get_file(file_id, transcript_text=transcript_text))

    # Analysis ---------------------------------------------------------------------
    def analyze_video(
        self,
        *,
        video_url: str,
        query: Optional[str] = None,
        transcript_text: bool = False,
        include_usage: bool = False,
    ) -> models.AnalysisResponse:
        """Summarize an online video and, with *query*, answer a question about it."""
        return self._call(_core.analyze_video(
            video_url=video_url, query=query, transcript_text=transcript_text,
            include_usage=include_usage,
        ))

    def analyze_file(
        self,
        *,
        file_id: str,
        query: Optional[str] = None,
        transcript_text: bool = False,
        include_usage: bool = False,
    ) -> models.AnalysisResponse:
        """Summarize an uploaded file and, with *query*, answer a question about it."""
        return self._call(_core.analyze_file(
            file_id=file_id, query=query, transcript_text=transcript_text,
            include_usage=include_usage,
        ))

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
    ) -> Job:
        """Start a structured-data extraction job and return its handle immediately.

        Pass ``schema`` to send a JSON request body, or ``schema_file`` to upload a
        JSON/YAML schema file as multipart/form-data. The schema is validated at
        submit time, so an invalid one raises before anything is billed.
        ``.result()`` on the handle returns an
        :class:`~vidnavigator.models.ExtractionApiResponse`.
        """
        return self._submit(_core.submit_extract_video_data(
            video_url=video_url,
            schema=schema,
            schema_file=schema_file,
            what_to_extract=what_to_extract,
            transcribe=transcribe,
            webhook_url=webhook_url,
        ))

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
        The extracted fields are in ``.data`` and the video's metadata in
        ``.video_info``.
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
        return self._call(_core.extract_file_data(
            file_id=file_id,
            schema=schema,
            schema_file=schema_file,
            what_to_extract=what_to_extract,
            include_usage=include_usage,
        ))

    # TikTok -----------------------------------------------------------------------
    def submit_tiktok_profile_scrape(
        self,
        *,
        profile_url: str,
        max_posts: Optional[int] = None,
        after_datetime: Optional[DateLike] = None,
        before_datetime: Optional[DateLike] = None,
        min_likes: Optional[int] = None,
        max_likes: Optional[int] = None,
        webhook_url: Optional[str] = None,
    ) -> Job:
        """Start a TikTok profile scrape job and return its handle immediately.

        Datetime filters must be YYYY-MM-DD strings or ISO format with timezone.
        ``date`` and ``datetime`` values are accepted and serialized automatically.

        ``.result(limit=..., cursor=...)`` on the handle waits and returns a
        :class:`~vidnavigator.models.TikTokProfileResponse` page; page further
        with :meth:`get_tiktok_profile_scrape`. *webhook_url* is passed through
        (``""`` opts out of your account default); the event carries a summary
        only.
        """
        return self._submit(_core.submit_tiktok_profile_scrape(
            profile_url=profile_url,
            max_posts=max_posts,
            after_datetime=after_datetime,
            before_datetime=before_datetime,
            min_likes=min_likes,
            max_likes=max_likes,
            webhook_url=webhook_url,
        ))

    def scrape_tiktok_profile(
        self,
        *,
        profile_url: str,
        max_posts: Optional[int] = None,
        after_datetime: Optional[DateLike] = None,
        before_datetime: Optional[DateLike] = None,
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
        return self._call(_core.get_tiktok_profile_scrape(
            task_id, cursor=cursor, limit=limit, include_usage=include_usage,
        ))

    def submit_tiktok_search(
        self,
        *,
        query: str,
        max_results: Optional[int] = None,
        parallel_search_slices: Optional[int] = None,
        sort_by: Optional[str] = None,
        published_within: Optional[str] = None,
        after_datetime: Optional[DateLike] = None,
        before_datetime: Optional[DateLike] = None,
        min_likes: Optional[int] = None,
        max_likes: Optional[int] = None,
        min_views: Optional[int] = None,
        max_views: Optional[int] = None,
        webhook_url: Optional[str] = None,
    ) -> Job:
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
            default). The event carries a summary only.
        """
        return self._submit(_core.submit_tiktok_search(
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
        ))

    def search_tiktok(
        self,
        *,
        query: str,
        max_results: Optional[int] = None,
        parallel_search_slices: Optional[int] = None,
        sort_by: Optional[str] = None,
        published_within: Optional[str] = None,
        after_datetime: Optional[DateLike] = None,
        before_datetime: Optional[DateLike] = None,
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
        return self._call(_core.get_tiktok_search(
            task_id, cursor=cursor, limit=limit, include_usage=include_usage,
        ))

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
        return self._call(_core.search_youtube(
            query=query,
            use_enhanced_search=use_enhanced_search,
            start_year=start_year,
            end_year=end_year,
            focus=focus,
            duration=duration,
            max_results=max_results,
            include_usage=include_usage,
        ))

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
        """Search the content of your uploaded files in natural language."""
        return self._call(_core.search_files(
            query=query, namespace_ids=namespace_ids, include_usage=include_usage,
        ))

    # Namespaces -------------------------------------------------------------------
    def get_namespaces(self) -> models.NamespaceListResponse:
        """List all namespaces for the authenticated user."""
        return self._call(_core.get_namespaces())

    def create_namespace(self, name: str) -> models.NamespaceResponse:
        """Create a new namespace."""
        return self._call(_core.create_namespace(name))

    def update_namespace(self, namespace_id: str, name: str) -> models.MessageResponse:
        """Rename a namespace."""
        return self._call(_core.update_namespace(namespace_id, name))

    def delete_namespace(self, namespace_id: str) -> models.MessageResponse:
        """Delete a namespace."""
        return self._call(_core.delete_namespace(namespace_id))

    def update_file_namespaces(
        self,
        file_id: str,
        namespace_ids: List[str],
    ) -> models.FileNamespacesResponse:
        """Replace namespace assignments for a file.

        Returns the updated *namespace_ids* and resolved *namespaces*.
        """
        return self._call(_core.update_file_namespaces(file_id, namespace_ids))

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
        return self._call(_core.upload_file(
            file_path, wait_for_completion=wait_for_completion, namespace_ids=namespace_ids,
        ))

    def retry_file_processing(self, file_id: str) -> Dict[str, Any]:
        return self._call(_core.file_action("POST", f"/file/{file_id}/retry"))

    def cancel_file_upload(self, file_id: str) -> Dict[str, Any]:
        return self._call(_core.file_action("POST", f"/file/{file_id}/cancel"))

    def delete_file(self, file_id: str) -> Dict[str, Any]:
        return self._call(_core.file_action("DELETE", f"/file/{file_id}/delete"))

    def get_file_url(self, file_id: str) -> Dict[str, Any]:
        return self._call(_core.file_action("GET", f"/file/{file_id}/url"))

    # System -----------------------------------------------------------------------
    def get_usage(self) -> models.UsageResponse:
        """Retrieve current API usage and storage information."""
        return self._call(_core.get_usage())

    def health_check(self) -> models.HealthResponse:
        return self._call(_core.health_check())

    # Tweet analysis ---------------------------------------------------------------
    def submit_tweet_statement(
        self,
        *,
        tweet_id: str,
        webhook_url: Optional[str] = None,
    ) -> Job:
        """Start a tweet claim analysis job and return its handle immediately.

        ``.result()`` on the handle returns a
        :class:`~vidnavigator.models.TweetStatementResponse`. *webhook_url* is
        passed through (``""`` opts out of your account default).
        """
        return self._submit(_core.submit_tweet_statement(tweet_id=tweet_id, webhook_url=webhook_url))

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
