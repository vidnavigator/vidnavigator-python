"""Typed Pydantic models that mirror VidNavigator API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

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


class ExtractionTokenUsage(BaseModel):
    prompt_tokens: Optional[int] = Field(None, alias="prompt_tokens")
    completion_tokens: Optional[int] = Field(None, alias="completion_tokens")
    total_tokens: Optional[int] = Field(None, alias="total_tokens")


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
    after_date: Optional[str] = Field(None, alias="after_date")
    before_date: Optional[str] = Field(None, alias="before_date")
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


class TikTokProfileTask(BaseModel):
    task_id: Optional[str] = Field(None, alias="task_id")
    task_status: Optional[str] = Field(None, alias="task_status")
    profile_url: Optional[str] = Field(None, alias="profile_url")
    profile: Optional[Dict[str, Any]] = None
    filters: Optional[TikTokProfileFilters] = None
    stats: Optional[TikTokProfileStats] = None
    videos: Optional[List[TikTokVideo]] = None
    pagination: Optional[TikTokProfilePagination] = None
    download_url: Optional[str] = Field(None, alias="download_url")
    error_message: Optional[str] = Field(None, alias="error_message")
    created_at: Optional[str] = Field(None, alias="created_at")
    completed_at: Optional[str] = Field(None, alias="completed_at")
    expires_at: Optional[str] = Field(None, alias="expires_at")


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


class TranscribeAllVideosData(BaseModel):
    carousel_info: CarouselInfo = Field(alias="carousel_info")
    videos: List[CarouselVideoResult]


class TranscribeAllVideosResponse(BaseModel):
    status: str
    data: TranscribeAllVideosData


class AnalysisData(BaseModel):
    video_info: Optional[VideoInfo] = Field(None, alias="video_info")
    file_info: Optional[FileInfo] = Field(None, alias="file_info")
    transcript: Optional[TranscriptOutput] = None
    transcript_analysis: AnalysisResult = Field(alias="transcript_analysis")


class AnalysisResponse(BaseModel):
    status: str
    data: AnalysisData


class VideoSearchData(BaseModel):
    results: List[VideoSearchResult]
    query: str
    total_found: int = Field(alias="total_found")
    explanation: Optional[str] = None


class VideoSearchResponse(BaseModel):
    status: str
    data: VideoSearchData


class FileSearchData(BaseModel):
    results: List[FileSearchResult]
    query: str
    total_found: int = Field(alias="total_found")
    explanation: Optional[str] = None


class FileSearchResponse(BaseModel):
    status: str
    data: FileSearchData


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
    usage: Optional[ExtractionTokenUsage] = None


class TikTokProfileSubmitData(BaseModel):
    task_id: Optional[str] = Field(None, alias="task_id")
    task_status: Optional[str] = Field(None, alias="task_status")
    profile_url: Optional[str] = Field(None, alias="profile_url")
    expires_at: Optional[str] = Field(None, alias="expires_at")
    check_status_url: Optional[str] = Field(None, alias="check_status_url")
    message: Optional[str] = None


class TikTokProfileSubmitResponse(BaseModel):
    status: str
    data: TikTokProfileSubmitData


class TikTokProfileResponse(BaseModel):
    status: str
    data: TikTokProfileTask


class TweetStatementResponse(BaseModel):
    status: str
    data: TweetStatementData


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
