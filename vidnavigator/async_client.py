"""Asyncio client for the VidNavigator Developer API.

Requires the ``async`` extra: ``pip install "vidnavigator[async]"``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

try:  # httpx is an optional dependency
    import httpx
except ImportError:  # pragma: no cover - exercised only without the extra
    httpx = None  # type: ignore[assignment]

from .exceptions import VidNavigatorError
from .jobs import DEFAULT_JOB_TIMEOUT, AsyncJob
from . import _core, models
from ._core import DEFAULT_BASE_URL, DateLike, Request


class AsyncVidNavigatorClient:
    """Asyncio client for the VidNavigator Developer API.

    Same methods and arguments as :class:`~vidnavigator.VidNavigatorClient`,
    as coroutines. Job methods return an :class:`~vidnavigator.AsyncJob`, and
    waiting for a job never blocks the event loop.

    Parameters
    ----------
    api_key:
        Your VidNavigator API key, or ``None`` to read ``VIDNAVIGATOR_API_KEY``.
    base_url:
        Override the default API base URL (useful for testing/staging).
    timeout:
        Per-request timeout in seconds.
    http_client:
        Optional ``httpx.AsyncClient`` to send requests with. You stay
        responsible for closing a client you pass in.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: Union[int, float] = 30,
        http_client: Optional["httpx.AsyncClient"] = None,
    ) -> None:
        if httpx is None:
            raise ImportError(
                'AsyncVidNavigatorClient requires httpx: pip install "vidnavigator[async]"'
            )
        self._headers = _core.default_headers(_core.resolve_api_key(api_key))
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._owns_http_client = http_client is None
        self.http_client = http_client or httpx.AsyncClient(timeout=timeout)

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------
    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        files: Any = None,
    ) -> Any:
        try:
            response = await self.http_client.request(
                method,
                f"{self.base_url}{path}",
                params=params,
                json=json_body,
                data=data,
                files=files,
                headers=self._headers,
                timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            raise VidNavigatorError(f"Request failed: {exc}") from exc
        return _core.decode_response(response, ok=response.is_success, reason_attr="reason_phrase")

    async def _call(self, req: Request) -> Any:
        """Send a request built by :mod:`vidnavigator._core` and parse the response."""
        if req.upload is None:
            raw = await self._request(req.method, req.path, **req.kwargs)
        else:
            up = req.upload
            with open(up.path, "rb") as fp:
                files = {up.field: (up.filename, fp, up.content_type)}
                raw = await self._request(req.method, req.path, files=files, **req.kwargs)
        return req.parse(raw)

    async def _submit(self, req: Request) -> AsyncJob:
        submitted = await self._call(req)
        task_id = _core.submitted_task_id(req.job_type, submitted)
        return AsyncJob(self, req.job_type, task_id, submit_response=submitted)

    # ---------------------------------------------------------------------
    # Background jobs
    # ---------------------------------------------------------------------

    def resume_job(self, job_type: str, task_id: str) -> AsyncJob:
        """Rebuild the handle of a job submitted earlier. See :meth:`VidNavigatorClient.resume_job`."""
        return AsyncJob(self, job_type, task_id)

    # Transcripts ------------------------------------------------------------------
    async def get_transcript(
        self,
        *,
        video_url: str,
        language: Optional[str] = None,
        metadata_only: bool = False,
        fallback_to_metadata: bool = False,
        transcript_text: bool = False,
        include_usage: bool = False,
    ) -> models.TranscriptResponse:
        """Extract the captions of any supported online video."""
        return await self._call(_core.get_transcript(
            video_url=video_url,
            language=language,
            metadata_only=metadata_only,
            fallback_to_metadata=fallback_to_metadata,
            transcript_text=transcript_text,
            include_usage=include_usage,
        ))

    async def submit_transcribe_video(
        self,
        *,
        video_url: str,
        transcript_text: bool = False,
        all_videos: bool = False,
        webhook_url: Optional[str] = None,
    ) -> AsyncJob:
        """Start a speech-to-text job and return its handle immediately."""
        return await self._submit(_core.submit_transcribe_video(
            video_url=video_url,
            transcript_text=transcript_text,
            all_videos=all_videos,
            webhook_url=webhook_url,
        ))

    async def transcribe_video(
        self,
        *,
        video_url: str,
        transcript_text: bool = False,
        all_videos: bool = False,
        include_usage: bool = False,
        webhook_url: Optional[str] = None,
        timeout: Optional[float] = DEFAULT_JOB_TIMEOUT,
    ) -> Union[models.TranscriptResponse, models.TranscribeAllVideosResponse]:
        """Transcribe an online video with speech-to-text and wait for the result."""
        job = await self.submit_transcribe_video(
            video_url=video_url,
            transcript_text=transcript_text,
            all_videos=all_videos,
            webhook_url=webhook_url,
        )
        return await job.result(timeout=timeout, include_usage=include_usage)

    # Files ------------------------------------------------------------------------
    async def get_files(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        namespace_id: Optional[str] = None,
    ) -> models.FilesListResponse:
        """Retrieve a paginated list of uploaded files."""
        return await self._call(_core.get_files(
            limit=limit, offset=offset, status=status, namespace_id=namespace_id,
        ))

    async def get_file(self, file_id: str, *, transcript_text: bool = False) -> models.FileResponse:
        """Retrieve details (and transcript) for a specific file."""
        return await self._call(_core.get_file(file_id, transcript_text=transcript_text))

    async def upload_file(
        self,
        file_path: str,
        *,
        wait_for_completion: bool = False,
        namespace_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Upload an audio or video file."""
        return await self._call(_core.upload_file(
            file_path, wait_for_completion=wait_for_completion, namespace_ids=namespace_ids,
        ))

    async def retry_file_processing(self, file_id: str) -> Dict[str, Any]:
        return await self._call(_core.file_action("POST", f"/file/{file_id}/retry"))

    async def cancel_file_upload(self, file_id: str) -> Dict[str, Any]:
        return await self._call(_core.file_action("POST", f"/file/{file_id}/cancel"))

    async def delete_file(self, file_id: str) -> Dict[str, Any]:
        return await self._call(_core.file_action("DELETE", f"/file/{file_id}/delete"))

    async def get_file_url(self, file_id: str) -> Dict[str, Any]:
        return await self._call(_core.file_action("GET", f"/file/{file_id}/url"))

    # Analysis ---------------------------------------------------------------------
    async def analyze_video(
        self,
        *,
        video_url: str,
        query: Optional[str] = None,
        transcript_text: bool = False,
        include_usage: bool = False,
    ) -> models.AnalysisResponse:
        """Summarize an online video and, with *query*, answer a question about it."""
        return await self._call(_core.analyze_video(
            video_url=video_url, query=query, transcript_text=transcript_text,
            include_usage=include_usage,
        ))

    async def analyze_file(
        self,
        *,
        file_id: str,
        query: Optional[str] = None,
        transcript_text: bool = False,
        include_usage: bool = False,
    ) -> models.AnalysisResponse:
        """Summarize an uploaded file and, with *query*, answer a question about it."""
        return await self._call(_core.analyze_file(
            file_id=file_id, query=query, transcript_text=transcript_text,
            include_usage=include_usage,
        ))

    # Extraction -------------------------------------------------------------------
    async def submit_extract_video_data(
        self,
        *,
        video_url: str,
        schema: Optional[Dict[str, Any]] = None,
        schema_file: Optional[str] = None,
        what_to_extract: Optional[str] = None,
        transcribe: bool = True,
        webhook_url: Optional[str] = None,
    ) -> AsyncJob:
        """Start a structured-data extraction job and return its handle immediately."""
        return await self._submit(_core.submit_extract_video_data(
            video_url=video_url,
            schema=schema,
            schema_file=schema_file,
            what_to_extract=what_to_extract,
            transcribe=transcribe,
            webhook_url=webhook_url,
        ))

    async def extract_video_data(
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
        """Extract structured data from an online video and wait for the result."""
        job = await self.submit_extract_video_data(
            video_url=video_url,
            schema=schema,
            schema_file=schema_file,
            what_to_extract=what_to_extract,
            transcribe=transcribe,
            webhook_url=webhook_url,
        )
        return await job.result(timeout=timeout, include_usage=include_usage)

    async def extract_file_data(
        self,
        *,
        file_id: str,
        schema: Optional[Dict[str, Any]] = None,
        schema_file: Optional[str] = None,
        what_to_extract: Optional[str] = None,
        include_usage: bool = False,
    ) -> models.ExtractionApiResponse:
        """Extract structured data from an uploaded file's transcript."""
        return await self._call(_core.extract_file_data(
            file_id=file_id,
            schema=schema,
            schema_file=schema_file,
            what_to_extract=what_to_extract,
            include_usage=include_usage,
        ))

    # TikTok -----------------------------------------------------------------------
    async def submit_tiktok_profile_scrape(
        self,
        *,
        profile_url: str,
        max_posts: Optional[int] = None,
        after_datetime: Optional[DateLike] = None,
        before_datetime: Optional[DateLike] = None,
        min_likes: Optional[int] = None,
        max_likes: Optional[int] = None,
        webhook_url: Optional[str] = None,
    ) -> AsyncJob:
        """Start a TikTok profile scrape job and return its handle immediately."""
        return await self._submit(_core.submit_tiktok_profile_scrape(
            profile_url=profile_url,
            max_posts=max_posts,
            after_datetime=after_datetime,
            before_datetime=before_datetime,
            min_likes=min_likes,
            max_likes=max_likes,
            webhook_url=webhook_url,
        ))

    async def scrape_tiktok_profile(
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
        """Scrape a TikTok profile and wait for the first page of *limit* videos."""
        job = await self.submit_tiktok_profile_scrape(
            profile_url=profile_url,
            max_posts=max_posts,
            after_datetime=after_datetime,
            before_datetime=before_datetime,
            min_likes=min_likes,
            max_likes=max_likes,
            webhook_url=webhook_url,
        )
        return await job.result(timeout=timeout, include_usage=include_usage, limit=limit)

    async def get_tiktok_profile_scrape(
        self,
        task_id: str,
        *,
        cursor: Optional[str] = None,
        limit: int = 50,
        include_usage: bool = False,
    ) -> models.TikTokProfileResponse:
        """Fetch a TikTok profile scrape task once and retrieve a page of videos."""
        return await self._call(_core.get_tiktok_profile_scrape(
            task_id, cursor=cursor, limit=limit, include_usage=include_usage,
        ))

    async def submit_tiktok_search(
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
    ) -> AsyncJob:
        """Start a TikTok keyword search job and return its handle immediately."""
        return await self._submit(_core.submit_tiktok_search(
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

    async def search_tiktok(
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
        """Run a TikTok keyword search and wait for the first page of *limit* results."""
        job = await self.submit_tiktok_search(
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
        return await job.result(timeout=timeout, include_usage=include_usage, limit=limit)

    async def get_tiktok_search(
        self,
        task_id: str,
        *,
        cursor: Optional[str] = None,
        limit: int = 50,
        include_usage: bool = False,
    ) -> models.TikTokSearchResponse:
        """Fetch a TikTok keyword search task once and retrieve a page of results."""
        return await self._call(_core.get_tiktok_search(
            task_id, cursor=cursor, limit=limit, include_usage=include_usage,
        ))

    # Search -----------------------------------------------------------------------
    async def search_youtube(
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
        """Search YouTube for videos with AI analysis and ranking."""
        return await self._call(_core.search_youtube(
            query=query,
            use_enhanced_search=use_enhanced_search,
            start_year=start_year,
            end_year=end_year,
            focus=focus,
            duration=duration,
            max_results=max_results,
            include_usage=include_usage,
        ))

    async def search_files(
        self,
        *,
        query: str,
        namespace_ids: Optional[List[str]] = None,
        include_usage: bool = False,
    ) -> models.FileSearchResponse:
        """Search the content of your uploaded files in natural language."""
        return await self._call(_core.search_files(
            query=query, namespace_ids=namespace_ids, include_usage=include_usage,
        ))

    # Namespaces -------------------------------------------------------------------
    async def get_namespaces(self) -> models.NamespaceListResponse:
        """List all namespaces for the authenticated user."""
        return await self._call(_core.get_namespaces())

    async def create_namespace(self, name: str) -> models.NamespaceResponse:
        """Create a new namespace."""
        return await self._call(_core.create_namespace(name))

    async def update_namespace(self, namespace_id: str, name: str) -> models.MessageResponse:
        """Rename a namespace."""
        return await self._call(_core.update_namespace(namespace_id, name))

    async def delete_namespace(self, namespace_id: str) -> models.MessageResponse:
        """Delete a namespace."""
        return await self._call(_core.delete_namespace(namespace_id))

    async def update_file_namespaces(
        self, file_id: str, namespace_ids: List[str],
    ) -> models.FileNamespacesResponse:
        """Replace namespace assignments for a file."""
        return await self._call(_core.update_file_namespaces(file_id, namespace_ids))

    # System -----------------------------------------------------------------------
    async def get_usage(self) -> models.UsageResponse:
        """Retrieve current API usage and storage information."""
        return await self._call(_core.get_usage())

    async def health_check(self) -> models.HealthResponse:
        return await self._call(_core.health_check())

    # Tweet analysis ---------------------------------------------------------------
    async def submit_tweet_statement(
        self, *, tweet_id: str, webhook_url: Optional[str] = None,
    ) -> AsyncJob:
        """Start a tweet claim analysis job and return its handle immediately."""
        return await self._submit(_core.submit_tweet_statement(tweet_id=tweet_id, webhook_url=webhook_url))

    async def get_tweet_statement(
        self,
        *,
        tweet_id: str,
        include_usage: bool = False,
        webhook_url: Optional[str] = None,
        timeout: Optional[float] = DEFAULT_JOB_TIMEOUT,
    ) -> models.TweetStatementResponse:
        """Analyze the claim made in an X/Twitter tweet and wait for the result."""
        job = await self.submit_tweet_statement(tweet_id=tweet_id, webhook_url=webhook_url)
        return await job.result(timeout=timeout, include_usage=include_usage)

    # Convenience ------------------------------------------------------------------
    async def aclose(self) -> None:
        """Close the HTTP client, unless it was passed in by the caller."""
        if self._owns_http_client:
            await self.http_client.aclose()

    async def __aenter__(self) -> "AsyncVidNavigatorClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.aclose()
