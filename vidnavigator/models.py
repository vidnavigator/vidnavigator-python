"""Typed Pydantic models that mirror VidNavigator API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from .exceptions import VidNavigatorError, error_from_response

try:
    from pydantic import field_validator as _field_validator

    def _pre_validator(*fields):
        return _field_validator(*fields, mode="before")
except ImportError:
    from pydantic import validator

    def _pre_validator(*fields):
        return validator(*fields, pre=True)

# ---------------------------------------------------------------------------
# Core data models (mirror `components.schemas`)
# ---------------------------------------------------------------------------


class TranscriptSegment(BaseModel):
    text: str
    start: float
    end: float


class VideoCarouselInfo(BaseModel):
    total_items: Optional[int] = Field(None, alias="total_items")
    video_count: Optional[int] = Field(None, alias="video_count")
    image_count: Optional[int] = Field(None, alias="image_count")
    selected_index: Optional[int] = Field(None, alias="selected_index")


class VideoInfo(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    url: Optional[str] = None
    channel: Optional[str] = None
    channel_url: Optional[str] = Field(None, alias="channel_url")
    duration: Optional[float] = None
    views: Optional[int] = None
    likes: Optional[int] = None
    published_date: Optional[str] = Field(None, alias="published_date")
    keywords: Optional[List[str]] = None
    category: Optional[str] = None
    available_languages: Optional[List[str]] = Field(None, alias="available_languages")
    selected_language: Optional[str] = Field(None, alias="selected_language")
    carousel_info: Optional[VideoCarouselInfo] = Field(None, alias="carousel_info")


class NamespaceRef(BaseModel):
    """Resolved namespace reference returned alongside file objects."""

    id: Optional[str] = None
    name: Optional[str] = None


class FileInfo(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    size: Optional[int] = None
    type: Optional[str] = None
    duration: Optional[float] = None
    status: Optional[str] = None
    created_at: Optional[str] = Field(None, alias="created_at")
    updated_at: Optional[str] = Field(None, alias="updated_at")
    original_file_date: Optional[str] = Field(None, alias="original_file_date")
    has_transcript: Optional[bool] = Field(None, alias="has_transcript")
    error_message: Optional[str] = Field(None, alias="error_message")
    namespace_ids: Optional[List[str]] = Field(None, alias="namespace_ids")
    namespaces: Optional[List[NamespaceRef]] = None


class PersonPlaceSubject(BaseModel):
    name: Optional[str] = None
    context: Optional[str] = None
    description: Optional[str] = None
    importance: Optional[str] = None

    @classmethod
    def _coerce(cls, v: Any) -> "PersonPlaceSubject":
        """Accept a plain string as a shorthand for ``{"name": value}``."""
        if isinstance(v, str):
            return cls(name=v)
        return v  # type: ignore[return-value]


KeySubjectItem = Union[PersonPlaceSubject, str]


def _coerce_person_place_list(
    values: Optional[List[Any]],
) -> Optional[List[PersonPlaceSubject]]:
    """Coerce plain strings to PersonPlaceSubject in people/places/key_subjects lists."""
    if values is None:
        return None
    return [
        PersonPlaceSubject(name=v) if isinstance(v, str) else v
        for v in values
    ]


class QueryAnswerDetail(BaseModel):
    answer: Optional[str] = None
    best_segment_index: Optional[int] = Field(None, alias="best_segment_index")
    relevant_segments: Optional[List[str]] = Field(None, alias="relevant_segments")


class AnalysisResult(BaseModel):
    summary: Optional[str] = None
    people: Optional[List[Any]] = None
    places: Optional[List[Any]] = None
    key_subjects: Optional[List[Any]] = Field(None, alias="key_subjects")
    timestamp: Optional[float] = None
    relevant_text: Optional[str] = Field(None, alias="relevant_text")
    query_answer: Optional[QueryAnswerDetail] = Field(None, alias="query_answer")

    @_pre_validator("people", "places", "key_subjects")
    @classmethod
    def _coerce_lists(cls, v):
        return _coerce_person_place_list(v)


class VideoSearchResult(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    channel: Optional[str] = None
    published_date: Optional[str] = Field(None, alias="published_date")
    duration: Optional[float] = None
    views: Optional[int] = None
    likes: Optional[int] = None
    relevance_score: Optional[float] = Field(None, alias="relevance_score")
    transcript_summary: Optional[str] = Field(None, alias="transcript_summary")
    people: Optional[List[Any]] = None
    places: Optional[List[Any]] = None
    key_subjects: Optional[List[Any]] = Field(None, alias="key_subjects")
    timestamp: Optional[float] = None
    relevant_text: Optional[str] = Field(None, alias="relevant_text")
    query_relevance: Optional[str] = Field(None, alias="query_relevance")

    @_pre_validator("people", "places", "key_subjects")
    @classmethod
    def _coerce_lists(cls, v):
        return _coerce_person_place_list(v)


class FileSearchResult(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    duration: Optional[float] = None
    size: Optional[int] = None
    type: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[str] = Field(None, alias="created_at")
    updated_at: Optional[str] = Field(None, alias="updated_at")
    original_file_date: Optional[str] = Field(None, alias="original_file_date")
    file_url: Optional[str] = Field(None, alias="file_url")
    namespace_ids: Optional[List[str]] = Field(None, alias="namespace_ids")
    namespaces: Optional[List[NamespaceRef]] = None
    relevance_score: Optional[float] = Field(None, alias="relevance_score")
    timestamps: Optional[List[float]] = Field(None, alias="timestamps")
    relevant_text: Optional[str] = Field(None, alias="relevant_text")
    query_answer: Optional[str] = Field(None, alias="query_answer")
    transcript_summary: Optional[str] = Field(None, alias="transcript_summary")
    people: Optional[List[Any]] = None
    places: Optional[List[Any]] = None
    key_subjects: Optional[List[Any]] = Field(None, alias="key_subjects")

    @_pre_validator("people", "places", "key_subjects")
    @classmethod
    def _coerce_lists(cls, v):
        return _coerce_person_place_list(v)


class CarouselInfo(BaseModel):
    total_items: Optional[int] = Field(None, alias="total_items")
    video_count: Optional[int] = Field(None, alias="video_count")
    image_count: Optional[int] = Field(None, alias="image_count")
    transcribed_count: Optional[int] = Field(None, alias="transcribed_count")
    total_duration: Optional[float] = Field(None, alias="total_duration")


TranscriptOutput = Union[List[TranscriptSegment], str]


class CarouselVideoResult(BaseModel):
    index: Optional[int] = None
    status: Optional[str] = None
    video_info: Optional[VideoInfo] = Field(None, alias="video_info")
    transcript: Optional[TranscriptOutput] = None
    error: Optional[str] = None
    message: Optional[str] = None


def _parse_nested(model_cls: Any, raw: Any) -> Any:
    """Pydantic v1/v2-compatible model parsing for use inside validators."""
    if hasattr(model_cls, "model_validate"):
        return model_cls.model_validate(raw)
    return model_cls.parse_obj(raw)


def _normalize_date(v: Any) -> Optional[str]:
    """Accept plain ISO strings or MongoDB ``{"$date": "..."}`` objects."""
    if v is None:
        return None
    if isinstance(v, dict) and "$date" in v:
        return v["$date"]
    return str(v)


def _coerce_optional_int(v: Any) -> Optional[int]:
    """Normalize API integer fields that may arrive as numeric strings."""
    if v is None:
        return None
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    if isinstance(v, str):
        stripped = v.strip().replace(",", "")
        if not stripped:
            return None
        return int(float(stripped))
    return v  # type: ignore[return-value]


class Namespace(BaseModel):
    """API may return Mongo-style ``_id``; it is exposed as *mongo_id*."""

    id: Optional[str] = None
    mongo_id: Optional[str] = Field(None, alias="_id")
    user_id: Optional[str] = Field(None, alias="user_id")
    name: Optional[str] = None
    created_at: Optional[str] = Field(None, alias="created_at")
    updated_at: Optional[str] = Field(None, alias="updated_at")

    @_pre_validator("created_at", "updated_at")
    @classmethod
    def _normalize_dates(cls, v):
        return _normalize_date(v)


class UsageTokens(BaseModel):
    """LLM token tally reported on the ``analysis_request`` charge entry."""

    prompt_tokens: Optional[int] = Field(None, alias="prompt_tokens")
    completion_tokens: Optional[int] = Field(None, alias="completion_tokens")
    total_tokens: Optional[int] = Field(None, alias="total_tokens")


class UsageCharge(BaseModel):
    """A single consolidated meter charge within a :class:`UsageBlock`."""

    service_type: Optional[str] = Field(None, alias="service_type")
    quantity: Optional[float] = None
    credits: Optional[float] = None
    waived: Optional[bool] = None
    credits_saved: Optional[float] = Field(None, alias="credits_saved")
    tokens: Optional[UsageTokens] = None


class UsageWaived(BaseModel):
    credits_saved: Optional[float] = Field(None, alias="credits_saved")


class UsageBlock(BaseModel):
    """Per-call usage disclosure returned when ``include_usage=true``.

    Lists every meter that fired (``charges``) and the net credits deducted.
    For LLM endpoints (extract/analyze/youtube search) the ``analysis_request``
    charge carries a nested :class:`UsageTokens`. ``/extract/*`` responses may
    also echo the token counts as flat ``prompt_tokens`` / ``completion_tokens``
    / ``total_tokens`` fields, which remain accessible here for convenience.
    """

    charges: Optional[List[UsageCharge]] = None
    total_credits: Optional[float] = Field(None, alias="total_credits")
    credits_remaining_after: Optional[float] = Field(None, alias="credits_remaining_after")
    waived: Optional[UsageWaived] = None
    prompt_tokens: Optional[int] = Field(None, alias="prompt_tokens")
    completion_tokens: Optional[int] = Field(None, alias="completion_tokens")
    total_tokens: Optional[int] = Field(None, alias="total_tokens")

    @property
    def analysis_tokens(self) -> Optional[UsageTokens]:
        """Return LLM token counts from the ``analysis_request`` charge, if any."""
        for charge in self.charges or []:
            if charge.service_type == "analysis_request" and charge.tokens is not None:
                return charge.tokens
        if any(v is not None for v in (self.prompt_tokens, self.completion_tokens, self.total_tokens)):
            return UsageTokens(
                prompt_tokens=self.prompt_tokens,
                completion_tokens=self.completion_tokens,
                total_tokens=self.total_tokens,
            )
        return None

    def charge_for(self, service_type: str) -> Optional[UsageCharge]:
        """Return the consolidated charge entry for a given meter, if present."""
        for charge in self.charges or []:
            if charge.service_type == service_type:
                return charge
        return None


# Backwards-compatible alias (pre-1.0.5 name).
ExtractionTokenUsage = UsageBlock


# ---------------------------------------------------------------------------
# Async jobs (shared by /transcribe, /extract/video, /tweet/statement and TikTok)
# ---------------------------------------------------------------------------


class AsyncJobError(BaseModel):
    """Failure details of an async job.

    Carries the same ``error`` code and HTTP status the synchronous endpoint
    would have returned; :meth:`to_exception` turns it into the matching SDK
    exception.
    """

    error: Optional[str] = None
    message: Optional[str] = None
    http_status: Optional[int] = Field(None, alias="http_status")

    def to_exception(self) -> VidNavigatorError:
        return error_from_response(
            self.http_status,
            {"error": self.error, "message": self.message or self.error or "Async job failed"},
        )


class AsyncJobWebhookStatus(BaseModel):
    """Delivery state of a job's webhook (the URL itself is never echoed back)."""

    status: Optional[str] = None
    attempts: Optional[int] = None
    response_status: Optional[int] = Field(None, alias="response_status")
    last_error: Optional[str] = Field(None, alias="last_error")
    delivered_at: Optional[str] = Field(None, alias="delivered_at")


class _TaskStatusMixin:
    """Status helpers shared by every pollable task body.

    Subclasses must define ``task_id``, ``task_status`` and ``error`` fields.
    """

    @property
    def is_processing(self) -> bool:
        return self.task_status == "processing"

    @property
    def is_completed(self) -> bool:
        return self.task_status == "completed"

    @property
    def is_failed(self) -> bool:
        return self.task_status == "failed"

    @property
    def is_finished(self) -> bool:
        """True once the task reached a terminal state (``completed`` or ``failed``)."""
        return self.task_status in ("completed", "failed")

    def raise_for_error(self) -> None:
        """Raise the SDK exception matching the failure when ``task_status == "failed"``.

        The exception is built from the ``error`` object (``error``, ``message``,
        ``http_status``), never from the deprecated ``error_message`` field.
        """
        if not self.is_failed:
            return
        if self.error is not None:
            raise self.error.to_exception()
        raise VidNavigatorError(f"Task {self.task_id} failed without error details")


class AsyncJobSubmitData(BaseModel):
    task_id: Optional[str] = Field(None, alias="task_id")
    task_status: Optional[str] = Field(None, alias="task_status")
    job_type: Optional[str] = Field(None, alias="job_type")
    expires_at: Optional[str] = Field(None, alias="expires_at")
    check_status_url: Optional[str] = Field(None, alias="check_status_url")
    webhook_url: Optional[str] = Field(None, alias="webhook_url")
    message: Optional[str] = None
    docs_url: Optional[str] = Field(None, alias="docs_url")


class AsyncJobSubmitResponse(BaseModel):
    """``202`` response from an async submit endpoint."""

    status: str
    data: AsyncJobSubmitData


class _AsyncJobBase(_TaskStatusMixin, BaseModel):
    task_id: Optional[str] = Field(None, alias="task_id")
    task_status: Optional[str] = Field(None, alias="task_status")
    job_type: Optional[str] = Field(None, alias="job_type")
    request: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = Field(None, alias="created_at")
    started_at: Optional[str] = Field(None, alias="started_at")
    completed_at: Optional[str] = Field(None, alias="completed_at")
    expires_at: Optional[str] = Field(None, alias="expires_at")
    check_status_url: Optional[str] = Field(None, alias="check_status_url")
    webhook: Optional[AsyncJobWebhookStatus] = None
    error: Optional[AsyncJobError] = None


class TikTokVideo(BaseModel):
    id: Optional[str] = None
    track: Optional[str] = None
    artists: Optional[List[str]] = None
    duration: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    timestamp: Optional[int] = None
    published_at: Optional[datetime] = Field(None, alias="published_at")
    views: Optional[int] = None
    likes: Optional[int] = None
    reposts: Optional[int] = None
    comments: Optional[int] = None
    thumbnails: Optional[List[Dict[str, Any]]] = None
    url: Optional[str] = None

    @_pre_validator("duration", "timestamp", "views", "likes", "reposts", "comments")
    @classmethod
    def _coerce_int_fields(cls, v):
        return _coerce_optional_int(v)


class TikTokProfileFilters(BaseModel):
    max_posts: Optional[int] = Field(None, alias="max_posts")
    after_datetime: Optional[str] = Field(None, alias="after_datetime")
    before_datetime: Optional[str] = Field(None, alias="before_datetime")
    min_likes: Optional[int] = Field(None, alias="min_likes")
    max_likes: Optional[int] = Field(None, alias="max_likes")

    @_pre_validator("max_posts", "min_likes", "max_likes")
    @classmethod
    def _coerce_int_fields(cls, v):
        return _coerce_optional_int(v)


class TikTokProfileStats(BaseModel):
    videos_scanned: Optional[int] = Field(None, alias="videos_scanned")
    videos_matched: Optional[int] = Field(None, alias="videos_matched")
    pages_consumed: Optional[int] = Field(None, alias="pages_consumed")

    @_pre_validator("videos_scanned", "videos_matched", "pages_consumed")
    @classmethod
    def _coerce_int_fields(cls, v):
        return _coerce_optional_int(v)


class TikTokProfilePagination(BaseModel):
    limit: Optional[int] = None
    offset: Optional[int] = None
    total_items: Optional[int] = Field(None, alias="total_items")
    has_next: Optional[bool] = Field(None, alias="has_next")
    has_prev: Optional[bool] = Field(None, alias="has_prev")
    next_cursor: Optional[str] = Field(None, alias="next_cursor")
    prev_cursor: Optional[str] = Field(None, alias="prev_cursor")

    @_pre_validator("limit", "offset", "total_items")
    @classmethod
    def _coerce_int_fields(cls, v):
        return _coerce_optional_int(v)


class TikTokProfileTask(_TaskStatusMixin, BaseModel):
    task_id: Optional[str] = Field(None, alias="task_id")
    task_status: Optional[str] = Field(None, alias="task_status")
    profile_url: Optional[str] = Field(None, alias="profile_url")
    profile: Optional[Dict[str, Any]] = None
    filters: Optional[TikTokProfileFilters] = None
    stats: Optional[TikTokProfileStats] = None
    videos: Optional[List[TikTokVideo]] = None
    pagination: Optional[TikTokProfilePagination] = None
    download_url: Optional[str] = Field(None, alias="download_url")
    # Deprecated by the API in favour of ``error``; kept for existing integrations.
    error_message: Optional[str] = Field(None, alias="error_message")
    created_at: Optional[str] = Field(None, alias="created_at")
    completed_at: Optional[str] = Field(None, alias="completed_at")
    expires_at: Optional[str] = Field(None, alias="expires_at")
    error: Optional[AsyncJobError] = None
    webhook: Optional[AsyncJobWebhookStatus] = None


class TikTokSearchAuthor(BaseModel):
    id: Optional[str] = None
    unique_id: Optional[str] = Field(None, alias="unique_id")
    nickname: Optional[str] = None
    sec_uid: Optional[str] = Field(None, alias="sec_uid")


class TikTokSearchStats(BaseModel):
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    collects: Optional[int] = None

    @_pre_validator("views", "likes", "comments", "shares", "collects")
    @classmethod
    def _coerce_int_fields(cls, v):
        return _coerce_optional_int(v)


class TikTokSearchMusic(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    author_name: Optional[str] = Field(None, alias="author_name")
    duration: Optional[int] = None

    @_pre_validator("duration")
    @classmethod
    def _coerce_int_fields(cls, v):
        return _coerce_optional_int(v)


class TikTokSearchResult(BaseModel):
    id: Optional[str] = None
    item_type: Optional[int] = Field(None, alias="item_type")
    description: Optional[str] = None
    timestamp: Optional[int] = None
    published_at: Optional[datetime] = Field(None, alias="published_at")
    author: Optional[TikTokSearchAuthor] = None
    stats: Optional[TikTokSearchStats] = None
    music: Optional[TikTokSearchMusic] = None
    duration: Optional[int] = None
    hashtags: Optional[List[str]] = None
    url: Optional[str] = None

    @_pre_validator("item_type", "timestamp", "duration")
    @classmethod
    def _coerce_int_fields(cls, v):
        return _coerce_optional_int(v)


class TikTokSearchFilters(BaseModel):
    sort_by: Optional[str] = Field(None, alias="sort_by")
    published_within: Optional[str] = Field(None, alias="published_within")
    after_datetime: Optional[str] = Field(None, alias="after_datetime")
    before_datetime: Optional[str] = Field(None, alias="before_datetime")
    min_likes: Optional[int] = Field(None, alias="min_likes")
    max_likes: Optional[int] = Field(None, alias="max_likes")
    min_views: Optional[int] = Field(None, alias="min_views")
    max_views: Optional[int] = Field(None, alias="max_views")

    @_pre_validator("min_likes", "max_likes", "min_views", "max_views")
    @classmethod
    def _coerce_int_fields(cls, v):
        return _coerce_optional_int(v)


class TikTokSearchStatsSummary(BaseModel):
    pages_fetched: Optional[int] = Field(None, alias="pages_fetched")
    results_count: Optional[int] = Field(None, alias="results_count")
    next_search_cursor: Optional[int] = Field(None, alias="next_search_cursor")
    sort_by: Optional[str] = Field(None, alias="sort_by")
    published_within: Optional[str] = Field(None, alias="published_within")

    @_pre_validator("pages_fetched", "results_count", "next_search_cursor")
    @classmethod
    def _coerce_int_fields(cls, v):
        return _coerce_optional_int(v)


class TikTokSearchTask(_TaskStatusMixin, BaseModel):
    task_id: Optional[str] = Field(None, alias="task_id")
    task_status: Optional[str] = Field(None, alias="task_status")
    query: Optional[str] = None
    parallel_search_slices: Optional[int] = Field(None, alias="parallel_search_slices")
    filters: Optional[TikTokSearchFilters] = None
    stats: Optional[TikTokSearchStatsSummary] = None
    results: Optional[List[TikTokSearchResult]] = None
    pagination: Optional[TikTokProfilePagination] = None
    download_url: Optional[str] = Field(None, alias="download_url")
    # Deprecated by the API in favour of ``error``; kept for existing integrations.
    error_message: Optional[str] = Field(None, alias="error_message")
    created_at: Optional[str] = Field(None, alias="created_at")
    completed_at: Optional[str] = Field(None, alias="completed_at")
    expires_at: Optional[str] = Field(None, alias="expires_at")
    error: Optional[AsyncJobError] = None
    webhook: Optional[AsyncJobWebhookStatus] = None

    @_pre_validator("parallel_search_slices")
    @classmethod
    def _coerce_int_fields(cls, v):
        return _coerce_optional_int(v)


class TweetStatementData(BaseModel):
    final_statement: Optional[str] = Field(None, alias="final_statement")
    statement_query: Optional[str] = Field(None, alias="statement_query")
    detailed_analysis: Optional[str] = Field(None, alias="detailed_analysis")
    topics: Optional[List[str]] = None
    entities: Optional[List[str]] = None
    claim_type: Optional[str] = Field(None, alias="claim_type")
    intent: Optional[str] = None
    tone: Optional[str] = None
    emotion: Optional[str] = None
    authority: Optional[str] = None
    tweet_text: Optional[str] = Field(None, alias="tweet_text")
    tweet_media_summary: Optional[str] = Field(None, alias="tweet_media_summary")
    quoted_tweet_text: Optional[str] = Field(None, alias="quoted_tweet_text")
    quoted_media_summary: Optional[str] = Field(None, alias="quoted_media_summary")


class HealthEndpoint(BaseModel):
    path: Optional[str] = None
    method: Optional[str] = None
    description: Optional[str] = None
    auth_required: Optional[bool] = Field(None, alias="auth_required")


# ---------------------------------------------------------------------------
# Wrapper / response models
# ---------------------------------------------------------------------------


class TranscriptData(BaseModel):
    video_info: VideoInfo = Field(alias="video_info")
    transcript: Optional[TranscriptOutput] = None


class TranscriptResponse(BaseModel):
    status: str
    data: TranscriptData
    usage: Optional[UsageBlock] = None


class TranscribeAllVideosData(BaseModel):
    carousel_info: CarouselInfo = Field(alias="carousel_info")
    videos: List[CarouselVideoResult]


class TranscribeAllVideosResponse(BaseModel):
    status: str
    data: TranscribeAllVideosData
    usage: Optional[UsageBlock] = None


class AnalysisData(BaseModel):
    video_info: Optional[VideoInfo] = Field(None, alias="video_info")
    file_info: Optional[FileInfo] = Field(None, alias="file_info")
    transcript: Optional[TranscriptOutput] = None
    transcript_analysis: AnalysisResult = Field(alias="transcript_analysis")


class AnalysisResponse(BaseModel):
    status: str
    data: AnalysisData
    usage: Optional[UsageBlock] = None


class VideoSearchData(BaseModel):
    results: List[VideoSearchResult]
    query: str
    total_found: int = Field(alias="total_found")
    explanation: Optional[str] = None


class VideoSearchResponse(BaseModel):
    status: str
    data: VideoSearchData
    usage: Optional[UsageBlock] = None


class FileSearchData(BaseModel):
    results: List[FileSearchResult]
    query: str
    total_found: int = Field(alias="total_found")
    explanation: Optional[str] = None


class FileSearchResponse(BaseModel):
    status: str
    data: FileSearchData
    usage: Optional[UsageBlock] = None


class FilesListData(BaseModel):
    files: List[FileInfo]
    total_count: int = Field(alias="total_count")
    limit: int
    offset: int
    has_more: bool = Field(alias="has_more")


class FilesListResponse(BaseModel):
    status: str
    data: FilesListData


class FileResponseData(BaseModel):
    file_info: FileInfo = Field(alias="file_info")
    transcript: Optional[TranscriptOutput] = None


class FileResponse(BaseModel):
    status: str
    data: FileResponseData


class NamespaceListResponse(BaseModel):
    status: str
    data: List[Namespace]


class NamespaceResponse(BaseModel):
    status: str
    data: Namespace


class ExtractionApiResponse(BaseModel):
    status: str
    data: Dict[str, Any]
    video_info: Optional[VideoInfo] = Field(None, alias="video_info")
    file_info: Optional[FileInfo] = Field(None, alias="file_info")
    usage: Optional[UsageBlock] = None


class TikTokProfileSubmitData(BaseModel):
    task_id: Optional[str] = Field(None, alias="task_id")
    task_status: Optional[str] = Field(None, alias="task_status")
    profile_url: Optional[str] = Field(None, alias="profile_url")
    expires_at: Optional[str] = Field(None, alias="expires_at")
    check_status_url: Optional[str] = Field(None, alias="check_status_url")
    webhook_url: Optional[str] = Field(None, alias="webhook_url")
    message: Optional[str] = None


class TikTokProfileSubmitResponse(BaseModel):
    status: str
    data: TikTokProfileSubmitData


class TikTokProfileResponse(BaseModel):
    status: str
    data: TikTokProfileTask
    usage: Optional[UsageBlock] = None


class TikTokSearchSubmitData(BaseModel):
    task_id: Optional[str] = Field(None, alias="task_id")
    task_status: Optional[str] = Field(None, alias="task_status")
    query: Optional[str] = None
    max_results: Optional[int] = Field(None, alias="max_results")
    parallel_search_slices: Optional[int] = Field(None, alias="parallel_search_slices")
    filters: Optional[TikTokSearchFilters] = None
    expires_at: Optional[str] = Field(None, alias="expires_at")
    check_status_url: Optional[str] = Field(None, alias="check_status_url")
    webhook_url: Optional[str] = Field(None, alias="webhook_url")
    message: Optional[str] = None

    @_pre_validator("max_results", "parallel_search_slices")
    @classmethod
    def _coerce_int_fields(cls, v):
        return _coerce_optional_int(v)


class TikTokSearchSubmitResponse(BaseModel):
    status: str
    data: TikTokSearchSubmitData


class TikTokSearchResponse(BaseModel):
    status: str
    data: TikTokSearchTask
    usage: Optional[UsageBlock] = None


class TweetStatementResponse(BaseModel):
    status: str
    data: TweetStatementData
    usage: Optional[UsageBlock] = None


# --- Async job results ---


class TranscribeJob(_AsyncJobBase):
    """Body of ``GET /transcribe/{task_id}``.

    Once completed, ``result`` is exactly the ``data`` block of the synchronous
    :meth:`~vidnavigator.VidNavigatorClient.transcribe_video` response: a
    :class:`TranscriptData`, or :class:`TranscribeAllVideosData` for carousel
    jobs submitted with ``all_videos=True``.
    """

    result: Optional[Union[TranscribeAllVideosData, TranscriptData]] = None

    @_pre_validator("result")
    @classmethod
    def _pick_result_model(cls, v):
        if isinstance(v, dict):
            if "videos" in v or "carousel_info" in v:
                return _parse_nested(TranscribeAllVideosData, v)
            return _parse_nested(TranscriptData, v)
        return v


class ExtractVideoJob(_AsyncJobBase):
    """Body of ``GET /extract/video/{task_id}``.

    Once completed, ``result`` holds the extracted data, matching the ``data``
    field of the synchronous :meth:`~vidnavigator.VidNavigatorClient.extract_video_data`.
    """

    result: Optional[Dict[str, Any]] = None


class TweetStatementJob(_AsyncJobBase):
    """Body of ``GET /tweet/statement/{task_id}``; ``result`` mirrors the sync ``data`` block."""

    result: Optional[TweetStatementData] = None


class TranscribeJobResponse(BaseModel):
    status: str
    data: TranscribeJob
    usage: Optional[UsageBlock] = None


class ExtractVideoJobResponse(BaseModel):
    status: str
    data: ExtractVideoJob
    usage: Optional[UsageBlock] = None


class TweetStatementJobResponse(BaseModel):
    status: str
    data: TweetStatementJob
    usage: Optional[UsageBlock] = None


# --- Webhooks ---


class WebhookEventData(BaseModel):
    task_id: Optional[str] = Field(None, alias="task_id")
    task_status: Optional[str] = Field(None, alias="task_status")
    job_type: Optional[str] = Field(None, alias="job_type")
    check_status_url: Optional[str] = Field(None, alias="check_status_url")
    # For TikTok events this is a summary, not the videos:
    # ``{"stats": {...}, "download_url_available": bool}``.
    result: Optional[Dict[str, Any]] = None
    result_truncated: Optional[bool] = Field(None, alias="result_truncated")
    error: Optional[AsyncJobError] = None


class WebhookEvent(BaseModel):
    """JSON body POSTed to your ``webhook_url`` when a job reaches a terminal state.

    ``type`` is e.g. ``"transcribe.completed"`` or ``"tiktok_search.failed"``.
    When ``data.result_truncated`` is true (result over 256 KB), fetch the
    result by polling ``data.task_id`` instead. TikTok events only carry a
    summary in ``data.result`` (``stats`` and ``download_url_available``); read
    the videos with the job handle.
    """

    id: Optional[str] = None
    type: Optional[str] = None
    created_at: Optional[str] = Field(None, alias="created_at")
    api_version: Optional[str] = Field(None, alias="api_version")
    data: Optional[WebhookEventData] = None


class FileNamespacesData(BaseModel):
    namespace_ids: Optional[List[str]] = Field(None, alias="namespace_ids")
    namespaces: Optional[List[NamespaceRef]] = None


class FileNamespacesResponse(BaseModel):
    """Response from PUT /file/{file_id}/namespaces with updated assignments."""

    status: str
    message: Optional[str] = None
    data: Optional[FileNamespacesData] = None


class MessageResponse(BaseModel):
    """Generic success responses with status + message (namespaces rename/delete)."""

    status: str
    message: Optional[str] = None


# --- Usage Schemas ---


class ActivityCount(BaseModel):
    used: float
    unit: Optional[str] = None


class CreditsInfo(BaseModel):
    monthly_total: Union[float, str]
    monthly_remaining: Union[float, str]
    purchased: float


class CapacityMetric(BaseModel):
    used: int
    limit: Union[int, str]
    remaining: Union[int, str]
    percentage: float


class StorageUsage(BaseModel):
    used_bytes: int
    used_formatted: str
    limit_bytes: Union[int, str]
    limit_formatted: str
    remaining_bytes: Union[int, str]
    remaining_formatted: str
    percentage: float


class UsagePeriod(BaseModel):
    start: str
    end: str


class BillingPeriod(BaseModel):
    start: str
    end: str
    interval: Optional[str] = None


class Subscription(BaseModel):
    plan_id: Optional[str] = None
    plan_name: Optional[str] = None
    interval: Optional[str] = None
    status: Optional[str] = None
    cancel_at_period_end: Optional[bool] = None


class UsageDetails(BaseModel):
    standard_request: Optional[ActivityCount] = None
    residential_request: Optional[ActivityCount] = None
    search_request: Optional[ActivityCount] = None
    analysis_request: Optional[ActivityCount] = None
    transcription_hour: Optional[ActivityCount] = None
    video_transcripts: Optional[ActivityCount] = None
    youtube_transcripts: Optional[ActivityCount] = None
    video_searches: Optional[ActivityCount] = None
    video_analyses: Optional[ActivityCount] = None
    video_scene_analyses: Optional[ActivityCount] = None
    video_uploads: Optional[ActivityCount] = None


class UsageData(BaseModel):
    usage_period: Optional[UsagePeriod] = None
    billing_period: Optional[BillingPeriod] = None
    subscription: Optional[Subscription] = None
    credits: Optional[CreditsInfo] = None
    usage: Optional[UsageDetails] = None
    channels_indexed: Optional[CapacityMetric] = Field(None, alias="channels_indexed")
    storage: Optional[StorageUsage] = None
    generated_at: Optional[str] = None


class UsageResponse(BaseModel):
    status: str
    data: UsageData


class HealthResponse(BaseModel):
    status: str
    message: Optional[str] = None
    version: Optional[str] = None
    endpoints: Optional[List[HealthEndpoint]] = None
