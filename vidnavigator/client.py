"""VidNavigator Developer API Python client."""

from __future__ import annotations

import warnings
from typing import Any, Dict, List, Optional, Union
import requests

from .exceptions import PaymentRequiredError, VidNavigatorError
from .jobs import DEFAULT_JOB_TIMEOUT, Job
from .operations import Operation
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

        # One object per background job, like the JavaScript SDK: call it to
        # wait for the result, `.submit(...)` for a handle, `.resume(task_id)`.
        self.transcribe = Operation("transcribe", self.transcribe_video, self.submit_transcribe_video,
                                    self.resume_job)
        self.watch = Operation("watch", self.watch_video, self.submit_watch_video, self.resume_job)
        self.extract_video = Operation("extract_video", self.extract_video_data,
                                       self.submit_extract_video_data, self.resume_job)
        self.tweet_statement = Operation("tweet_statement", self.get_tweet_statement,
                                         self.submit_tweet_statement, self.resume_job)
        self.tiktok_profile = Operation("tiktok_profile", self.scrape_tiktok_profile,
                                        self.submit_tiktok_profile_scrape, self.resume_job)
        self.tiktok_search = Operation("tiktok_search", self.search_tiktok, self.submit_tiktok_search,
                                       self.resume_job)
        self.tiktok_live_search = Operation("tiktok_live_search", self.search_tiktok_live,
                                            self.submit_tiktok_live_search, self.resume_job)

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
        min_timeout: Optional[float] = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        timeout = self.timeout
        if min_timeout is not None and isinstance(timeout, (int, float)):
            # A call known to run long raises the timeout, never lowers it.
            timeout = max(timeout, min_timeout)
        try:
            response = self.session.request(
                method,
                url,
                params=params,
                json=json_body,
                data=data,
                files=files,
                timeout=timeout,
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

        *job_type* is one of ``"transcribe"``, ``"watch"``, ``"extract_video"``,
        ``"tweet_statement"``, ``"tiktok_profile"``, ``"tiktok_search"`` or
        ``"tiktok_live_search"``.
        Use it after an :class:`~vidnavigator.TaskTimeoutError`, a restart,
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

        Raises :class:`~vidnavigator.TaskTimeoutError` (carrying the
        ``task_id``) if the job is still running after *timeout* seconds.
        """
        job = self.submit_transcribe_video(
            video_url=video_url,
            transcript_text=transcript_text,
            all_videos=all_videos,
            webhook_url=webhook_url,
        )
        return job.result(timeout=timeout, include_usage=include_usage)

    # Watch ------------------------------------------------------------------------
    def submit_watch_video(
        self,
        *,
        video_url: str,
        detail: Optional[str] = None,
        include_transcript: bool = True,
        transcript_text: bool = False,
        webhook_url: Optional[str] = None,
    ) -> Job:
        """Start watching a video and return the job's handle immediately.

        Call ``.result()`` on the handle to wait for a
        :class:`~vidnavigator.models.WatchResponse`, or ``.status()`` to check
        on it. Same parameters as :meth:`watch_video`.
        """
        if detail is not None:
            warnings.warn(_core.WATCH_DETAIL_DEPRECATION, DeprecationWarning, stacklevel=2)
        return self._submit(_core.submit_watch_video(
            video_url=video_url,
            include_transcript=include_transcript,
            transcript_text=transcript_text,
            webhook_url=webhook_url,
        ))

    def watch_video(
        self,
        *,
        video_url: str,
        detail: Optional[str] = None,
        include_transcript: bool = True,
        transcript_text: bool = False,
        include_usage: bool = False,
        webhook_url: Optional[str] = None,
        timeout: Optional[float] = DEFAULT_JOB_TIMEOUT,
    ) -> models.WatchResponse:
        """Read what a video shows, next to what it says, and wait for the result.

        ``.data.scenes`` lists the scenes in order: for each one its ``start``
        and ``end`` in seconds, a ``description`` of the picture and the
        ``on_screen_text``. ``.data.transcript`` holds what is said. Works with
        every platform :meth:`get_transcript` and :meth:`transcribe_video`
        support.

        Parameters
        ----------
        detail:
            Deprecated and ignored: the API no longer uses it.
        include_transcript:
            Set to False for the scenes only. With the default, a video without
            a transcript is not an error: ``.data.transcript`` is empty and
            ``.data.transcript_error`` says why.
        transcript_text:
            Return the transcript as one string instead of segments.

        Runs as a background job (``POST /watch/async`` then polling), so long
        videos are not subject to the synchronous endpoint's duration limit.
        Raises :class:`~vidnavigator.TaskTimeoutError` (carrying the
        ``task_id``) if the job is still running after *timeout* seconds.
        """
        if detail is not None:
            warnings.warn(_core.WATCH_DETAIL_DEPRECATION, DeprecationWarning, stacklevel=2)
        job = self.submit_watch_video(
            video_url=video_url,
            include_transcript=include_transcript,
            transcript_text=transcript_text,
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

    # Extraction -------------------------------------------------------------------
    def submit_extract_video_data(
        self,
        *,
        video_url: str,
        schema: Optional[Dict[str, Any]] = None,
        schema_file: Optional[str] = None,
        what_to_extract: Optional[str] = None,
        transcribe: bool = True,
        include_scenes: bool = False,
        webhook_url: Optional[str] = None,
    ) -> Job:
        """Start a structured-data extraction job and return its handle immediately.

        Pass ``schema`` (a standard JSON Schema, e.g. a Pydantic model's
        ``model_json_schema()``) to send a JSON request body, or ``schema_file``
        to upload a JSON/YAML schema file as multipart/form-data, or neither with
        ``what_to_extract``: the schema is then written from that text and comes
        back on ``.extraction_schema``. A schema is validated at submit time, so
        an invalid one raises before anything is billed.
        ``.result()`` on the handle returns an
        :class:`~vidnavigator.models.ExtractionApiResponse`. Same parameters as
        :meth:`extract_video_data`.
        """
        return self._submit(_core.submit_extract_video_data(
            video_url=video_url,
            schema=schema,
            schema_file=schema_file,
            what_to_extract=what_to_extract,
            transcribe=transcribe,
            include_scenes=include_scenes,
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
        include_scenes: bool = False,
        webhook_url: Optional[str] = None,
        timeout: Optional[float] = DEFAULT_JOB_TIMEOUT,
    ) -> models.ExtractionApiResponse:
        """Extract structured data from an online video and wait for the result.

        Runs as a background job (``POST /extract/async`` then polling).
        The extracted fields are in ``.data`` and the video's metadata in
        ``.video_info``.

        With ``include_scenes=True`` the fields can also be filled from what
        the video shows (a price on screen, a product, a caption), not only
        from what is said; ``.frames_analyzed`` is then the number of frames
        read.
        """
        job = self.submit_extract_video_data(
            video_url=video_url,
            schema=schema,
            schema_file=schema_file,
            what_to_extract=what_to_extract,
            transcribe=transcribe,
            include_scenes=include_scenes,
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
        include_scenes: bool = False,
    ) -> models.ExtractionApiResponse:
        """Extract structured data from an uploaded file, with a JSON Schema or from ``what_to_extract`` alone.

        Pass ``schema`` (a standard JSON Schema) to send a JSON request body, or
        ``schema_file`` to upload a JSON/YAML schema file as multipart/form-data,
        or neither with ``what_to_extract``: the schema is then written from that
        text and comes back on ``.extraction_schema``.

        With ``include_scenes=True`` the fields can also be filled from the
        scenes kept with the file; while the file has none, the call raises
        :class:`~vidnavigator.ScenesNotAvailableError` (see
        :meth:`watch_file`).
        """
        return self._call(_core.extract_file_data(
            file_id=file_id,
            schema=schema,
            schema_file=schema_file,
            what_to_extract=what_to_extract,
            include_usage=include_usage,
            include_scenes=include_scenes,
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
        limit: Optional[int] = None,
        include_usage: bool = False,
        timeout: Optional[float] = DEFAULT_JOB_TIMEOUT,
    ) -> models.TikTokProfileResponse:
        """Scrape a TikTok profile and wait for every matching video, all pages merged.

        Pass *limit* to get only the first page of that size, then page further
        with :meth:`get_tiktok_profile_scrape` using ``response.data.task_id``
        and ``response.data.pagination.next_cursor``.
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
        country: Optional[str] = None,
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
        country:
            Two-letter country code (``"fr"``, ``"de"``, ...) whose TikTok
            results you get. Defaults to ``"gb"``; ``"us"`` is not supported.
            The API lists the accepted codes.
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
            country=country,
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
        country: Optional[str] = None,
        webhook_url: Optional[str] = None,
        limit: Optional[int] = None,
        include_usage: bool = False,
        timeout: Optional[float] = DEFAULT_JOB_TIMEOUT,
    ) -> models.TikTokSearchResponse:
        """Run a TikTok keyword search and wait for every result, all pages merged.

        Pass *limit* to get only the first page of that size, then page further
        with :meth:`get_tiktok_search`. See :meth:`submit_tiktok_search` for the
        parameters.
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
            country=country,
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

    def submit_tiktok_live_search(
        self,
        *,
        query: str,
        max_results: Optional[int] = None,
        country: Optional[str] = None,
        include_stream_urls: Optional[bool] = None,
        webhook_url: Optional[str] = None,
    ) -> Job:
        """Start a search of TikTok LIVE rooms broadcasting now, and return its handle immediately.

        Parameters
        ----------
        max_results:
            Upper bound on rooms; ``0`` or ``None`` means as many as TikTok
            serves (about 50 per keyword).
        country:
            Two-letter country code whose LIVE rooms you get. Defaults to
            ``"us"``; the API lists the accepted codes.
        include_stream_urls:
            The API returns each room's playback URLs by default (FLV and HLS
            by quality, plus an audio-only stream). Pass ``False`` to leave
            them out.
        webhook_url:
            Passed through to the API (``""`` opts out of your account
            default). The event carries a summary only.
        """
        return self._submit(_core.submit_tiktok_live_search(
            query=query,
            max_results=max_results,
            country=country,
            include_stream_urls=include_stream_urls,
            webhook_url=webhook_url,
        ))

    def search_tiktok_live(
        self,
        *,
        query: str,
        max_results: Optional[int] = None,
        country: Optional[str] = None,
        include_stream_urls: Optional[bool] = None,
        webhook_url: Optional[str] = None,
        limit: Optional[int] = None,
        include_usage: bool = False,
        timeout: Optional[float] = DEFAULT_JOB_TIMEOUT,
    ) -> models.TikTokLiveSearchResponse:
        """Search TikTok LIVE rooms and wait for every room, all pages merged.

        Pass *limit* to get only the first page of that size, then page further
        with :meth:`get_tiktok_live_search`. See :meth:`submit_tiktok_live_search`
        for the parameters.
        """
        job = self.submit_tiktok_live_search(
            query=query,
            max_results=max_results,
            country=country,
            include_stream_urls=include_stream_urls,
            webhook_url=webhook_url,
        )
        return job.result(timeout=timeout, include_usage=include_usage, limit=limit)

    def get_tiktok_live_search(
        self,
        task_id: str,
        *,
        cursor: Optional[str] = None,
        limit: int = 50,
        include_usage: bool = False,
    ) -> models.TikTokLiveSearchResponse:
        """Fetch a TikTok LIVE search task once and retrieve a page of rooms.

        Set *include_usage* to receive a ``usage`` block (only populated once the
        task is ``completed``). Polling itself is free.
        """
        return self._call(_core.get_tiktok_live_search(
            task_id, cursor=cursor, limit=limit, include_usage=include_usage,
        ))

    def get_tiktok_live_room(
        self,
        *,
        room_id: Optional[str] = None,
        username: Optional[str] = None,
        url: Optional[str] = None,
        include_comments: Optional[bool] = None,
        comments_limit: Optional[int] = None,
        include_stream_urls: Optional[bool] = None,
        include_usage: bool = False,
    ) -> models.TikTokLiveRoomResponse:
        """Get one TikTok LIVE room, synchronously. Pass exactly one of the first three.

        Parameters
        ----------
        room_id:
            A LIVE room ID, e.g. the ``id`` of a :meth:`search_tiktok_live` room.
        username:
            The streamer, with or without ``@``: their current LIVE, or their
            last one when they are offline (``room.status == "ended"``).
        url:
            ``https://www.tiktok.com/@username/live``, the profile URL, or a
            room's ``share_url``.
        include_comments:
            Also return the latest comments (up to 50, newest first), the
            pinned comment, the intro and the top viewers. Bills 2
            ``residential_request`` instead of 1. An ended room has none.
        comments_limit:
            At most this many comments (1-50, default 50).
        include_stream_urls:
            The room's playback URLs are returned by default; ``False`` leaves
            them out.

        The room has no likes, comment count or share count: TikTok gives those
        to LIVE search only. A room or account that does not exist raises
        :class:`~vidnavigator.exceptions.NotFoundError` and is not billed. The
        call waits up to two minutes, whatever the client's ``timeout``.
        """
        return self._call(_core.get_tiktok_live_room(
            room_id=room_id,
            username=username,
            url=url,
            include_comments=include_comments,
            comments_limit=comments_limit,
            include_stream_urls=include_stream_urls,
            include_usage=include_usage,
        ))

    # Search -----------------------------------------------------------------------
    def search_youtube(
        self,
        *,
        query: str,
        use_enhanced_search: bool = False,
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
        start_year, end_year:
            Only videos published in or after ``start_year``, and in or before
            ``end_year``.
        focus:
            What comes first among the videos that match the query:
            ``"relevance"`` (default, the best matches), ``"recency"`` (the
            most recent), ``"popularity"`` (the most viewed) or ``"brevity"``
            (the shortest). With a value other than ``"relevance"``,
            ``explanation`` is empty.
        duration:
            Maximum duration in seconds: longer videos are left out.
        max_results:
            Maximum number of candidate videos to analyse and return. Each
            candidate incurs one ``residential_request``, so lowering this caps
            cost. Defaults to the plan ceiling when omitted.
        include_usage:
            When True, the response includes a per-call ``usage`` block.

        If credits run out mid-search, the API answers 402 with the videos
        analysed so far: they are returned with ``status == "partial"`` and
        ``error_code == "insufficient_credits_video_search"`` instead of
        raising. A search that cannot start raises ``PaymentRequiredError``.
        """
        req = _core.search_youtube(
            query=query,
            use_enhanced_search=use_enhanced_search,
            start_year=start_year,
            end_year=end_year,
            focus=focus,
            duration=duration,
            max_results=max_results,
            include_usage=include_usage,
        )
        try:
            return self._call(req)
        except PaymentRequiredError as exc:
            partial = _core.partial_youtube_search(exc)
            if partial is None:
                raise
            return partial

    def search_videos(
        self,
        *,
        query: str,
        use_enhanced_search: bool = False,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
        focus: str = "relevance",
        duration: Optional[int] = None,
        max_results: Optional[int] = None,
        include_usage: bool = False,
    ) -> models.VideoSearchResponse:
        """Deprecated alias for :meth:`search_youtube`, which calls ``/youtube/search``."""
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
        include_scenes: bool = False,
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
        include_scenes: bool
            If *True*, what the file shows is analyzed as well (video files
            only). Follow ``file_info.scenes_status`` with :meth:`get_file`.
        """
        return self._call(_core.upload_file(
            file_path, wait_for_completion=wait_for_completion, namespace_ids=namespace_ids,
            include_scenes=include_scenes,
        ))

    def watch_file(self, file_id: str) -> models.FileScenesResponse:
        """Watch a file already uploaded: start the analysis of what its picture shows.

        Calls ``POST /watch/file``, as :meth:`watch_video` does for an online
        video. The scenes of a file are analyzed once and kept with it. Follow
        ``file_info.scenes_status`` with :meth:`get_file`: it goes from
        ``"processing"`` to ``"completed"`` (the scenes are then in
        ``.data.scenes``) or ``"failed"`` (``file_info.scenes_error`` says
        why). :meth:`extract_file_data` reads them with ``include_scenes=True``.

        Calling it again while the analysis runs, or once it is done, starts
        nothing new: ``.data.scenes_status`` says where it stands. An audio
        file has no picture: the call raises
        :class:`~vidnavigator.BadRequestError` (``frames_not_available``).
        """
        return self._call(_core.watch_file(file_id))

    def analyze_file_scenes(self, file_id: str) -> models.FileScenesResponse:
        """The name of :meth:`watch_file` before 3.3.0, kept so existing code keeps working."""
        return self.watch_file(file_id)

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
        include_scenes: bool = False,
        webhook_url: Optional[str] = None,
    ) -> Job:
        """Start a tweet claim analysis job and return its handle immediately.

        ``.result()`` on the handle returns a
        :class:`~vidnavigator.models.TweetStatementResponse`. Same parameters
        as :meth:`get_tweet_statement`. *webhook_url* is passed through
        (``""`` opts out of your account default).
        """
        return self._submit(_core.submit_tweet_statement(
            tweet_id=tweet_id,
            include_scenes=include_scenes,
            webhook_url=webhook_url,
        ))

    def get_tweet_statement(
        self,
        *,
        tweet_id: str,
        include_usage: bool = False,
        include_scenes: bool = False,
        webhook_url: Optional[str] = None,
        timeout: Optional[float] = DEFAULT_JOB_TIMEOUT,
    ) -> models.TweetStatementResponse:
        """Extract a structured claim analysis from an X/Twitter tweet and wait for it.

        Runs as a background job (``POST /tweet/statement/async`` then polling),
        so tweets carrying long videos work too.

        With ``include_scenes=True`` what the post's video and the quoted
        post's video show (their scenes, with the text readable on screen) is
        read as well and used with their transcripts, so a video without speech
        is summarized from its picture. ``.data.frames_analyzed`` is then the
        number of frames read; ``.data.scenes_error`` is set when a video's
        picture could not be read (that video is then summarized from its
        transcript alone).
        """
        job = self.submit_tweet_statement(
            tweet_id=tweet_id,
            include_scenes=include_scenes,
            webhook_url=webhook_url,
        )
        return job.result(timeout=timeout, include_usage=include_usage)

    # Convenience ------------------------------------------------------------------
    def close(self) -> None:
        """Close the underlying HTTP session."""
        self.session.close()

    def __enter__(self) -> "VidNavigatorClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
