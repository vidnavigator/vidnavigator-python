"""Typed Pydantic models that mirror VidNavigator API schemas."""

from __future__ import annotations

from typing import List, Optional, Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Core data models (mirror `components.schemas`)
# ---------------------------------------------------------------------------

class TranscriptSegment(BaseModel):
    text: str
    start: float
    end: float


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
    published_date: Optional[str] = None
    keywords: Optional[List[str]] = None
    category: Optional[str] = None
    available_languages: Optional[List[str]] = Field(None, alias="available_languages")
    selected_language: Optional[str] = Field(None, alias="selected_language")


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


class PersonPlaceSubject(BaseModel):
    name: Optional[str] = None
    context: Optional[str] = None
    description: Optional[str] = None
    importance: Optional[str] = None


class AnalysisResult(BaseModel):
    summary: Optional[str] = None
    people: Optional[List[PersonPlaceSubject]] = None
    places: Optional[List[PersonPlaceSubject]] = None
    key_subjects: Optional[List[PersonPlaceSubject]] = Field(None, alias="key_subjects")
    timestamp: Optional[float] = None
    relevant_text: Optional[str] = Field(None, alias="relevant_text")
    query_answer: Optional[Any] = Field(None, alias="query_answer")


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
    people: Optional[List[PersonPlaceSubject]] = None
    places: Optional[List[PersonPlaceSubject]] = None
    key_subjects: Optional[List[PersonPlaceSubject]] = Field(None, alias="key_subjects")
    timestamp: Optional[float] = None
    relevant_text: Optional[str] = Field(None, alias="relevant_text")
    query_relevance: Optional[str] = Field(None, alias="query_relevance")


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
    relevance_score: Optional[float] = Field(None, alias="relevance_score")
    timestamp: Optional[float] = None
    relevant_text: Optional[str] = Field(None, alias="relevant_text")
    query_answer: Optional[str] = Field(None, alias="query_answer")
    transcript_summary: Optional[str] = Field(None, alias="transcript_summary")
    people: Optional[List[PersonPlaceSubject]] = None
    places: Optional[List[PersonPlaceSubject]] = None
    key_subjects: Optional[List[PersonPlaceSubject]] = Field(None, alias="key_subjects")


# ---------------------------------------------------------------------------
# Wrapper / response models
# ---------------------------------------------------------------------------

class TranscriptData(BaseModel):
    video_info: VideoInfo = Field(alias="video_info")
    transcript: List[TranscriptSegment]


class TranscriptResponse(BaseModel):
    status: str
    data: TranscriptData


class AnalysisData(BaseModel):
    video_info: Optional[VideoInfo] = Field(None, alias="video_info")
    file_info: Optional[FileInfo] = Field(None, alias="file_info")
    transcript: List[TranscriptSegment]
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
    transcript: Optional[List[TranscriptSegment]] = None


class FileResponse(BaseModel):
    status: str
    data: FileResponseData 